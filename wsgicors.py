# -*- encoding: utf-8 -*-
#
# This file is part of wsgicors
#
# wsgicors is a WSGI middleware that answers CORS preflight requests
# 
# copyright 2014-2015 Norman Krämer
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import fnmatch
from functools import reduce
from collections import namedtuple
try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

class CORS(object):
    "WSGI middleware allowing CORS requests to succeed"

    @staticmethod
    def matchpattern(accu, pattern, host):
        return accu or fnmatch.fnmatch(host, pattern)

    @staticmethod
    def matchlist(origin, allowed_origins, case_sensitive=False):
        return reduce(lambda accu, x: CORS.matchpattern(accu, x, origin.lower() if not case_sensitive else origin), allowed_origins, False)


    def __init__(self, application, cfg=None, **kw):

        Policy = namedtuple("Policy", ["name", "origin", "methods", "headers", "expose_headers", "credentials", "maxage", "match"])

        self.policies = {}
        if kw and "policy" not in kw:  # direct config
            self.activepolicies = ["direct"]
            self.matchstrategy = "firstmatch"
            self.policies["direct"]=kw
        else:  # multiple policies programatically or via configfile (paster factory for instance)
            cfg = kw or cfg or {}
            self.activepolicies = list(map(lambda x: x.strip(), cfg.get("policy", "deny").split(",")))
            self.matchstrategy = cfg.get("matchstrategy", "firstmatch")

            for policy in self.activepolicies:
                kw = {}
                prefix = policy + "_"
                for k, v in filter(lambda key_value: key_value[0].startswith(prefix), cfg.items()):
                    kw[k.split(prefix)[-1]] = v
                self.policies[policy]=kw

        for policy in self.activepolicies:
            kw = self.policies[policy]
            # copy or * or a space separated list of hostnames, possibly with filename wildcards "*" and "?"
            pol_origin = kw.get("origin", "")  
            if pol_origin not in ("copy", "*"):
                match = list(filter(lambda x: x != "*", map(lambda x: x.strip(), pol_origin.split(" "))))
            else:
                match = []

            pol_methods = kw.get("methods", "")
            methods = list(map(lambda x: x.strip(), pol_methods.split(",")))

            # copy or * or a space separated list of hostnames, possibly with filename wildcards "*" and "?"
            pol_headers = kw.get("headers", "")  # * or list of headers
            pol_expose_headers = kw.get("expose_headers", "")  # * or list of headers to expose to the client
            pol_credentials = kw.get("credentials", "false")  # true or false
            pol_maxage = kw.get("maxage", "")  # in seconds
            pol=Policy(name=policy, 
                       origin=pol_origin, 
                       methods=methods,
                       headers=pol_headers, 
                       expose_headers=pol_expose_headers, 
                       credentials=pol_credentials, 
                       maxage=pol_maxage, 
                       match=match)
            self.policies[policy] = pol

            # a little sanity check
            configkeys="origin,methods,headers,expose_headers,credentials,maxage".split(",")
            existingkeys=[k for k in configkeys if k in kw]
                
            if "origin" not in kw:
                if existingkeys:
                    print("The policy '%s' was referenced but has no value for 'origin' set. Nothing good can come from this." % policy)
                elif policy != "deny":
                    print("The policy '%s' was referenced but hasn't defined any keys. This might be an case sensitivity issue." % policy)
                    


        self.application = application

    @lru_cache(maxsize=200)
    def selectPolicy(self, origin, request_method=None):
        "Based on the matching strategy and the origin and optionally the requested method a tuple of policyname and origin to pass back is returned."
        ret_origin = None
        policyname = None
        if self.matchstrategy in ("firstmatch", "verbmatch"):
            for pol in self.activepolicies:
                policy=self.policies[pol]
                ret_origin = None
                policyname = policy.name
                if policyname == "deny":
                    break
                if self.matchstrategy == "verbmatch":
                    if policy.methods != "*" and not CORS.matchlist(request_method, policy.methods, case_sensitive=True):
                        continue
                if origin and policy.match:
                    if CORS.matchlist(origin, policy.match):
                        ret_origin = origin
                elif policy.origin == "copy":
                    ret_origin = origin
                elif policy.origin:
                    ret_origin = policy.origin
                if ret_origin:
                    break
        return policyname, ret_origin 

    def __call__(self, environ, start_response):

        # we handle the request ourself only if it is identified as a prefilght request
        if 'OPTIONS' == environ['REQUEST_METHOD'] and environ.get("HTTP_ACCESS_CONTROL_REQUEST_METHOD") is not None \
           and environ.get("HTTP_ORIGIN") is not None:
            resp = []

            orig = environ.get("HTTP_ORIGIN")
            ac_request_method = environ.get("HTTP_ACCESS_CONTROL_REQUEST_METHOD")
            policyname, origin = self.selectPolicy(orig, ac_request_method)

            if policyname == "deny":
                pass
            else:
                policy = self.policies[policyname]
                methods = None
                headers = None
                credentials = None
                maxage = None

                if "*" in policy.methods:
                    methods = environ.get("HTTP_ACCESS_CONTROL_REQUEST_METHOD", None)
                elif policy.methods:
                    methods = ", ".join(policy.methods)

                if policy.headers == "*":
                    headers = environ.get("HTTP_ACCESS_CONTROL_REQUEST_HEADERS", None)
                elif policy.headers:
                    headers = policy.headers

                if policy.credentials == "true":
                    credentials = "true"

                if policy.maxage:
                    maxage = policy.maxage

                if origin: resp.append(('Access-Control-Allow-Origin', origin))
                if methods: resp.append(('Access-Control-Allow-Methods', methods))
                if headers: resp.append(('Access-Control-Allow-Headers', headers))
                if credentials: resp.append(('Access-Control-Allow-Credentials', credentials))
                if maxage: resp.append(('Access-Control-Max-Age', maxage))

            status = '204 OK'
            start_response(status, resp)
            return []

        orig = environ.get("HTTP_ORIGIN", None)
        request_method = environ['REQUEST_METHOD']
        policyname, ret_origin = self.selectPolicy(orig, request_method)

        if orig and policyname != "deny":
            def custom_start_response(status, headers, exc_info=None):

                policyname, ret_origin = self.selectPolicy(orig, request_method)
                policy = self.policies[policyname]
                if policy.credentials == 'true' and policy.origin == "*":
                    # for credentialed access '*' are ignored in origin
                    ret_origin = orig

                if ret_origin:
                    headers.append(('Access-Control-Allow-Origin', ret_origin))

                    if policy.credentials == 'true':
                        headers.append(('Access-Control-Allow-Credentials', 'true'))

                    if policy.expose_headers:
                        headers.append(('Access-Control-Expose-Headers', policy.expose_headers))

                    if policy.origin != "*":
                        headers.append(('Vary', 'Origin'))

                return start_response(status, headers, exc_info)
        else:
            custom_start_response = start_response

        return self.application(environ, custom_start_response)


def make_middleware(app, cfg=None, **kw):
    cfg = (cfg or {}).copy()
    cfg.update(kw)
    app = CORS(app, cfg)
    return app
