from opentracing_utils import trace, extract_span_from_kwargs, trace_flask, trace_requests, remove_span_from_kwargs


def test_dummy():
    assert extract_span_from_kwargs
    assert remove_span_from_kwargs
    assert trace
    assert trace_flask
    assert trace_requests
