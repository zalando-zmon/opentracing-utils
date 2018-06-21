========================
OPENTRACING PYTHON UTILS
========================

**Early stage WIP + Experimental**


.. image:: https://api.travis-ci.org/zalando-zmon/opentracing-utils.svg?branch=master
  :target: https://travis-ci.org/zalando-zmon/opentracing-utils
  :alt: Build status

.. image:: https://codecov.io/gh/zalando-zmon/opentracing-utils/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/zalando-zmon/opentracing-utils
  :alt: Code coverage

.. image:: https://img.shields.io/pypi/v/opentracing-utils.svg
   :target: https://pypi.python.org/pypi/opentracing-utils/
   :alt: Latest PyPI version

.. image:: https://img.shields.io/pypi/l/opentracing-utils.svg
   :target: https://pypi.python.org/pypi/opentracing-utils/
   :alt: License

.. image:: https://img.shields.io/badge/OpenTracing-enabled-blue.svg
   :target: http://opentracing.io
   :alt: OpenTracing enabled

Convenient utilities for adding `OpenTracing <http://opentracing.io>`_ support in your python projects.

Features
========

``opentracing-utils`` should provide and aims at the following:

* No extrenal dependencies, only `opentracing-python <https://github.com/opentracing/opentracing-python>`_.
* No threadlocals. Either pass spans explicitly or fallback to callstack frames inspection!
* Context agnostic, so no external **context implementation** dependency (no Tornado, Flask, Django etc ...).
* Try to be less verbose - just add the ``@trace`` decorator.
* Could be more verbose when needed, without complexity - just accept ``**kwargs`` and get the span passed to your traced functions via ``@trace(pass_span=True)``.
* Support asyncio/async-await coroutines. (drop support for py2.7)
* Support **gevent**.
* Ability to add OpenTracing support to external libs/frameworks/clients:

    * Flask (via ``trace_flask()``)
    * Requests (via ``trace_requests()``)
    * SQLAlchemy (via ``trace_sqlalchemy()``)

Install
=======

Using pip (not released yet to PyPi)

.. code-block:: bash

    pip install -U opentracing-utils


or by cloning the repo

.. code-block:: bash

    python setup.py install


Usage
=====

init_opentracing_tracer
-----------------------

The first step needed in OpenTracing instrumentation is to initialize a tracer. Each vendor defines how the tracer can be initialized. Currently the following tracers are supported:

* `BasicTracer <https://github.com/opentracing/basictracer-python>`_
* `Instana <https://github.com/instana/python-sensor>`_
* `Jaeger <https://github.com/jaegertracing/jaeger-client-python/>`_
* `LightStep <https://github.com/lightstep/lightstep-tracer-python>`_

BasicTracer
^^^^^^^^^^^

This is the basic noop tracer. It could be initialized with a recorder (e.g. `Memory Recorder <https://github.com/opentracing/basictracer-python/blob/master/basictracer/recorder.py#L21>`_), which can be useful in debugging and playing around with OpenTracing concepts.

.. code-block:: python

    import opentracing
    from opentracing_utils import OPENTRACING_BASIC, init_opentracing_tracer

    # Initialize upon application start
    init_opentracing_tracer(OPENTRACING_BASIC)

    # It is possible to pass custom recorder
    # init_opentracing_tracer(OPENTRACING_BASIC, recorder=custom_recorder)

    # Now use the opentracing.tracer
    root_span = opentracing.tracer.start_span(operation_name='root_span')

Instana
^^^^^^^

Config Vars
~~~~~~~~~~~

The following config variables can be used in initialization if set as env variables

OPENTRACING_INSTANA_SERVICE
  The service name.

.. code-block:: python

    import opentracing
    from opentracing_utils import OPENTRACING_INSTANA, init_opentracing_tracer

    # Initialize upon application start
    init_opentracing_tracer(OPENTRACING_INSTANA)

    # It is possible to pass args
    # init_opentracing_tracer(OPENTRACING_INSTANA, service='python-server')

    # Now use the opentracing.tracer
    root_span = opentracing.tracer.start_span(operation_name='root_span')

Jaeger
^^^^^^

Config Vars
~~~~~~~~~~~

The following config variables can be used in initialization if set as env variables

OPENTRACING_JAEGER_SERVICE_NAME
  The service name.

.. note::

    Jaeger configuration should be passed by the instrumentated code. Default is ``{}``.


.. code-block:: python

    import opentracing
    from opentracing_utils import OPENTRACING_JAEGER, init_opentracing_tracer

    # Initialize upon application start
    init_opentracing_tracer(OPENTRACING_JAEGER)

    # It is possible to pass args
    # init_opentracing_tracer(OPENTRACING_JAEGER, service_name='python-server', config=custom_config_with_sampling)

    # Now use the opentracing.tracer
    root_span = opentracing.tracer.start_span(operation_name='root_span')


LightStep
^^^^^^^^^

Config Vars
~~~~~~~~~~~

The following config variables can be used in initialization if set as env variables

OPENTRACING_LIGHTSTEP_COMPONENT_NAME
  The component name.

OPENTRACING_LIGHTSTEP_ACCESS_TOKEN
  The LightStep collector access token.

OPENTRACING_LIGHTSTEP_COLLECTOR_HOST
  The LightStep collector host. Default: ``collector.lightstep.com``.

OPENTRACING_LIGHTSTEP_COLLECTOR_PORT
  The LightStep collector port (``int``). Default: ``443``.

OPENTRACING_LIGHTSTEP_VERBOSITY
  The verbosity of the tracer (``int``). Default: ``0``.

.. code-block:: python

    import opentracing
    from opentracing_utils import OPENTRACING_LIGHTSTEP, init_opentracing_tracer

    # Initialize upon application start
    init_opentracing_tracer(OPENTRACING_LIGHTSTEP)

    # It is possible to pass args
    # init_opentracing_tracer(OPENTRACING_LIGHTSTEP, component_name='python-server', access_token='123', collector_host='production-collector.com')

    # Now use the opentracing.tracer
    root_span = opentracing.tracer.start_span(operation_name='root_span')


@trace decorator
----------------

.. code-block:: python

    from opentracing_utils import trace, extract_span_from_kwargs

    # decorate all your functions that require tracing

    # Normal traced function
    @trace()
    def trace_me():
        pass


    # Traced function with access to created span in ``kwargs``
    @trace(operation_name='user.operation', pass_span=True)
    def user_operation(user, op, **kwargs):
        current_span = extract_span_from_kwargs(**kwargs)

        current_span.set_tag('user.id', user.id)

        # Then do stuff ...

        # trace_me will have ``current_span`` as its parent.
        trace_me()

    # Traced function using ``follows_from`` instead of ``child_of`` reference.
    @trace(use_follows_from=True)
    def trace_me_later():
        pass


    # Start a fresh trace - any parent spans will be ignored
    @trace(operation_name='epoch', ignore_parent_span=True)
    def start_fresh():

        user = {'id': 1}

        # trace decorator will handle trace heirarchy
        user_operation(user, 'create')

        # trace_me will have ``epoch`` span as its parent.
        trace_me()

Skip Spans
^^^^^^^^^^

In certain cases you might need to skip certain spans while using the ``@trace`` decorator.

.. code-block:: python

    def skip_this_span(arg1, arg2, **kwargs):
        if arg1 == 'special':
            # span should be skipped
            return True

        return False


    @trace(skip_span=skip_this_span)
    def traced(arg1, arg2):
        pass


    top_span = opentracing.tracer.start_span(operation_name='top_trace')
    with top_span:
        # this call will be traced and have a span!
        traced('open', 'tracing')

        # this call won't be traced and no span to be added!
        traced('special', 'tracing')


Broken traces
^^^^^^^^^^^^^

If you plan to break nested traces, then it is recommended to pass the span to traced functions

.. code-block:: python

    top_span = opentracing.tracer.start_span(operation_name='top_trace')
    with top_span:

        # This one gets ``top_span`` as parent span
        call_traced()

        # Here, we break the trace, since we create a new span with no parents
        broken_span = opentracing.tracer.start_span(operation_name='broken_trace')
        with broken_span:
            # This one gets ``broken_span`` as parent span (not consistent in 2.7 and 3.5)
            call_traced()

            # pass span as safer/guaranteed trace here
            call_traced(span=broken_span)

        # ISSUE: Due to stack call inspection, next call will get ``broken_span`` instead of ``top_span``, which is wrong!!
        call_traced()

        # To get the ``top_span`` as parent span, then pass it to the traced call
        call_traced(span=top_span)


Multiple traces
^^^^^^^^^^^^^^^

If you plan to use multiple traces then it is better to always pass the span as it is safer/guaranteed.

.. code-block:: python

    first_span = opentracing.tracer.start_span(operation_name='first_trace')
    with first_span:

        # This one gets ``first_span`` as parent span
        call_traced()

    second_span = opentracing.tracer.start_span(operation_name='second_trace')
    with second_span:

        # ISSUE: This one **could** get ``first_span`` as parent span (not consistent among Python versions)
        call_traced()

        # It is better to pass ``second_span`` explicitly
        call_traced(span=second_span)


Generators (yield)
^^^^^^^^^^^^^^^^^^

Using generators could get tricky and leads to invalid parent span inspection. It is recommended to pass the span explicitly.

.. code-block:: python

    @trace(pass_span=True)
    def gen(**kwargs):
        s = extract_span_from_kwargs(**kwargs)  # noqa

        # Extract and pass span to ``f2()`` otherwise it could get ``f1()`` as parent span instead of ``gen()``
        f2(span=s)

        for i in range(10):
            yield i

    @trace()
    def f2():
        pass

    @trace()
    def f1():
        list(gen())

    first_span = opentracing.tracer.start_span(operation_name='first_trace')
    with first_span:
        f1()


External libraries and clients
------------------------------

Flask
^^^^^

For tracing `Flask <http://flask.pocoo.org>`_ applications. This utility function adds a middleware that handles all incoming requests to the Flask application.

.. code-block:: python

    from opentracing_utils import trace_flask, extract_span_from_flask_request
    from flask import Flask

    app = Flask(__name__)

    trace_flask(app)

    # You can add default_tags or optionally treat 4xx responses as not an error (i.e no error tag in span)
    # trace_flask(app, default_tags={'always-there': True}, error_on_4xx=False)

    # Extract current span from request context
    def internal_function():
        current_span = extract_span_from_flask_request()

        current_span.set_tag('internal', True)

    # You can skip requests spans.
    def skip_health_checks(request):
        return request.path == '/health'

    # trace_flask(skip_span=skip_health_checks)



Requests
^^^^^^^^

For tracing `requests <https://github.com/requests/requests>`_ client library for all outgoing requests.

.. code-block:: python

    # trace_requests should be called as early as possible, before importing requests
    from opentracing_utils import trace_requests
    trace_requests()  # noqa

    # In case you want to include default span tags to be sent with every outgoing request.
    # trace_requests(default_tags={'account_id': '123'}, set_error_tag=False)

    # In case you want to keep the URL query args (masked by default in order to avoid leaking auth tokens etc...)
    # trace_requests(mask_url_query=False)

    # You can also mask URL path parameters (e.g. http://hostname/1 will be http://hostname/??/)
    # trace_requests(mask_url_path=True)

    # The library patches the requests library send functionality. This causes
    # all requests to propagate the span id's in the headers. Sometimes this is
    # undesireable so it's also possible to avoid tracing specific URL's or
    # endpoints. trace_requests accepts a list of regex patterns and matches the
    # request.url against these patterns, ignoring traces if any pattern matches.
    # trace_requests(ignore_patterns=[r".*hostname/endpoint"]

    import requests

    def main():

        span = opentracing.tracer.start_span(operation_name='main')
        with span:
            # Following call will be traced as a ``child span`` and propagated via HTTP headers.
            requests.get('https://example.org')

SQLAlchemy
^^^^^^^^^^

For tracing `SQLAlchemy <https://docs.sqlalchemy.org/en/latest/>`_ client library for all SQL queries.

.. code-block:: python

    # trace_sqlalchemy can be used to trace all SQL queries.
    # By default, span operation_name will be deduced from the query statement (e.g. select, update, delete).
    from opentracing_utils import trace_sqlalchemy
    trace_sqlalchemy()

    # You can customize the span operation_name via supplying a callable
    def get_sqlalchemy_span_op_name(conn, cursor, statement, parameters, context, executemany):
        # inspect statement and parameters etc...
        return 'custom_operation_name'
    # trace_sqlalchemy(operation_name=get_sqlalchemy_span_op_name)

    # By default, trace_sqlalchemy will not set error tags for SQL errors/exceptions. You can change that via ``set_error_tag`` param.
    # trace_sqlalchemy(set_error_tag=True)

    # you can skip spans for certain SQL queries.
    def skip_inserts(conn, cursor, statement, parameters, context, executemany):
        return statement.lower().startswith('insert')

    # trace_sqlalchemy(skip_span=skip_inserts)


License
=======

The MIT License (MIT)

Copyright (c) 2017 Zalando SE, https://tech.zalando.com

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
