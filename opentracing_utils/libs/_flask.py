import logging

import opentracing
from opentracing.ext import tags as ot_tags

try:
    from flask import request
except Exception:  # pragma: no cover
    pass

from opentracing_utils.common import sanitize_url


logger = logging.getLogger(__name__)


DEFUALT_REQUEST_ATTRIBUTES = ('url', 'method')
DEFUALT_RESPONSE_ATTRIBUTES = ('status_code',)


def trace_flask(app, request_attr=DEFUALT_REQUEST_ATTRIBUTES, response_attr=DEFUALT_RESPONSE_ATTRIBUTES,
                default_tags=None, error_on_4xx=True, mask_url_query=False, mask_url_path=False, operation_name=None,
                skip_span=None):
    """
    Add OpenTracing to Flask applications using ``before_request`` & ``after_request``.

    Will trace all incoming requests and add proper tags to spans.

    Will also add ``current_span`` to ``flask.request`` so other spans can access it further down the application
    functions.

    :param app: Flask application.
    :type app: Flask.App

    :param request_attr: Flask.Request attributes that can be set as span tags.
    :type request_attr: list

    :param response_attr: Flask.Response attributes that can be set as span tags.
    :type response_attr: list

    :param default_tags: Default span tags to included with every request span.
    :type default_tags: dict

    :param error_on_4xx: Set ``error`` tag in span if response is ``4xx`` or ``5xx``. Default is ``True``.
    :type error_on_4xx: bool

    :param mask_url_query: Mask URL query args in span. Default is False.
    :type mask_url_query: bool

    :param mask_url_path: Mask URL path in span. Default is False.
    :type mask_url_path: bool

    :param operation_name: Callable that returns the operation name of the request span. Default is None.
    :type operation_name: Callable[*args, **kwargs]

    :param skip_span: Callable to determine whether to skip this request span. If returned ``True`` then span
                      will be skipped. This is useful for excluding certain endpoints, like health checks.
    :type skip_span: Callable[*args, **kwargs]
    """

    min_error_code = 400 if error_on_4xx else 500

    @app.before_request
    def trace_request():
        if callable(skip_span) and skip_span(request):
            return

        op_name = request.endpoint if request.endpoint else request.path.strip('/').replace('/', '_')

        if callable(operation_name):
            op_name = operation_name() or op_name

        span = None
        headers_carrier = dict(request.headers.items())

        try:
            span_ctx = opentracing.tracer.extract(opentracing.Format.HTTP_HEADERS, headers_carrier)
            span = opentracing.tracer.start_span(operation_name=op_name, child_of=span_ctx)
        except (opentracing.InvalidCarrierException, opentracing.SpanContextCorruptedException):
            span = opentracing.tracer.start_span(operation_name=op_name, tags={'flask-no-propagation': True})

        if span is None:
            span = opentracing.tracer.start_span(op_name)

        if request_attr:
            for attr in request_attr:
                if hasattr(request, attr):
                    try:
                        tag_value = str(getattr(request, attr))
                        tag_key = attr

                        # Masking URL query and path params.
                        if attr == 'url':
                            tag_value = sanitize_url(
                                tag_value, mask_url_query=mask_url_query, mask_url_path=mask_url_path)
                            tag_key = ot_tags.HTTP_URL
                        elif attr == 'method':
                            tag_key = ot_tags.HTTP_METHOD

                        if tag_value:
                            span.set_tag(tag_key, tag_value)
                    except Exception:
                        pass

        if type(default_tags) is dict:
            for k, v in default_tags.items():
                try:
                    span.set_tag(k, v)
                except Exception:
                    pass

        span.set_tag(ot_tags.COMPONENT, 'flask')
        span.set_tag(ot_tags.SPAN_KIND, ot_tags.SPAN_KIND_RPC_SERVER)

        # Use ``flask.request`` as in process context.
        request.current_span = span

    @app.after_request
    def trace_response(response):
        try:
            if hasattr(request, 'current_span'):
                if response_attr:
                    for attr in response_attr:
                        if hasattr(response, attr):
                            tag_key = attr
                            if tag_key == 'status_code':
                                tag_key = ot_tags.HTTP_STATUS_CODE
                            request.current_span.set_tag(tag_key, str(getattr(response, attr)))

                if response.status_code >= min_error_code:
                    request.current_span.set_tag('error', True)

                request.current_span.finish()
        finally:
            return response


def extract_span_from_flask_request(*args, **kwargs):
    """
    Safe utility function to extract the ``current_span`` from ``flask.request``. Compatible with ``@trace`` decorator.
    """
    try:
        return getattr(request, 'current_span', None)
    except Exception:  # pragma: no cover
        pass

    return None
