from opentracing_utils import trace_requests

trace_requests()  # noqa

import requests
from requests import Response

import pytest
from mock import MagicMock

import opentracing
from opentracing.ext import tags

from basictracer import BasicTracer

from .conftest import Recorder
from opentracing_utils import trace
from opentracing_utils.libs.requests_ import sanitize_url


URL = 'http://example.com/'
CUSTOM_HEADER = 'X-CUSTOM'
CUSTOM_HEADER_VALUE = '123'


def assert_send_reuqest_mock(resp):

    def send_request_mock(self, request, **kwargs):
        assert 'ot-tracer-traceid' in request.headers
        assert 'ot-tracer-spanid' in request.headers

        assert request.headers[CUSTOM_HEADER] == CUSTOM_HEADER_VALUE

        return resp

    return send_request_mock


@pytest.mark.parametrize('status_code', (200, 302, 400, 500))
def test_trace_requests(monkeypatch, status_code):
    resp = Response()
    resp.status_code = status_code
    resp.url = URL

    monkeypatch.setattr('opentracing_utils.libs.requests_.__requests_http_send', assert_send_reuqest_mock(resp))

    @trace()
    def f1():
        pass

    recorder = Recorder()
    t = BasicTracer(recorder=recorder)
    t.register_required_propagators()
    opentracing.tracer = t

    top_span = opentracing.tracer.start_span(operation_name='top_span')

    with top_span:
        response = requests.get(URL, headers={CUSTOM_HEADER: CUSTOM_HEADER_VALUE})

        f1()

    assert len(recorder.spans) == 3

    assert recorder.spans[0].context.trace_id == top_span.context.trace_id
    assert recorder.spans[0].parent_id == recorder.spans[-1].context.span_id

    assert recorder.spans[-1].operation_name == 'top_span'

    assert response.status_code == resp.status_code
    assert recorder.spans[0].tags[tags.HTTP_STATUS_CODE] == resp.status_code
    assert recorder.spans[0].tags[tags.HTTP_URL] == URL
    assert recorder.spans[0].tags[tags.HTTP_METHOD] == 'GET'
    assert recorder.spans[0].tags[tags.SPAN_KIND] == tags.SPAN_KIND_RPC_CLIENT

    if status_code >= 400:
        assert recorder.spans[0].tags['error'] is True


def test_trace_requests_session(monkeypatch):
    resp = Response()
    resp.status_code = 200
    resp.url = URL

    monkeypatch.setattr('opentracing_utils.libs.requests_.__requests_http_send', assert_send_reuqest_mock(resp))

    recorder = Recorder()
    t = BasicTracer(recorder=recorder)
    t.register_required_propagators()
    opentracing.tracer = t

    top_span = opentracing.tracer.start_span(operation_name='top_span')

    with top_span:
        session = requests.Session()
        session.headers.update({CUSTOM_HEADER: CUSTOM_HEADER_VALUE})
        response = session.get(URL)

    assert len(recorder.spans) == 2

    assert recorder.spans[0].context.trace_id == top_span.context.trace_id
    assert recorder.spans[0].parent_id == recorder.spans[-1].context.span_id

    assert recorder.spans[-1].operation_name == 'top_span'

    assert response.status_code == resp.status_code
    assert recorder.spans[0].tags[tags.HTTP_STATUS_CODE] == resp.status_code
    assert recorder.spans[0].tags[tags.HTTP_URL] == URL
    assert recorder.spans[0].tags[tags.HTTP_METHOD] == 'GET'
    assert recorder.spans[0].tags[tags.SPAN_KIND] == tags.SPAN_KIND_RPC_CLIENT


def test_trace_requests_nested(monkeypatch):
    resp = Response()
    resp.status_code = 200
    resp.url = URL

    monkeypatch.setattr('opentracing_utils.libs.requests_.__requests_http_send', assert_send_reuqest_mock(resp))

    recorder = Recorder()
    t = BasicTracer(recorder=recorder)
    t.register_required_propagators()
    opentracing.tracer = t

    top_span = opentracing.tracer.start_span(operation_name='top_span')

    @trace()
    def caller():

        def child():
            session = requests.Session()
            session.headers.update({CUSTOM_HEADER: CUSTOM_HEADER_VALUE})
            return session.get(URL)

        # child is un-traced, but rquests will consume the current span!
        return child()

    with top_span:
        response = caller()

    assert len(recorder.spans) == 3

    assert recorder.spans[0].context.trace_id == top_span.context.trace_id
    assert recorder.spans[0].parent_id == recorder.spans[1].context.span_id

    assert recorder.spans[-1].operation_name == 'top_span'

    assert response.status_code == resp.status_code
    assert recorder.spans[0].tags[tags.HTTP_STATUS_CODE] == resp.status_code
    assert recorder.spans[0].tags[tags.HTTP_URL] == URL
    assert recorder.spans[0].tags[tags.HTTP_METHOD] == 'GET'
    assert recorder.spans[0].tags[tags.SPAN_KIND] == tags.SPAN_KIND_RPC_CLIENT


def test_trace_requests_no_propagators(monkeypatch):
    resp = Response()
    resp.status_code = 200
    resp.url = URL

    send_request_mock = MagicMock()
    send_request_mock.return_value = resp

    logger = MagicMock()

    monkeypatch.setattr('opentracing_utils.libs.requests_.__requests_http_send', send_request_mock)
    monkeypatch.setattr('opentracing_utils.libs.requests_.logger', logger)

    recorder = Recorder()
    opentracing.tracer = BasicTracer(recorder=recorder)

    top_span = opentracing.tracer.start_span(operation_name='top_span')

    with top_span:
        session = requests.Session()
        session.headers.update({CUSTOM_HEADER: CUSTOM_HEADER_VALUE})
        response = session.get(URL)

    assert len(recorder.spans) == 2

    assert recorder.spans[0].context.trace_id == top_span.context.trace_id
    assert recorder.spans[0].parent_id == recorder.spans[1].context.span_id

    assert recorder.spans[-1].operation_name == 'top_span'

    assert response.status_code == resp.status_code
    assert recorder.spans[0].tags[tags.HTTP_STATUS_CODE] == resp.status_code
    assert recorder.spans[0].tags[tags.HTTP_URL] == URL
    assert recorder.spans[0].tags[tags.HTTP_METHOD] == 'GET'
    assert recorder.spans[0].tags[tags.SPAN_KIND] == tags.SPAN_KIND_RPC_CLIENT

    logger.error.assert_called_once()


def test_trace_requests_no_parent_span(monkeypatch):
    resp = Response()
    resp.status_code = 200
    resp.url = URL

    monkeypatch.setattr('opentracing_utils.libs.requests_.__requests_http_send', assert_send_reuqest_mock(resp))

    recorder = Recorder()
    t = BasicTracer(recorder=recorder)
    t.register_required_propagators()
    opentracing.tracer = t

    session = requests.Session()
    session.headers.update({CUSTOM_HEADER: CUSTOM_HEADER_VALUE})
    response = session.get(URL)

    assert len(recorder.spans) == 1

    assert recorder.spans[0].tags[tags.HTTP_STATUS_CODE] == resp.status_code
    assert recorder.spans[0].tags[tags.HTTP_URL] == URL
    assert recorder.spans[0].tags[tags.HTTP_METHOD] == 'GET'
    assert recorder.spans[0].tags[tags.SPAN_KIND] == tags.SPAN_KIND_RPC_CLIENT

    assert response.status_code == resp.status_code


def test_trace_requests_extract_span_fail(monkeypatch):
    resp = Response()
    resp.status_code = 200
    resp.url = URL

    send_request_mock = MagicMock()
    send_request_mock.return_value = resp

    extract_span_mock = MagicMock()
    extract_span_mock.return_value = None, None

    monkeypatch.setattr('opentracing_utils.libs.requests_.__requests_http_send', send_request_mock)
    monkeypatch.setattr('opentracing_utils.libs.requests_.extract_span', extract_span_mock)

    logger = MagicMock()
    monkeypatch.setattr('opentracing_utils.libs.requests_.logger', logger)

    recorder = Recorder()
    t = BasicTracer(recorder=recorder)
    t.register_required_propagators()
    opentracing.tracer = t

    session = requests.Session()
    session.headers.update({CUSTOM_HEADER: CUSTOM_HEADER_VALUE})
    response = session.get(URL)

    assert response.status_code == resp.status_code

    logger.warn.assert_called_once()


@pytest.mark.parametrize('url,res', (
    ('https://example.org', 'https://example.org'),
    ('https://www.example.org', 'https://www.example.org'),
    ('http://example.org/p/1', 'http://example.org/p/1'),
    ('http://www.example.org/p/1', 'http://www.example.org/p/1'),
    ('http://www.example.org/p/1?q=abc&v=123&x=some%20thing', 'http://www.example.org/p/1?q=abc&v=123&x=some%20thing'),
    ('http://www.example.org/p/1?q=abc#f1', 'http://www.example.org/p/1?q=abc#f1'),
    ('https://user:pass@www.example.org/p/1?q=abc#f1', 'https://www.example.org/p/1?q=abc#f1'),
    ('https://user:@www.example.org/p/1?q=abc#f1', 'https://www.example.org/p/1?q=abc#f1'),
    ('https://user@www.example.org/p/1?q=abc#f1', 'https://www.example.org/p/1?q=abc#f1'),
    ('https://user:pass@example.org/p/1?q=abc#f1', 'https://example.org/p/1?q=abc#f1'),
    ('https://user:@sub1.sub2.example.org/p/1?q=abc#f1', 'https://sub1.sub2.example.org/p/1?q=abc#f1'),
    ('https://user@example.org/p/1/?q=abc#f1', 'https://example.org/p/1/?q=abc#f1'),
    ('http://user@localhost:8080/p/1/?q=abc#f1', 'http://localhost:8080/p/1/?q=abc#f1'),
    ('http://user@127.0.0.1:8080/p/1/?q=abc#f1', 'http://127.0.0.1:8080/p/1/?q=abc#f1'),
))
def test_sanitize_url(url, res):
    assert sanitize_url(url) == res
