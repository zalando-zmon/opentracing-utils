import opentracing
from basictracer import BasicTracer

from .conftest import Recorder
from opentracing_utils import trace


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


def test_trace_nested():

    @trace()
    def parent():
        nested()

    @trace()
    def nested():
        pass

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
