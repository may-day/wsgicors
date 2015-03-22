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

from webob import Request, Response
from wsgicors import make_middleware as mw
from nose import with_setup

deny = {"policy":"deny"}

free = {"policy":"pol", 
        "pol_origin":"*", 
        "pol_methods":"*", 
        "pol_headers":"*",
        "pol_credentials":"true",
        "pol_maxage":"100"
        }

wildcard = {"policy":"pol", 
        "pol_origin":"example.com example?.com *.example.com", 
        "pol_methods":"*", 
        "pol_headers":"*",
        "pol_credentials":"true",
        "pol_maxage":"100"
        }

free_nocred = {"policy":"pol", 
        "pol_origin":"*", 
        "pol_methods":"*", 
        "pol_headers":"*",
        "pol_credentials":"false",
        "pol_maxage":"100"
        }

verbatim = {"policy":"pol", 
        "pol_origin":"example.com", 
        "pol_methods":"put,delete", 
        "pol_headers":"header1,header2",
        "pol_credentials":"true",
        "pol_maxage":"100"
        }

post2 = post = preflight = None

def setup():
    global preflight, deniedpreflight, allowedpreflight, post, post2, post3

    preflight = Request.blank("/")
    preflight.method="OPTIONS"
    preflight.headers["Access-Control-Request-Method"] = "post"
    preflight.headers["Access-Control-Request-Headers"] = "*"

    deniedpreflight = Request.blank("/")
    deniedpreflight.method="OPTIONS"
    deniedpreflight.headers["Access-Control-Request-Method"] = "post"
    deniedpreflight.headers["Access-Control-Request-Headers"] = "*"
    deniedpreflight.headers["Origin"] = "somedomain.com"

    allowedpreflight = Request.blank("/")
    allowedpreflight.method="OPTIONS"
    allowedpreflight.headers["Access-Control-Request-Method"] = "post"
    allowedpreflight.headers["Access-Control-Request-Headers"] = "*"
    allowedpreflight.headers["Origin"] = "sub.example.com"

    post = Request.blank("/")
    post.method="POST"
    post.headers["Origin"] = "example.com"

    post2 = Request.blank("/")
    post2.method="POST"
    post2.headers["Origin"] = "example2.com"

    post3 = Request.blank("/")
    post3.method="POST"
    post3.headers["Origin"] = "sub.example.com"

@with_setup(setup)
def testdeny():
    corsed = mw(Response(), deny)
    res = preflight.get_response(corsed)
    assert "Access-Control-Allow-Origin" not in res.headers
    assert "Access-Control-Allow-Credentials" not in res.headers
    assert "Access-Control-Allow-Methods" not in res.headers
    assert "Access-Control-Allow-Headers" not in res.headers
    assert "Access-Control-Max-Age" not in res.headers

    res = post.get_response(corsed)
    assert "Access-Control-Allow-Origin" not in res.headers
    assert "Access-Control-Allow-Credentials" not in res.headers

@with_setup(setup)
def testfree():
    corsed = mw(Response(), free)
    res = preflight.get_response(corsed)
    assert res.headers.get("Access-Control-Allow-Origin", "") == "*"
    assert res.headers.get("Access-Control-Allow-Credentials", "") == "true"
    assert res.headers.get("Access-Control-Allow-Methods", "") == "post"
    assert res.headers.get("Access-Control-Allow-Headers", "") == "*"
    assert res.headers.get("Access-Control-Max-Age", "0") == "100"

    res = post.get_response(corsed)
    assert res.headers.get("Access-Control-Allow-Origin", "") == "example.com"
    assert res.headers.get("Access-Control-Allow-Credentials", "") == "true"

@with_setup(setup)
def testwildcard():
    corsed = mw(Response(), wildcard)
    res = deniedpreflight.get_response(corsed)
    assert res.headers.get("Access-Control-Allow-Origin", "") == ""
    assert res.headers.get("Access-Control-Allow-Credentials", "") == "true"
    assert res.headers.get("Access-Control-Allow-Methods", "") == "post"
    assert res.headers.get("Access-Control-Allow-Headers", "") == "*"
    assert res.headers.get("Access-Control-Max-Age", "0") == "100"

    res = allowedpreflight.get_response(corsed)
    assert res.headers.get("Access-Control-Allow-Origin", "") == "sub.example.com"
    assert res.headers.get("Access-Control-Allow-Credentials", "") == "true"
    assert res.headers.get("Access-Control-Allow-Methods", "") == "post"
    assert res.headers.get("Access-Control-Allow-Headers", "") == "*"
    assert res.headers.get("Access-Control-Max-Age", "0") == "100"

    res = post.get_response(corsed)
    assert res.headers.get("Access-Control-Allow-Origin", "") == "example.com"
    assert res.headers.get("Access-Control-Allow-Credentials", "") == "true"

    res = post3.get_response(corsed)
    assert res.headers.get("Access-Control-Allow-Origin", "") == "sub.example.com"
    assert res.headers.get("Access-Control-Allow-Credentials", "") == "true"


@with_setup(setup)
def testfree_nocred():
    """
    similar to free, but the actual request will be answered 
    with a '*' for allowed origin
    """

    corsed = mw(Response(), free_nocred)
    res = preflight.get_response(corsed)
    assert res.headers.get("Access-Control-Allow-Origin", "") == "*"
    assert res.headers.get("Access-Control-Allow-Credentials", None) == None
    assert res.headers.get("Access-Control-Allow-Methods", "") == "post"
    assert res.headers.get("Access-Control-Allow-Headers", "") == "*"
    assert res.headers.get("Access-Control-Max-Age", "0") == "100"

    res = post.get_response(corsed)
    assert res.headers.get("Access-Control-Allow-Origin", "") == "*"
    assert res.headers.get("Access-Control-Allow-Credentials", None) == None

@with_setup(setup)
def testverbatim():

    corsed = mw(Response(), verbatim)
    res = preflight.get_response(corsed)
    assert res.headers.get("Access-Control-Allow-Origin", "") == "example.com"
    assert res.headers.get("Access-Control-Allow-Credentials", "") == "true"
    assert res.headers.get("Access-Control-Allow-Methods", "") == "put,delete"
    assert res.headers.get("Access-Control-Allow-Headers", "") == "header1,header2"
    assert res.headers.get("Access-Control-Max-Age", "0") == "100"

    res = post.get_response(corsed)
    assert res.headers.get("Access-Control-Allow-Origin", "") == "example.com"
    assert res.headers.get("Access-Control-Allow-Credentials", "") == "true"

@with_setup(setup)
def test_req_origin_no_match():
    "sending a post from a disallowed host => no allow headers will be returned"

    corsed = mw(Response(), verbatim)
    res = preflight.get_response(corsed)
    assert res.headers.get("Access-Control-Allow-Origin", "") == "example.com"
    assert res.headers.get("Access-Control-Allow-Credentials", "") == "true"
    assert res.headers.get("Access-Control-Allow-Methods", "") == "put,delete"
    assert res.headers.get("Access-Control-Allow-Headers", "") == "header1,header2"
    assert res.headers.get("Access-Control-Max-Age", "0") == "100"

    res = post2.get_response(corsed)
    assert "Access-Control-Allow-Origin" not in res.headers
    assert "Access-Control-Allow-Credentials" not in res.headers

    
