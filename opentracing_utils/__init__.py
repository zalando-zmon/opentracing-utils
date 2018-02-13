from pkg_resources import get_distribution

from opentracing_utils.decorators import trace

from opentracing_utils.tracers import init_opentracing_tracer
from opentracing_utils.tracers import OPENTRACING_BASIC, OPENTRACING_INSTANA, OPENTRACING_LIGHTSTEP, OPENTRACING_JAEGER

from opentracing_utils.span import get_active_span, get_span_from_kwargs, extract_span, extract_span_from_kwargs

from opentracing_utils.libs._requests import trace_requests
from opentracing_utils.libs._flask import trace_flask, extract_span_from_flask_request


__version__ = get_distribution('opentracing-utils').version


__all__ = (
    'extract_span',
    'extract_span_from_kwargs',
    'extract_span_from_flask_request',
    'get_active_span',
    'get_span_from_kwargs',
    'init_opentracing_tracer',
    'trace',
    'trace_flask',
    'trace_requests',

    'OPENTRACING_BASIC',
    'OPENTRACING_INSTANA',
    'OPENTRACING_JAEGER',
    'OPENTRACING_LIGHTSTEP',
)
