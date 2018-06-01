from pkg_resources import get_distribution

from opentracing_utils.decorators import trace

from opentracing_utils.tracers import init_opentracing_tracer
from opentracing_utils.tracers import OPENTRACING_BASIC, OPENTRACING_INSTANA, OPENTRACING_LIGHTSTEP, OPENTRACING_JAEGER

from opentracing_utils.span import extract_span_from_kwargs, remove_span_from_kwargs

from opentracing_utils.libs._requests import trace_requests, sanitize_url
from opentracing_utils.libs._flask import trace_flask, extract_span_from_flask_request
from opentracing_utils.libs._sqlalchemy import trace_sqlalchemy


__version__ = get_distribution('opentracing-utils').version


__all__ = (
    'extract_span_from_flask_request',
    'extract_span_from_kwargs',
    'init_opentracing_tracer',
    'remove_span_from_kwargs',
    'sanitize_url',
    'trace',
    'trace_flask',
    'trace_requests',
    'trace_sqlalchemy',

    'OPENTRACING_BASIC',
    'OPENTRACING_INSTANA',
    'OPENTRACING_JAEGER',
    'OPENTRACING_LIGHTSTEP',
)
