import logging

try:
    import requests
except ImportError:  # pragma: no cover
    pass
else:
    __requests_http_send = requests.adapters.HTTPAdapter.send

import opentracing
from opentracing import Format
from opentracing.ext import tags as opentracing_tags

from opentracing_utils.decorators import trace
from opentracing_utils.span import extract_span


OPERATION_NAME_PREFIX = 'requests.send'

logger = logging.getLogger(__name__)


def trace_requests():
    """Patch requests library with Opentracing"""
    requests.adapters.HTTPAdapter.send = requests_send_wrapper


@trace(pass_span=True)
def requests_send_wrapper(self, request, **kwargs):
    op_name = '{}.{}'.format(OPERATION_NAME_PREFIX, request.method)

    k, request_span = extract_span(inspect_stack=False, **kwargs)
    kwargs.pop(k, None)

    if request_span:
        (request_span
            .set_operation_name(op_name)
            .set_tag(opentracing_tags.HTTP_URL, request.url)
            .set_tag(opentracing_tags.HTTP_METHOD, request.method))

        # Inject our current span context to outbound request
        try:
            carrier = {}
            opentracing.tracer.inject(request_span.context, Format.HTTP_HEADERS, carrier)
            for k, v in carrier.items():
                request.add_header(k, v)
        except opentracing.UnsupportedFormatException:
            logger.error('Failed to inject span context in request!')

        resp = __requests_http_send(self, request, **kwargs)
        request_span.set_tag(opentracing_tags.HTTP_STATUS_CODE, resp.status_code)

        return resp
    else:
        return __requests_http_send(self, request, **kwargs)
