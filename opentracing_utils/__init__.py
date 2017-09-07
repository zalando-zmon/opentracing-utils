from pkg_resources import get_distribution

from opentracing_utils.decorators import trace
from opentracing_utils.span import get_active_span, get_span_from_kwargs, extract_span
from opentracing_utils.libs.requests_ import trace_requests


__version__ = get_distribution('opentracing-utils').version


__all__ = (
    'extract_span',
    'get_active_span',
    'get_span_from_kwargs',
    'trace',
    'trace_requests',
)
