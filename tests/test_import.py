from opentracing_utils import trace, extract_span
from opentracing_utils import trace_requests


__all__ = (
    'extract_span',
    'trace',
    'trace_requests',
)


def test_dummy():
    assert trace
    assert extract_span
