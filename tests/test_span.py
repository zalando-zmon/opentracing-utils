import opentracing

from mock import MagicMock

from opentracing.ext import tags as opentracing_tags
from basictracer import BasicTracer


from opentracing_utils.span import get_new_span, adjust_span, extract_span_from_kwargs
from opentracing_utils.span import DEFAULT_SPAN_ARG_NAME


def test_get_new_span():

    def f():
        pass

    span_arg_name, span = get_new_span(f, [], {})

    assert DEFAULT_SPAN_ARG_NAME == span_arg_name
    assert isinstance(span, opentracing.Span)


def test_get_new_span_with_extractor():
    opentracing.tracer = BasicTracer()
    parent_span = opentracing.tracer.start_span()

    extractor = MagicMock()
    extractor.return_value = parent_span

    ctx = '123'

    def f(ctx, extras=True):
        pass

    span_arg_name, span = get_new_span(f, [ctx], {'extras': True}, span_extractor=extractor, inspect_stack=False)

    assert DEFAULT_SPAN_ARG_NAME == span_arg_name
    assert span.parent_id == parent_span.context.span_id
    extractor.assert_called_with(ctx, extras=True)


def test_get_new_span_with_failing_extractor():
    def f():
        pass

    def extractor():
        raise RuntimeError('Failed')

    span_arg_name, span = get_new_span(f, [], {}, span_extractor=extractor)

    assert DEFAULT_SPAN_ARG_NAME == span_arg_name
    assert span.parent_id is None


def test_adjust_span(monkeypatch):
    span = MagicMock()
    span.set_tag.side_effect = [Exception, None, None]

    adjust_span(span, 'op_name', 'component', {'tag1': '1', 'tag2': '2'})

    span.set_tag.assert_called_with(opentracing_tags.COMPONENT, 'component')
    span.set_operation_name.assert_called_with('op_name')


def test_extract_span_from_kwargs(monkeypatch):
    span = opentracing.tracer.start_span(operation_name='test_op')

    extracted = extract_span_from_kwargs(span=span, x=1, y='some-value')

    assert extracted == span
