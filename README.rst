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
* Context agnostic, so no external **context implementation** dependency (no tornado, Flask, Django etc ...).
* Try to be less verbose - just add the ``@trace`` decorator.
* Could be more verbose when needed, without complexity - just accept ``**kwargs`` and get the span passed to your traced functions via ``@trace(pass_span=True)``.
* Support asyncio/async-await coroutines. (drop support for py2.7)
* Support **gevent**.
* Ability to add OpenTracing support to external libs/clients:

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
^^^^^^^^^^^^^

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


@trace_async decorator
----------------------

NOT SUPPORTED AT THE MOMENT

.. code-block:: python

    import asyncio

    import opentracing
    from opentracing_utils import trace, trace_async, extract_span

    loop = asyncio.get_event_loop()

    # decorate all your functions that require tracing

    # Normal traced function
    @trace()
    def trace_me():
        pass

    # Async function expecting the span to be passed down in ``kwargs``
    @trace_async(pass_span=True)
    async def send_email(user, **kwargs):
        current_span = extract_span(**kwargs)

        current_span.set_operation_name('send.email.{}'.format(user.id))
        current_span.set_tag('user.id', user.id)

        # then send email - will not be correlated to ``current_span``
        await send_email_payload(user, 'new email')


    # Async function
    @trace_async()
    async def just_wait():
        await asyncio.sleep(1)


    async def start_fresh():

        user = {'id': 1}

        async_span = opentracing.tracer.start_span(operation_name='start.fresh')
        with async_span:

            # traced async op - IMPORTANT: ``async_span`` must be passed to the async function as kwarg
            a1 = asyncio.ensure_future(send_email(user, span=async_span))

            # normal, traced blocking function
            trace_me()

            # Always pass the ``async_span`` as kwarg even if the ``just_wait`` function does not accept any ``kwargs``
            a2 = asyncio.ensure_future(just_wait(span=async_span))

            await asyncio.wait_for(a1, 20)
            await asyncio.wait_for(a2, 2)


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
