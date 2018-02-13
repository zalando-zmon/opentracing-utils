from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()  # noqa

import logging
import urllib.parse as parse

try:
    import requests
except ImportError:  # pragma: no cover
    pass
else:
    __requests_http_send = requests.adapters.HTTPAdapter.send

import opentracing
from opentracing import Format
from opentracing.ext import tags as ot_tags

from opentracing_utils.decorators import trace
from opentracing_utils.span import extract_span

OPERATION_NAME_PREFIX = 'requests.send'

logger = logging.getLogger(__name__)


def trace_requests(default_tags=None):
    """Patch requests library with OpenTracing support.

    :param default_tags: Default span tags to included with every outgoing request.
    :type default_tags: dict
    """
    @trace(pass_span=True, tags=default_tags)
    def requests_send_wrapper(self, request, **kwargs):
        op_name = '{}.{}'.format(OPERATION_NAME_PREFIX, request.method)

        k, request_span = extract_span(inspect_stack=False, **kwargs)
        kwargs.pop(k, None)

        if request_span:
            (request_span
                .set_operation_name(op_name)
                .set_tag(ot_tags.HTTP_URL, sanitize_url(request.url))
                .set_tag(ot_tags.HTTP_METHOD, request.method)
                .set_tag(ot_tags.SPAN_KIND, ot_tags.SPAN_KIND_RPC_CLIENT))

            # Inject our current span context to outbound request
            try:
                carrier = {}
                opentracing.tracer.inject(request_span.context, Format.HTTP_HEADERS, carrier)
                request.headers.update(carrier)

                for k, v in carrier.items():
                    request_span.set_tag(k, v)

            except opentracing.UnsupportedFormatException:
                logger.error('Failed to inject span context in request!')

            resp = __requests_http_send(self, request, **kwargs)
            request_span.set_tag(ot_tags.HTTP_STATUS_CODE, resp.status_code)

            if not resp.ok:
                request_span.set_tag('error', True)

            return resp
        else:
            logger.warn('Failed to extract span during initiating request!')
            return __requests_http_send(self, request, **kwargs)

    # The Patch!
    requests.adapters.HTTPAdapter.send = requests_send_wrapper


def sanitize_url(url):
    parsed = parse.urlsplit(url)
    if not parsed.username and not parsed.password:
        return url

    host = '{}:{}'.format(parsed.hostname, parsed.port) if parsed.port else parsed.hostname
    components = parse.SplitResult(
        parsed.scheme, host, parsed.path, parsed.query, parsed.fragment)

    return parse.urlunsplit(components)
