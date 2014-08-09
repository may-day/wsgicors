import fnmatch

class CORS(object):
    "WSGI middleware allowing CORS requests to succeed"

    def __init__(self, application, cfg=None, **kw):

        if kw: # direct config
            self.policy = "direct"
        else: # via configfile, paster factory for instance
            cfg = cfg or {}
            self.policy = cfg.get("policy", "deny")
            kw = {}
            prefix=self.policy+"_"
            for k, v in filter(lambda (k, v): k.startswith(prefix), cfg.items()):
                kw[k.split(prefix)[-1]] = v


        self.pol_origin = kw.get("origin", "") # copy or * or a space separated list of hostnames, possibly with filename wildcards "*" and "?"
        if self.pol_origin not in ("copy", "*"):
            self.match=filter(lambda x: x != "*", map(lambda x: x.strip(), self.pol_origin.split(" ")))
        else:
            self.match = []
        self.pol_origin = kw.get("origin", "") # copy or * or a space separated list of hostnames, possibly with filename wildcards "*" and "?"

        self.pol_methods = kw.get("methods", "") # * or list of methods
        self.pol_headers = kw.get("headers", "") # * or list of headers
        self.pol_credentials = kw.get("credentials", "false") # true or false
        self.pol_maxage = kw.get("maxage", "") # in seconds
            
        self.application = application
 
 
    def __call__(self, environ, start_response):

        def matchpattern(accu, pattern, host):
            return accu or fnmatch.fnmatch(host, pattern)

        if 'OPTIONS' == environ['REQUEST_METHOD']:
            resp = []
            if self.policy == "deny":
                pass
            else:

                origin = None
                methods = None
                headers = None
                credentials = None
                maxage = None

                orig=environ.get("HTTP_ORIGIN",None)
                if orig and self.match:
                    if reduce(lambda accu, x: matchpattern(accu, x, orig.lower()), self.match, False):
                        origin = orig
                elif self.pol_origin == "copy":
                    origin = orig
                elif self.pol_origin:
                    origin = self.pol_origin

                if self.pol_methods == "*":
                    methods = environ.get("HTTP_ACCESS_CONTROL_REQUEST_METHOD",None)
                elif self.pol_methods:
                    methods = self.pol_methods

                if self.pol_headers == "*":
                    headers = environ.get("HTTP_ACCESS_CONTROL_REQUEST_HEADERS",None)
                elif self.pol_headers:
                    headers = self.pol_headers

                if self.pol_credentials == "true":
                    credentials = "true"

                if self.pol_maxage:
                    maxage = self.pol_maxage
                
                if origin: resp.append(('Access-Control-Allow-Origin', origin))
                if methods: resp.append(('Access-Control-Allow-Methods', methods))
                if headers: resp.append(('Access-Control-Allow-Headers', headers))
                if credentials: resp.append(('Access-Control-Allow-Credentials', credentials))
                if maxage: resp.append(('Access-Control-Max-Age', maxage))


            status = '204 OK'
            start_response(status, resp)
            return []


        orig=environ.get("HTTP_ORIGIN",None)
        if orig and self.policy != "deny":
            def custom_start_response(status, headers, exc_info=None):
                origin = None

                if orig and self.match and reduce(lambda accu, x: matchpattern(accu, x, orig.lower()), self.match, False):
                    origin = orig
                elif self.pol_origin == "copy":
                    origin = orig
                elif self.pol_origin == "*":
                    origin = "*"
                elif self.pol_origin == orig:
                    origin = orig

                if self.pol_credentials == 'true' and self.pol_origin == "*":
                    # for credentialed access '*' are ignored in origin
                    origin = orig
                    
                if origin:
                    headers.append(('Access-Control-Allow-Origin', origin))

                    if self.pol_credentials == 'true':
                        headers.append(('Access-Control-Allow-Credentials', 'true'))

                return start_response(status, headers, exc_info)
        else:
            custom_start_response = start_response
 
        return self.application(environ, custom_start_response)

def make_middleware(app, cfg=None, **kw):
    cfg = (cfg or {}).copy()
    cfg.update(kw)
    app = CORS(app, cfg)
    return app
