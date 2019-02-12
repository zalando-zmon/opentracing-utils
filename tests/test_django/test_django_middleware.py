
import opentracing

import pytest

import six

from mock import MagicMock

from opentracing.ext import tags
from basictracer import BasicTracer

from ..conftest import Recorder

from opentracing_utils import extract_span_from_django_request


@pytest.mark.skipif(six.PY2, reason='')
def skip_span(request, view_func, view_args, view_kwargs):
    if view_func.__name__ == 'home':
        return True
    return False


def operation_name(request, view_func, view_args, view_kwargs):
    return 'custom-op-name'


def get_recorder():
    recorder = Recorder()
    t = BasicTracer(recorder=recorder)
    t.register_required_propagators()
    opentracing.tracer = t

    return recorder


@pytest.mark.skipif(six.PY2, reason='')
@pytest.mark.parametrize('url,method,status', (
    ('/', 'GET', 200),
    ('/', 'POST', 200),
    ('/notfound', 'GET', 404),
))
def test_request_home(client, url, method, status):
    recorder = get_recorder()

    m = client.get if method == 'GET' else client.post
    response = m(url)
    if status != 404:
        assert response.content == b'TRACED'

        assert len(recorder.spans) == 1

        assert recorder.spans[0].operation_name == 'home'
        assert recorder.spans[0].tags[tags.COMPONENT] == 'django'
        assert recorder.spans[0].tags[tags.HTTP_URL] == url
        assert recorder.spans[0].tags[tags.HTTP_METHOD] == method
        assert recorder.spans[0].tags[tags.HTTP_STATUS_CODE] == status


@pytest.mark.skipif(six.PY2, reason='')
def test_request_nested(client):
    recorder = get_recorder()

    response = client.get('/nested')
    assert response.content == b'NESTED'

    assert len(recorder.spans) == 2

    assert recorder.spans[1].operation_name == 'nested'
    assert recorder.spans[1].tags[tags.COMPONENT] == 'django'
    assert recorder.spans[1].tags[tags.HTTP_URL] == '/nested'
    assert recorder.spans[1].tags[tags.HTTP_METHOD] == 'GET'
    assert recorder.spans[1].tags[tags.HTTP_STATUS_CODE] == 200

    assert recorder.spans[0].operation_name == 'nested_call'
    assert recorder.spans[0].tags['nested'] is True
    assert recorder.spans[0].context.trace_id == recorder.spans[1].context.trace_id
    assert recorder.spans[0].parent_id == recorder.spans[1].context.span_id


@pytest.mark.skipif(six.PY2, reason='')
def test_request_user(client):
    recorder = get_recorder()

    response = client.get('/user')
    assert response.content == b'USER'

    assert len(recorder.spans) == 1

    assert recorder.spans[0].operation_name == 'user'
    assert recorder.spans[0].tags[tags.COMPONENT] == 'django'
    assert recorder.spans[0].tags[tags.HTTP_URL] == '/user'
    assert recorder.spans[0].tags[tags.HTTP_METHOD] == 'GET'
    assert recorder.spans[0].tags[tags.HTTP_STATUS_CODE] == 200


@pytest.mark.skipif(six.PY2, reason='')
def test_request_error(client):
    recorder = get_recorder()

    with pytest.raises(RuntimeError):
        client.get('/error')

    assert len(recorder.spans) == 1

    assert recorder.spans[0].operation_name == 'error'
    assert recorder.spans[0].tags[tags.COMPONENT] == 'django'
    assert recorder.spans[0].tags[tags.HTTP_URL] == '/error'
    assert recorder.spans[0].tags[tags.HTTP_METHOD] == 'GET'
    assert recorder.spans[0].tags[tags.HTTP_STATUS_CODE] == 500
    assert recorder.spans[0].tags['error'] is True


@pytest.mark.skipif(six.PY2, reason='')
@pytest.mark.parametrize('op_name', ('tests.test_django.test_django_middleware.skip_span', skip_span))
def test_request_skip_span(client, settings, op_name):
    recorder = get_recorder()

    settings.OPENTRACING_UTILS_SKIP_SPAN_CALLABLE = op_name

    response = client.get('/')
    assert response.content == b'TRACED'

    assert len(recorder.spans) == 0

    response = client.get('/user')
    assert response.content == b'USER'

    assert len(recorder.spans) == 1

    assert recorder.spans[0].operation_name == 'user'
    assert recorder.spans[0].tags[tags.COMPONENT] == 'django'
    assert recorder.spans[0].tags[tags.HTTP_URL] == '/user'
    assert recorder.spans[0].tags[tags.HTTP_METHOD] == 'GET'
    assert recorder.spans[0].tags[tags.HTTP_STATUS_CODE] == 200


@pytest.mark.skipif(six.PY2, reason='')
@pytest.mark.parametrize('op_name', ('tests.test_django.test_django_middleware.operation_name', operation_name))
def test_request_operation_name(client, settings, op_name):
    recorder = get_recorder()

    settings.OPENTRACING_UTILS_OPERATION_NAME_CALLABLE = op_name

    response = client.get('/user')
    assert response.content == b'USER'

    assert len(recorder.spans) == 1

    assert recorder.spans[0].operation_name == 'custom-op-name'
    assert recorder.spans[0].tags[tags.COMPONENT] == 'django'
    assert recorder.spans[0].tags[tags.HTTP_URL] == '/user'
    assert recorder.spans[0].tags[tags.HTTP_METHOD] == 'GET'
    assert recorder.spans[0].tags[tags.HTTP_STATUS_CODE] == 200


@pytest.mark.skipif(six.PY2, reason='')
@pytest.mark.parametrize('default_tags', (
    {},
    '',
    None,
    [],
    {'tag-1': 'val-1', 'tag-2': 'val-2'},
))
def test_request_default_tags(client, settings, default_tags):
    recorder = get_recorder()

    settings.OPENTRACING_UTILS_DEFAULT_TAGS = default_tags

    response = client.get('/user')
    assert response.content == b'USER'

    assert len(recorder.spans) == 1

    assert recorder.spans[0].operation_name == 'user'
    assert recorder.spans[0].tags[tags.COMPONENT] == 'django'
    assert recorder.spans[0].tags[tags.HTTP_URL] == '/user'
    assert recorder.spans[0].tags[tags.HTTP_METHOD] == 'GET'
    assert recorder.spans[0].tags[tags.HTTP_STATUS_CODE] == 200

    if type(default_tags) is dict:
        for t, v in default_tags.items():
            recorder.spans[0].tags[t] == v


@pytest.mark.skipif(six.PY2, reason='')
@pytest.mark.parametrize('error_4xx', (True, False))
def test_request_ignore_4xx(client, settings, error_4xx):
    recorder = get_recorder()

    settings.OPENTRACING_UTILS_ERROR_4XX = error_4xx

    client.get('/bad')

    assert len(recorder.spans) == 1

    assert recorder.spans[0].operation_name == 'bad_request'
    assert recorder.spans[0].tags[tags.COMPONENT] == 'django'
    assert recorder.spans[0].tags[tags.HTTP_URL] == '/bad'
    assert recorder.spans[0].tags[tags.HTTP_METHOD] == 'GET'
    assert recorder.spans[0].tags[tags.HTTP_STATUS_CODE] == 400

    assert ('error' in recorder.spans[0].tags) is error_4xx


@pytest.mark.skipif(six.PY2, reason='')
def test_request_propagated(monkeypatch, client):
    recorder = get_recorder()

    propagated_span = MagicMock()
    propagated_span.context.trace_id = 123
    propagated_span.context.span_id = 123456

    def extract(fmt, carrier):
        assert 'x-trace-id' in carrier
        return propagated_span

    monkeypatch.setattr('opentracing.tracer.extract', extract)

    response = client.get('/', HTTP_X_TRACE_ID=123)  # HTTP_X_TRACE_ID is only used to test headers transformation!
    assert response.content == b'TRACED'

    assert recorder.spans[0].context.trace_id == propagated_span.context.trace_id
    assert recorder.spans[0].parent_id == propagated_span.context.span_id

    assert recorder.spans[0].operation_name == 'home'
    assert recorder.spans[0].tags[tags.COMPONENT] == 'django'
    assert recorder.spans[0].tags[tags.HTTP_URL] == '/'
    assert recorder.spans[0].tags[tags.HTTP_METHOD] == 'GET'
    assert recorder.spans[0].tags[tags.HTTP_STATUS_CODE] == 200


@pytest.mark.skipif(six.PY2, reason='')
def test_extract_span():
    request = MagicMock()

    request.current_span = '1'

    assert '1' == extract_span_from_django_request(request)
