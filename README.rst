wsgicors
========

This is a WSGI middleware that answers CORS preflight requests and adds
the needed header to the response. For CORS see:
http://www.w3.org/TR/cors/

Usage
-----

Either plug it in programmatically as in this pyramid example:

.. code:: python


    def app(global_config, **settings):
        """ This function returns a WSGI application.
        
        It is usually called by the PasteDeploy framework during 
        ``paster serve``.
        """

        def get_root(request):
            return {}

        config = Configurator(root_factory=get_root, settings=settings)
        config.begin()
        # whatever it takes to config your app goes here
        config.end()

        from wsgicors import CORS
        return CORS(config.make_wsgi_app(), headers="*", methods="*", maxage="180", origin="*")

or plug it into your wsgi pipeline via paste ini to let it serve by
waitress for instance:

::

    [app:myapp]
    use = egg:mysuperapp#app

    ###
    # wsgi server configuration
    ###

    [server:main]
    use = egg:waitress#main
    host = 0.0.0.0
    port = 6543

    [pipeline:main]
    pipeline =
        cors
        myapp

    [filter:cors]
    use = egg:wsgicors#middleware
    policy=free
    free_origin=copy
    free_headers=*
    free_methods=*
    free_maxage=180

    policy=subdom
    subdom_origin=example.com example2.com *.example.com
    subdom_headers=*
    subdom_methods=*
    subdom_maxage=180

Keywords are:

-  ``origin``
-  ``headers``
-  ``methods``
-  ``credentials``
-  ``maxage``

for ``origin``:

-  use ``copy`` which will copy whatever origin the request comes from
-  a space separated list of hostnames - they can also contain wildcards
   like ``*`` or ``?`` (fnmatch lib is used for matching). If a match is
   found the original host is returned.
-  any other literal will be be copied verbatim (like ``*`` for instance
   to allow every source)

for ``headers``:

-  use ``*`` which will allow whatever header is asked for
-  any other literal will be be copied verbatim (like ``*`` for instance
   to allow every source)

for ``methods``:

-  use ``*`` which will allow whatever method is asked for
-  any other literal will be be copied verbatim (like
   ``POST, PATCH, PUT, DELETE`` for instance)

for ``credentials``:

-  use ``true``
-  anything else will be ignored (that is no response header for
   ``Access-Control-Allow-Credentials`` is sent)

for ``maxage``:

-  give the number of seconds the answer can be used by a client,
   anything nonempty will be copied verbatim

As can be seen in the example above, a policy needs to be created with
the ``policy`` keyword. The options need then be prefixed with the
policy name and a ``_``.
