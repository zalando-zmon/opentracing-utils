from django.http import HttpResponse

from opentracing_utils import trace, extract_span_from_django_request, extract_span_from_kwargs


def home(request):
    return HttpResponse('TRACED')


def user(request):
    return HttpResponse('USER')


def error(request):
    raise RuntimeError('Failed request')


def bad_request(request):
    return HttpResponse(status=400)


@trace(span_extractor=extract_span_from_django_request, operation_name='nested_call', pass_span=True)
def nested(request, *args, **kwargs):
    current_span = extract_span_from_kwargs(**kwargs)
    current_span.set_tag('nested', True)

    return HttpResponse('NESTED')
