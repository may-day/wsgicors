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
        "pol_expose_headers":"*",
        "pol_credentials":"true",
        "pol_maxage":"100"
        }

multi = {"policy":"pol2,pol1", 
        "pol1_origin":"*", 
        "pol1_methods":"*", 
        "pol1_headers":"*",
        "pol1_expose_headers":"*",
        "pol1_credentials":"true",
        "pol1_maxage":"100",
        "pol2_origin":"*.woopy.com", 
        "pol2_methods":"*", 
        "pol2_headers":"*",
        "pol2_expose_headers":"*",
        "pol2_credentials":"true",
        "pol2_maxage":"100",
        }

# example from https://github.com/may-day/wsgicors/pull/16
# note that pol1 does not allow PUT, but pol2 does
verbmulti = {"policy":"pol2,pol1",
             "pol1_origin":"*.ourdomain.com",
             "pol1_headers":"*",
             "pol1_methods":"HEAD, OPTIONS, GET, POST, PUT, DELETE",
             "pol1_maxage":"180",
             "pol2_origin":"*",
             "pol2_headers":"*",
             "pol2_methods":"HEAD, OPTIONS, GET",
             "pol2_maxage":"180",
             }

preflight_headers = {'REQUEST_METHOD':'OPTIONS', 'Access-Control-Request-Method':'*', 'Origin':'localhost'}
request_headers = {'REQUEST_METHOD':'GET', 'Access-Control-Request-Method':'*', 'Origin':'localhost'}

def setup():
    pass

@with_setup(setup)
def test_selectPolicy_firstmatch():
    "check whether correct policy is returned"
    multi2 = multi.copy()
    multi2["policy"] = "pol2,pol1"
    multi2["matchstrategy"] = "firstmatch"
    corsed = mw(Response("this is not a preflight response"), multi2)
    
    policyname, ret_origin = corsed.selectPolicy("palim.woopy.com")
    assert policyname == "pol2", "'pol2' should have been returned since it matches first (but result was: '%s')" % policyname
    assert ret_origin == "palim.woopy.com", "'palim.woopy.com' expected since its matched by pol2 (but result was: '%s')" % ret_origin

    policyname, ret_origin = corsed.selectPolicy("palim.com")
    assert policyname == "pol1", "'pol1' should have been returned since it matches first (but result was: '%s')" % policyname
    assert ret_origin == "*", "'*' expected since its matched by pol1 (but result was: '%s')" % ret_origin

    multi2 = multi.copy()
    multi2["policy"] = "pol1,pol2"
    corsed = mw(Response("this is not a preflight response"), multi2)
    policyname, ret_origin = corsed.selectPolicy("palim.woopy.com")
    assert policyname == "pol1", "'pol1' should have been returned since it matches first (but result was: '%s')" % policyname
    assert ret_origin == "*", "'*' expectedsince its matched by pol1 (but result was: '%s')" % ret_origin

@with_setup(setup)
def test_selectPolicy_verbmatch():
    "check whether correct policy is returned"
    multi2 = verbmulti.copy()
    multi2["policy"] = "pol2,pol1"
    multi2["matchstrategy"] = "verbmatch"
    corsed = mw(Response("this is not a preflight response"), multi2)
    
    policyname, ret_origin = corsed.selectPolicy("ourdomain", "PUT")
    assert policyname == "pol1", "'pol1' should have been returned since it matches both origin and verb first (but result was: '%s')" % policyname

    multi2 = verbmulti.copy()
    multi2["policy"] = "pol2,pol1"
    multi2["matchstrategy"] = "verbmatch"
    multi2["pol1_methods"] = "*"
    corsed = mw(Response("this is not a preflight response"), multi2)
    
    policyname, ret_origin = corsed.selectPolicy("ourdomain", "PUT")
    assert policyname == "pol1", "'pol1' should have been returned since it matches both origin and verb first (but result was: '%s')" % policyname
    
@with_setup(setup)
def test_non_preflight_are_not_answered():
    "requests that don't match preflight criteria are ignored"
    corsed = mw(Response("this is not a preflight response"), free)

    for drop_header in preflight_headers.keys():
        hdr=preflight_headers.copy()
        del hdr[drop_header]
        yield non_preflight_are_not_answered, corsed, hdr

def non_preflight_are_not_answered(corsed, hdr):
    "requests that don't match preflight criteria are ignored"

    req = prepRequest(hdr)
    res = req.get_response(corsed)
    assert res.body.decode("utf-8") == "this is not a preflight response", "No preflight should have been detected (body was: '%s')" % res.body
        
def prepRequest(hdr, **kw):
    req = Request.blank("/")
    req.method= "GET" if "REQUEST_METHOD" not in hdr else hdr["REQUEST_METHOD"]
    
    for k, v in hdr.items():
        if k != "REQUEST_METHOD":
            req.headers[k] = v

    for k,v in kw.items():
        k=getRequestHeaderName(k)
        req.headers[k] = v
        
    return req 

@with_setup(setup)
def testdeny():
    "Denied policy"
    corsed = mw(Response("non preflight"), deny)
    preflight = prepRequest(preflight_headers)
    res = preflight.get_response(corsed)
    assert res.body.decode("utf-8") == "", "Body must be empty but was:%s" % res.body
    assert "Access-Control-Allow-Origin" not in res.headers, "Header should not be in repsonse"
    assert "Access-Control-Allow-Credentials" not in res.headers, "Header should not be in repsonse"
    assert "Access-Control-Allow-Methods" not in res.headers, "Header should not be in repsonse"
    assert "Access-Control-Allow-Headers" not in res.headers, "Header should not be in repsonse"
    assert "Access-Control-Max-Age" not in res.headers, "Header should not be in repsonse"
    assert "Access-Control-Expose-Headers" not in res.headers, "Header should not be in repsonse"
    assert "Vary" not in res.headers, "Header should not be in repsonse"

@with_setup(setup)
def test_origin_policy_match():
    policy = free.copy()
    policy["pol_origin"] = "http://example.com example?.com https://*.example.com"

    corsed = mw(Response("non preflight response"), policy)

    ### preflight request

    for origin, expected in [("localhost", None), 
                             ("http://example.com", "http://example.com"), 
                             ("example2.com", "example2.com"), 
                             ("https://www.example.com", "https://www.example.com")]:
        yield preflight_check_result, corsed, "Origin", origin, expected


    ### actual request

    for origin, origin_expected, vary_expected in [("localhost", None, None), 
                                                   ("http://example.com", "http://example.com", "Origin"), 
                                                   ("example2.com", "example2.com", "Origin"), 
                                                   ("https://www.example.com", "https://www.example.com", "Origin")]:
        yield request_check_result, corsed, "Origin", origin, origin_expected, ("Vary", vary_expected)


@with_setup(setup)
def test_origin_policy_copy():
    policy = free.copy()
    policy["pol_origin"] = "copy"

    corsed = mw(Response("non preflight response"), policy)

    ### preflight request

    for origin, expected in [("localhost", "localhost"), 
                             ("example.com", "example.com")]:
        yield preflight_check_result, corsed, "Origin", origin, expected


    ### actual request

    for origin, origin_expected, vary_expected in [("localhost", "localhost", "Origin"), 
                                                   ("example.com", "example.com", "Origin")]:
        yield request_check_result, corsed, "Origin", origin, origin_expected, ("Vary", vary_expected)

@with_setup(setup)
def test_origin_policy_all():
    policy = free.copy()
    policy["pol_origin"] = "*"

    corsed = mw(Response("non preflight response"), policy)

    ### preflight request

    for origin, expected in [("localhost", "*")]:
        yield preflight_check_result, corsed, "Origin", origin, expected


    ### actual request

    for origin, origin_expected, vary_expected in [("localhost", "localhost", None)]:
        yield request_check_result, corsed, "Origin", origin, origin_expected, ("Vary", vary_expected)

@with_setup(setup)
def test_method_policy_all():
    policy = free.copy()
    policy["pol_methods"] = "*"

    corsed = mw(Response("non preflight response"), policy)

    ### preflight request

    for requested, expected in [("woopy", "woopy")]:
        yield preflight_check_result, corsed, "Method", requested, expected


    ### actual request

    for requested, expected in [("woopy", None)]:
        yield request_check_result, corsed, "Method", requested, expected


@with_setup(setup)
def test_method_policy_fixed():
    policy = free.copy()
    policy["pol_methods"] = "PUT, GET"

    corsed = mw(Response("non preflight response"), policy)

    ### preflight request

    for requested, expected in [("woopy", "PUT, GET")]:
        yield preflight_check_result, corsed, "Method", requested, expected


    ### actual request

    for requested, expected in [("woopy", None)]:
        yield request_check_result, corsed, "Method", requested, expected

@with_setup(setup)
def test_header_policy_all():
    policy = free.copy()
    policy["pol_headers"] = "*"

    corsed = mw(Response("non preflight response"), policy)

    ### preflight request

    for requested, expected in [("woopy", "woopy")]:
        yield preflight_check_result, corsed, "Headers", requested, expected


    ### actual request

    for requested, expected in [("woopy", None)]:
        yield request_check_result, corsed, "Headers", requested, expected


@with_setup(setup)
def test_headers_policy_fixed():
    policy = free.copy()
    policy["pol_headers"] = "Wooble"

    corsed = mw(Response("non preflight response"), policy)

    ### preflight request

    for requested, expected in [("woopy", "Wooble")]:
        yield preflight_check_result, corsed, "Headers", requested, expected


    ### actual request

    for requested, expected in [("woopy", None)]:
        yield request_check_result, corsed, "Headers", requested, expected

@with_setup(setup)
def test_credentials_policy_true():
    "Allow-Credentials should be added to the response"
    policy = free.copy()
    policy["pol_credentials"] = "true"

    corsed = mw(Response("non preflight response"), policy)

    ### preflight request

    for requested, expected in [("woopy", "woopy")]:
        yield preflight_check_result, corsed, "Headers", requested, expected, ("Access-Control-Allow-Credentials", "true")


    ### actual request

    for requested, expected in [("woopy", None)]:
        yield request_check_result, corsed, "Headers", requested, expected, ("Access-Control-Allow-Credentials", "true")

@with_setup(setup)
def test_credentials_policy_no():
    "Allow-Credentials should not be present, if policy is different from 'yes'"
    policy = free.copy()
    policy["pol_credentials"] = "no" # something different from "yes"

    corsed = mw(Response("non preflight response"), policy)

    ### preflight request

    for requested, expected in [("woopy", "woopy")]:
        yield preflight_check_result, corsed, "Headers", requested, expected, ("Access-Control-Allow-Credentials", None)


    ### actual request

    for requested, expected in [("woopy", None)]:
        yield request_check_result, corsed, "Headers", requested, expected, ("Access-Control-Allow-Credentials", None)

@with_setup(setup)
def test_credentials_policy_none():
    "Allow-Credentials should not be present"
    policy = free.copy()
    del policy["pol_credentials"]

    corsed = mw(Response("non preflight response"), policy)

    ### preflight request

    for requested, expected in [("woopy", "woopy")]:
        yield preflight_check_result, corsed, "Headers", requested, expected, ("Access-Control-Allow-Credentials", None)


    ### actual request

    for requested, expected in [("woopy", None)]:
        yield request_check_result, corsed, "Headers", requested, expected, ("Access-Control-Allow-Credentials", None)

@with_setup(setup)
def test_age_policy_set():
    "Add Max-Age added to preflight response"
    policy = free.copy()
    policy["pol_maxage"]="100"

    corsed = mw(Response("non preflight response"), policy)

    ### preflight request

    for requested, expected in [("woopy", "woopy")]:
        yield preflight_check_result, corsed, "Headers", requested, expected, ("Access-Control-Max-Age", "100")


    ### actual request

    for requested, expected in [("woopy", None)]:
        yield request_check_result, corsed, "Headers", requested, expected, ("Access-Control-Max-Age", None)

@with_setup(setup)
def test_age_policy_unset():
    "Add Max-Age not in preflight response"
    policy = free.copy()
    del policy["pol_maxage"]

    corsed = mw(Response("non preflight response"), policy)

    ### preflight request

    for requested, expected in [("woopy", "woopy")]:
        yield preflight_check_result, corsed, "Headers", requested, expected, ("Access-Control-Max-Age", None)


    ### actual request

    for requested, expected in [("woopy", None)]:
        yield request_check_result, corsed, "Headers", requested, expected, ("Access-Control-Max-Age", None)

@with_setup(setup)
def test_expose_header_policy_set():
    "Add Expose-Headers in actual request if policy says so"
    policy = free.copy()
    policy["pol_expose_headers"] = "exposed"

    corsed = mw(Response("non preflight response"), policy)

    ### preflight request

    for requested, expected in [("woopy", "woopy")]:
        yield preflight_check_result, corsed, "Headers", requested, expected, ("Access-Control-Expose-Headers", None)


    ### actual request

    for requested, expected in [("woopy", None)]:
        yield request_check_result, corsed, "Headers", requested, expected, ("Access-Control-Expose-Headers", "exposed")

@with_setup(setup)
def test_expose_header_policy_unset():
    "No Expose-Headers in actual request if not given"
    policy = free.copy()
    del policy["pol_expose_headers"]

    corsed = mw(Response("non preflight response"), policy)

    ### preflight request

    for requested, expected in [("woopy", "woopy")]:
        yield preflight_check_result, corsed, "Headers", requested, expected, ("Access-Control-Expose-Headers", None)


    ### actual request

    for requested, expected in [("woopy", None)]:
        yield request_check_result, corsed, "Headers", requested, expected, ("Access-Control-Expose-Headers", None)

def preflight_check_result(corsed, check_header, requested, result_expected, *more_header_expectpairs):
    casename=getRequestHeaderName(check_header)
    preflight = prepRequest(preflight_headers, **{check_header:requested})
    res = preflight.get_response(corsed)
    res_header = getResponseHeaderName(check_header)
    result=res.headers.get(res_header)
    assert result == result_expected, "Preflight %s - %s: expected '%s' but got '%s'" % (casename, res_header, result_expected, result)

    for header, expected in more_header_expectpairs:
        result=res.headers.get(header)
        assert result == expected, "Preflight %s - %s: expected '%s' but got '%s'" % (casename, header, expected, result)

def request_check_result(corsed, check_header, requested, result_expected, *more_header_expectpairs):
    casename=getRequestHeaderName(check_header)

    request = prepRequest(request_headers, **{check_header:requested})
    res = request.get_response(corsed)
    result=res.body.decode("utf-8")
    expected = "non preflight response"
    assert result == expected, "ActualRequest %s - Body: expected '%s' but got '%s'" % (casename, expected, result)
    res_header = getResponseHeaderName(check_header)
    result=res.headers.get(res_header)
    assert result == result_expected, "ActualRequest %s - %s: expected '%s' but got '%s'" % (casename, res_header, result_expected, result)
    for header, expected in more_header_expectpairs:
        result=res.headers.get(header)
        assert result == expected, "ActualRequest %s - %s: expected '%s' but got '%s'" % (casename, header, expected, result)

def getResponseHeaderName(name):
    rename={
        "Method":"Access-Control-Allow-Methods"
        ,"Origin":"Access-Control-Allow-Origin"
        ,"Headers":"Access-Control-Allow-Headers"
        ,"Credentials":"Access-Control-Allow-Credentials"
        ,"Age":"Access-Control-Max-Age"
    }
    return rename.get(name)

def getRequestHeaderName(name):
    if name not in ("Origin", ):
            name="Access-Control-Request-" + name.capitalize()
    return name
