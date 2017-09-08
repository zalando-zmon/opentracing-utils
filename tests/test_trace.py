import pytest

import opentracing
from basictracer import BasicTracer

from .conftest import Recorder
from opentracing_utils import trace


def is_span_in_kwargs(**kwargs):
    for _, v in kwargs.items():
        if isinstance(v, opentracing.Span):
            return True

    return False


def test_trace_single():

    @trace()
    def f1():
        pass

    recorder = Recorder()
    opentracing.tracer = BasicTracer(recorder=recorder)

    test_span = opentracing.tracer.start_span(operation_name='test_trace')

    with test_span:
        f1()
        f1()
        f1()

    assert len(recorder.spans) == 4
    for span in recorder.spans[:3]:
        assert span.context.trace_id == test_span.context.trace_id
        assert span.parent_id == test_span.context.span_id


def test_trace_method():

    class C:
        @trace()
        def func(self):
            pass

    recorder = Recorder()
    opentracing.tracer = BasicTracer(recorder=recorder)

    test_span = opentracing.tracer.start_span(operation_name='test_trace')

    with test_span:
        C().func()

    assert len(recorder.spans) == 2

    assert recorder.spans[0].context.trace_id == test_span.context.trace_id
    assert recorder.spans[0].parent_id == recorder.spans[1].context.span_id


@pytest.mark.parametrize('pass_span', (False, True))
def test_trace_nested(pass_span):

    @trace(pass_span=pass_span)
    def parent(**kwargs):
        assert is_span_in_kwargs(**kwargs) is pass_span
        nested()

    @trace(pass_span=pass_span)
    def nested(**kwargs):
        assert is_span_in_kwargs(**kwargs) is pass_span

    recorder = Recorder()
    opentracing.tracer = BasicTracer(recorder=recorder)

    test_span = opentracing.tracer.start_span(operation_name='test_trace')

    with test_span:
        parent()

    assert len(recorder.spans) == 3

    assert recorder.spans[0].context.trace_id == test_span.context.trace_id
    assert recorder.spans[0].parent_id == recorder.spans[1].context.span_id

    assert recorder.spans[1].context.trace_id == test_span.context.trace_id
    assert recorder.spans[1].parent_id == test_span.context.span_id

    assert recorder.spans[-1].parent_id is None


def test_trace_nested_with_args():

    @trace()
    def parent(arg1, arg2):
        nested(arg1)

    @trace()
    def nested(arg1, **kwargs):
        assert is_span_in_kwargs(**kwargs) is False

    @trace(pass_span=True)
    def expect_span(**kwargs):
        assert is_span_in_kwargs(**kwargs) is True

    recorder = Recorder()
    opentracing.tracer = BasicTracer(recorder=recorder)

    test_span = opentracing.tracer.start_span(operation_name='test_trace')

    with test_span:
        parent(1, 2)

        expect_span()

    assert len(recorder.spans) == 4

    assert recorder.spans[0].context.trace_id == test_span.context.trace_id
    assert recorder.spans[0].parent_id == recorder.spans[1].context.span_id

    assert recorder.spans[1].context.trace_id == test_span.context.trace_id
    assert recorder.spans[1].parent_id == test_span.context.span_id

    assert recorder.spans[-1].parent_id is None


def test_trace_mutliple_spans():

    @trace()
    def parent():
        nested()

    @trace()
    def nested(**kwargs):
        assert is_span_in_kwargs(**kwargs) is False

    recorder = Recorder()
    opentracing.tracer = BasicTracer(recorder=recorder)

    test_span_first = opentracing.tracer.start_span(operation_name='test_trace_first')

    with test_span_first:
        parent()

    assert len(recorder.spans) == 3

    assert recorder.spans[0].context.trace_id == test_span_first.context.trace_id
    assert recorder.spans[0].parent_id == recorder.spans[1].context.span_id

    assert recorder.spans[1].context.trace_id == test_span_first.context.trace_id
    assert recorder.spans[1].parent_id == test_span_first.context.span_id

    assert recorder.spans[-1].parent_id is None
    assert recorder.spans[-1].operation_name == 'test_trace_first'

    # reset recorder
    recorder.reset()
    test_span_second = opentracing.tracer.start_span(operation_name='test_trace_second')

    with test_span_second:
        nested(span=test_span_second)

    assert len(recorder.spans) == 2

    assert recorder.spans[0].context.trace_id == test_span_second.context.trace_id
    assert recorder.spans[0].parent_id == recorder.spans[1].context.span_id

    assert recorder.spans[-1].parent_id is None
    assert recorder.spans[-1].operation_name == 'test_trace_second'


def test_trace_nested_broken_traces():

    @trace()
    def f1():
        pass

    @trace()
    def f2():
        pass

    recorder = Recorder()
    opentracing.tracer = BasicTracer(recorder=recorder)

    test_span = opentracing.tracer.start_span(operation_name='test_trace')

    with test_span:
        f1()

        broken_span = opentracing.tracer.start_span(operation_name='broken_trace')
        with broken_span:
            f1(span=broken_span)

        # Broken traces does not work with stack inspection, it is better to pass the span in this case!
        f2(span=test_span)

    assert len(recorder.spans) == 5

    assert recorder.spans[0].context.trace_id == test_span.context.trace_id
    assert recorder.spans[0].parent_id == recorder.spans[-1].context.span_id

    assert recorder.spans[1].context.trace_id == broken_span.context.trace_id
    assert recorder.spans[1].parent_id == recorder.spans[2].context.span_id

    assert recorder.spans[3].context.trace_id == test_span.context.trace_id
    assert recorder.spans[3].parent_id == recorder.spans[-1].context.span_id

    assert recorder.spans[2].parent_id is None
    assert recorder.spans[2].operation_name == 'broken_trace'

    assert recorder.spans[-1].parent_id is None
    assert recorder.spans[-1].operation_name == 'test_trace'
