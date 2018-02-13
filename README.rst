========================
OPENTRACING PYTHON UTILS
========================

**Early stage WIP + Experimental**


.. image:: https://api.travis-ci.org/zalando-zmon/opentracing-utils.svg?branch=master
  :target: https://travis-ci.org/zalando-zmon/opentracing-utils

.. image:: https://codecov.io/gh/zalando-zmon/opentracing-utils/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/zalando-zmon/opentracing-utils


Convenient utilities for adding `OpenTracing <http://opentracing.io>`_ support in your python projects.

Features
========

``opentracing-utils`` should provide and aims at the following:

* No extrenal dependencies, only `opentracing-python <https://github.com/opentracing/opentracing-python>`_.
* No threadlocals. Either pass spans safely or fallback to callstack frames inspection!
* Context agnostic, so no external **context implementation** dependency (no Tornado, Flask, Django etc ...).
* Try to be less verbose - just add the ``@trace`` decorator.
* Could be more verbose when needed, without complexity - just accept ``**kwargs`` and get the span passed to your traced functions via ``@trace(pass_span=True)``.
* Support asyncio/async-await coroutines. (drop support for py2.7)
* Support **gevent**.
* Ability to add OpenTracing support to external libs/frameworks/clients:

    * requests (via ``trace_requests()``)
    * TODO ...


Install
=======

Using pip

.. code-block:: bash

    pip install -U -e git+ssh://git@github.com/zalando-zmon/opentracing-utils.git#egg=opentracing_utils


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

    from opentracing_utils import trace, extract_span

    # decorate all your functions that require tracing

    # Normal traced function
    @trace()
    def trace_me():
        pass


    # Traced function with access to created span in ``kwargs``
    @trace(operation_name='user.operation', pass_span=True)
    def user_operation(user, op, **kwargs):
        current_span = extract_span(**kwargs)

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


External libraries and clients
------------------------------

Requests
^^^^^^^^

For tracing `requests <https://github.com/requests/requests>`_ client library for all outgoing requests.

.. code-block:: python

    # trace_requests should be called as early as possible, before importing requests
    from opentracing_utils import trace_requests
    trace_requests()  # noqa

    # In case you want to include default span tags to be sent with every outgoing request
    # trace_requests(default_tags={'account_id': '123'})

    import requests

    def main():

        span = opentracing.tracer.start_span(operation_name='main')
        with span:
            # Following call will be traced, and parent span will be inherited and propagated via HTTP headers.
            requests.get('https://example.org')


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
