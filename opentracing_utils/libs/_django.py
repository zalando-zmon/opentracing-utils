"""
Django OpenTracing middleware.

This is a slightly modified version of the middleware implemented in:
https://github.com/opentracing-contrib/python-django [BSD 3-Clause]
"""
import traceback
import opentracing


settings = None  # noqa

try:
    from django.conf import settings
    from django.utils.deprecation import MiddlewareMixin
except ImportError:  # pragma: no cover
    MiddlewareMixin = object

try:
    from django.utils.module_loading import import_string
except ImportError:  # pragma: no cover
    try:
        from django.utils.module_loading import import_by_path as import_string
    except ImportError:  # pragma: no cover
        pass

from opentracing.ext import tags as ot_tags

from opentracing_utils.common import sanitize_url


class OpenTracingHttpMiddleware(MiddlewareMixin):

    def __init__(self, get_response=None):
        self.get_response = get_response

        self._default_tags = getattr(settings, 'OPENTRACING_UTILS_DEFAULT_TAGS', {})
        if type(self._default_tags) is not dict:
            self._default_tags = {}

        error_4xx = bool(getattr(settings, 'OPENTRACING_UTILS_ERROR_4XX', True))
        self._min_error_code = 400 if error_4xx else 500

        op_name_str = getattr(settings, 'OPENTRACING_UTILS_OPERATION_NAME_CALLABLE', '')
        if callable(op_name_str):
            self._op_name_callable = op_name_str
        else:
            self._op_name_callable = import_string(op_name_str) if op_name_str else None

        skip_span_str = getattr(settings, 'OPENTRACING_UTILS_SKIP_SPAN_CALLABLE', '')
        if callable(skip_span_str):
            self._skip_span_callable = skip_span_str
        else:
            self._skip_span_callable = import_string(skip_span_str) if skip_span_str else None

    def process_view(self, request, view_func, view_args, view_kwargs):
        if self._skip_span_callable and self._skip_span_callable(request, view_func, view_args, view_kwargs):
            return

        headers_carrier = self._get_headers(request)

        op_name = (self._op_name_callable(request, view_func, view_args, view_kwargs) if self._op_name_callable
                   else view_func.__name__)

        span = None
        try:
            span_ctx = opentracing.tracer.extract(opentracing.Format.HTTP_HEADERS, headers_carrier)
            span = opentracing.tracer.start_span(operation_name=op_name, child_of=span_ctx)
        except (opentracing.InvalidCarrierException, opentracing.SpanContextCorruptedException):
            span = opentracing.tracer.start_span(operation_name=op_name, tags={'django-no-propagation': True})

        span.set_tag(ot_tags.COMPONENT, 'django')
        span.set_tag(ot_tags.SPAN_KIND, ot_tags.SPAN_KIND_RPC_SERVER)
        span.set_tag(ot_tags.HTTP_METHOD, request.method)
        span.set_tag(ot_tags.HTTP_URL, sanitize_url(request.get_full_path()))

        # Default tags
        for k, v in self._default_tags.items():
            try:
                span.set_tag(k, v)
            except Exception:  # pragma: no cover
                pass

        request.current_span = span

    def process_exception(self, request, exception):
        self._finish_tracing(request, exception=exception)

    def process_response(self, request, response):
        self._finish_tracing(request, response=response)
        return response

    def _get_headers(self, request):
        headers = {}

        for k, v in request.META.items():
            k = k.lower().replace('_', '-')
            k = k.replace('http-', '') if k.startswith('http-') else k  # remove Django magic prefix!
            headers[k] = v

        return headers

    def _finish_tracing(self, request, response=None, exception=None):
        current_span = getattr(request, 'current_span', None)
        if not current_span:
            return

        if response:
            current_span.set_tag(ot_tags.HTTP_STATUS_CODE, response.status_code)

            if response.status_code >= self._min_error_code:
                current_span.set_tag('error', True)

            current_span.finish()
        elif exception:
            current_span.set_tag('error', True)
            current_span.log_kv({
                'error.kind': str(exception),
                'stack': traceback.format_exc(),
            })


def extract_span_from_django_request(request, *args, **kwargs):
    """
    Safe utility function to extract the ``current_span`` from ``HttpRequest``. Compatible with ``@trace`` decorator.
    """
    try:
        return getattr(request, 'current_span', None)
    except Exception:  # pragma: no cover
        pass

    return None  # pragma: no cover
