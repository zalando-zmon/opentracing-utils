import opentracing

from basictracer import BasicTracer

from opentracing_utils.span import get_new_span
from opentracing_utils.span import DEFAULT_SPAN_ARG_NAME


def test_get_new_span():

    def f():
        pass

    span_arg_name, span = get_new_span(f)

    assert DEFAULT_SPAN_ARG_NAME == span_arg_name
    assert isinstance(span, opentracing.Span)


def test_get_new_span_with_extractor():
    opentracing.tracer = BasicTracer()
    parent_span = opentracing.tracer.start_span()

    def f():
        pass

    def extractor():
        return parent_span

    span_arg_name, span = get_new_span(f, span_extractor=extractor)

    assert DEFAULT_SPAN_ARG_NAME == span_arg_name
    assert span.parent_id == parent_span.context.span_id


def test_get_new_span_with_failing_extractor():
    def f():
        pass

    def extractor():
        raise RuntimeError('Failed')

    span_arg_name, span = get_new_span(f, span_extractor=extractor)

    assert DEFAULT_SPAN_ARG_NAME == span_arg_name
    assert span.parent_id is None
