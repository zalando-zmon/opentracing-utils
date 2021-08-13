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
from opentracing_utils.common import sanitize_url
from opentracing_utils.libs._requests import OPERATION_NAME_PREFIX


URL = 'http://example.com/'
CUSTOM_HEADER = 'X-CUSTOM'
CUSTOM_HEADER_VALUE = '123'


def assert_send_request_mock(resp):

    def send_request_mock(self, request, **kwargs):
        assert 'ot-tracer-traceid' in request.headers
        assert 'ot-tracer-spanid' in request.headers

        assert request.headers[CUSTOM_HEADER] == CUSTOM_HEADER_VALUE

        return resp

    return send_request_mock


def assert_send_request_mock_no_traces(resp):
    def send_request_mock(self, request, **kwargs):
        assert 'ot-tracer-traceid' not in request.headers
        assert 'ot-tracer-spanid' not in request.headers
        assert '__OPENTRACINGUTILS_SPAN' not in kwargs
        assert request.headers[CUSTOM_HEADER] == CUSTOM_HEADER_VALUE

        return resp
    return send_request_mock


def assert_send_request_mock_scope_active(resp):
    def send_request_mock(self, request, **kwargs):
        assert opentracing.tracer.active_span is not None
        return resp
    return send_request_mock


@pytest.mark.parametrize('status_code', (200, 302, 400, 500))
def test_trace_requests(monkeypatch, status_code):
    resp = Response()
    resp.status_code = status_code
    resp.url = URL

    monkeypatch.setattr('opentracing_utils.libs._requests.__requests_http_send', assert_send_request_mock(resp))

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
    assert recorder.spans[0].tags[tags.PEER_HOSTNAME] == 'example.com'
    assert recorder.spans[0].tags['timeout'] is None
    assert recorder.spans[0].tags[tags.COMPONENT] == 'requests'
    assert recorder.spans[0].operation_name == '{}_get'.format(OPERATION_NAME_PREFIX)

    if status_code >= 400:
        assert recorder.spans[0].tags['error'] is True


@pytest.mark.parametrize('status_code', (200, 302, 400, 500))
def test_trace_requests_scope_active(monkeypatch, status_code):
    resp = Response()
    resp.status_code = status_code
    resp.url = URL

    monkeypatch.setattr('opentracing_utils.libs._requests.__requests_http_send', assert_send_request_mock(resp))

    @trace()
    def f1():
        pass

    recorder = Recorder()
    t = BasicTracer(recorder=recorder)
    t.register_required_propagators()
    opentracing.tracer = t

    top_span = None
    with opentracing.tracer.start_active_span(operation_name='top_span', finish_on_close=True) as top_scope:
        top_span = top_scope.span
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
    assert recorder.spans[0].tags[tags.PEER_HOSTNAME] == 'example.com'
    assert recorder.spans[0].tags['timeout'] is None
    assert recorder.spans[0].tags[tags.COMPONENT] == 'requests'
    assert recorder.spans[0].operation_name == '{}_get'.format(OPERATION_NAME_PREFIX)

    if status_code >= 400:
        assert recorder.spans[0].tags['error'] is True


@pytest.mark.parametrize('timeout', (None, 5, (1, 10)))
def test_trace_requests_timeout(monkeypatch, timeout):
    resp = Response()
    resp.status_code = 200
    resp.url = URL

    monkeypatch.setattr('opentracing_utils.libs._requests.__requests_http_send', assert_send_request_mock(resp))

    recorder = Recorder()
    t = BasicTracer(recorder=recorder)
    t.register_required_propagators()
    opentracing.tracer = t

    response = requests.get(URL, headers={CUSTOM_HEADER: CUSTOM_HEADER_VALUE}, timeout=timeout)

    assert response.status_code == resp.status_code
    assert recorder.spans[0].tags[tags.HTTP_STATUS_CODE] == resp.status_code
    assert recorder.spans[0].tags[tags.HTTP_URL] == URL
    assert recorder.spans[0].tags[tags.HTTP_METHOD] == 'GET'
    assert recorder.spans[0].tags[tags.SPAN_KIND] == tags.SPAN_KIND_RPC_CLIENT
    assert recorder.spans[0].tags[tags.PEER_HOSTNAME] == 'example.com'
    assert recorder.spans[0].tags['timeout'] == timeout
    assert recorder.spans[0].tags[tags.COMPONENT] == 'requests'
    assert recorder.spans[0].operation_name == '{}_get'.format(OPERATION_NAME_PREFIX)


def test_trace_requests_with_ignore_url_pattern(monkeypatch):
    resp = Response()
    resp.status_code = 200
    resp.url = URL

    trace_requests(ignore_url_patterns=[r".*{}.*".format(URL)])

    monkeypatch.setattr('opentracing_utils.libs._requests.__requests_http_send',
                        assert_send_request_mock_no_traces(resp))

    response = requests.get(URL, headers={CUSTOM_HEADER: CUSTOM_HEADER_VALUE})
    assert response.status_code == resp.status_code


def test_trace_requests_with_use_scope_manager(monkeypatch):
    resp = Response()
    resp.status_code = 200
    resp.url = URL

    recorder = Recorder()
    t = BasicTracer(recorder=recorder)
    t.register_required_propagators()
    opentracing.tracer = t

    trace_requests(use_scope_manager=True)

    monkeypatch.setattr(
        'opentracing_utils.libs._requests.__requests_http_send',
        assert_send_request_mock_scope_active(resp)
    )

    response = requests.get(URL, headers={CUSTOM_HEADER: CUSTOM_HEADER_VALUE})
    assert response.status_code == resp.status_code

    assert len(recorder.spans) == 1


def test_trace_requests_do_not_ignore_if_no_match(monkeypatch):
    resp = Response()
    resp.status_code = 200
    resp.url = URL

    trace_requests(ignore_url_patterns=[r".*{}.*".format(URL)])

    monkeypatch.setattr('opentracing_utils.libs._requests.__requests_http_send', assert_send_request_mock(resp))

    response = requests.get("http://I-do-not-match.com", headers={CUSTOM_HEADER: CUSTOM_HEADER_VALUE})
    assert response.status_code == resp.status_code


def test_trace_requests_with_ignore_url_pattern_prune_kwargs(monkeypatch):
    """ In case there is a parent span already, the ignore url pattern must
    still be respected """
    resp = Response()
    resp.status_code = 200
    resp.url = URL

    trace_requests(ignore_url_patterns=[r".*{}.*".format(URL)])

    monkeypatch.setattr('opentracing_utils.libs._requests.__requests_http_send',
                        assert_send_request_mock_no_traces(resp))

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

    # Top span, and  @trace for f1() create spans. With the ignore pattern
    # in place, the call to requests.get should not add a span
    assert len(recorder.spans) == 2

    assert recorder.spans[0].context.trace_id == top_span.context.trace_id
    assert recorder.spans[0].operation_name == 'f1'
    assert recorder.spans[1].operation_name == 'top_span'
    assert response.status_code == resp.status_code


def test_trace_requests_with_tags(monkeypatch):
    resp = Response()
    resp.status_code = 200
    resp.url = URL

    trace_requests(default_tags={'tag1': 'value1'})

    monkeypatch.setattr('opentracing_utils.libs._requests.__requests_http_send', assert_send_request_mock(resp))

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
    # ``requests`` default tags do not leak to other unrelated spans!
    assert recorder.spans[1].tags == {}
    assert recorder.spans[1].operation_name == 'f1'

    assert response.status_code == resp.status_code
    assert recorder.spans[0].tags[tags.HTTP_STATUS_CODE] == resp.status_code
    assert recorder.spans[0].tags[tags.HTTP_URL] == URL
    assert recorder.spans[0].tags[tags.HTTP_METHOD] == 'GET'
    assert recorder.spans[0].tags[tags.SPAN_KIND] == tags.SPAN_KIND_RPC_CLIENT
    assert recorder.spans[0].tags[tags.PEER_HOSTNAME] == 'example.com'
    assert recorder.spans[0].tags['timeout'] is None
    assert recorder.spans[0].tags[tags.COMPONENT] == 'requests'
    assert recorder.spans[0].operation_name == '{}_get'.format(OPERATION_NAME_PREFIX)
    assert recorder.spans[0].tags['tag1'] == 'value1'


def test_trace_requests_no_error_tag(monkeypatch):
    resp = Response()
    resp.status_code = 400
    resp.url = URL

    trace_requests(set_error_tag=False)

    monkeypatch.setattr('opentracing_utils.libs._requests.__requests_http_send', assert_send_request_mock(resp))

    recorder = Recorder()
    t = BasicTracer(recorder=recorder)
    t.register_required_propagators()
    opentracing.tracer = t

    top_span = opentracing.tracer.start_span(operation_name='top_span')

    with top_span:
        response = requests.get(URL, headers={CUSTOM_HEADER: CUSTOM_HEADER_VALUE})

    assert len(recorder.spans) == 2

    assert recorder.spans[0].context.trace_id == top_span.context.trace_id
    assert recorder.spans[0].parent_id == recorder.spans[-1].context.span_id

    assert response.status_code == resp.status_code
    assert recorder.spans[0].tags[tags.HTTP_STATUS_CODE] == resp.status_code
    assert recorder.spans[0].tags[tags.HTTP_URL] == URL
    assert recorder.spans[0].tags[tags.HTTP_METHOD] == 'GET'
    assert recorder.spans[0].tags[tags.SPAN_KIND] == tags.SPAN_KIND_RPC_CLIENT
    assert recorder.spans[0].tags[tags.PEER_HOSTNAME] == 'example.com'
    assert recorder.spans[0].tags['timeout'] is None
    assert recorder.spans[0].tags[tags.COMPONENT] == 'requests'
    assert recorder.spans[0].operation_name == '{}_get'.format(OPERATION_NAME_PREFIX)
    assert 'error' not in recorder.spans[0].tags


def test_trace_requests_session(monkeypatch):
    resp = Response()
    resp.status_code = 200
    resp.url = URL

    monkeypatch.setattr('opentracing_utils.libs._requests.__requests_http_send', assert_send_request_mock(resp))

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
    assert recorder.spans[0].tags[tags.PEER_HOSTNAME] == 'example.com'
    assert recorder.spans[0].tags['timeout'] is None
    assert recorder.spans[0].tags[tags.COMPONENT] == 'requests'
    assert recorder.spans[0].operation_name == '{}_get'.format(OPERATION_NAME_PREFIX)


def test_trace_requests_nested(monkeypatch):
    resp = Response()
    resp.status_code = 200
    resp.url = URL

    monkeypatch.setattr('opentracing_utils.libs._requests.__requests_http_send', assert_send_request_mock(resp))

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
    assert recorder.spans[0].tags[tags.PEER_HOSTNAME] == 'example.com'
    assert recorder.spans[0].tags['timeout'] is None
    assert recorder.spans[0].tags[tags.COMPONENT] == 'requests'
    assert recorder.spans[0].operation_name == '{}_get'.format(OPERATION_NAME_PREFIX)


def test_trace_requests_no_propagators(monkeypatch):
    resp = Response()
    resp.status_code = 200
    resp.url = URL

    send_request_mock = MagicMock()
    send_request_mock.return_value = resp

    logger = MagicMock()

    monkeypatch.setattr('opentracing_utils.libs._requests.__requests_http_send', send_request_mock)
    monkeypatch.setattr('opentracing_utils.libs._requests.logger', logger)

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
    assert recorder.spans[0].tags[tags.PEER_HOSTNAME] == 'example.com'
    assert recorder.spans[0].tags['timeout'] is None
    assert recorder.spans[0].tags[tags.COMPONENT] == 'requests'
    assert recorder.spans[0].operation_name == '{}_get'.format(OPERATION_NAME_PREFIX)

    logger.error.assert_called_once()


def test_trace_requests_no_parent_span(monkeypatch):
    resp = Response()
    resp.status_code = 200
    resp.url = URL

    monkeypatch.setattr('opentracing_utils.libs._requests.__requests_http_send', assert_send_request_mock(resp))

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
    assert recorder.spans[0].tags[tags.PEER_HOSTNAME] == 'example.com'
    assert recorder.spans[0].tags['timeout'] is None
    assert recorder.spans[0].tags[tags.COMPONENT] == 'requests'
    assert recorder.spans[0].operation_name == '{}_get'.format(OPERATION_NAME_PREFIX)

    assert response.status_code == resp.status_code


def test_trace_requests_extract_span_fail(monkeypatch):
    resp = Response()
    resp.status_code = 200
    resp.url = URL

    send_request_mock = MagicMock()
    send_request_mock.return_value = resp

    extract_span_mock = MagicMock()
    extract_span_mock.return_value = None, None

    monkeypatch.setattr('opentracing_utils.libs._requests.__requests_http_send', send_request_mock)
    monkeypatch.setattr('opentracing_utils.libs._requests.get_span_from_kwargs', extract_span_mock)

    logger = MagicMock()
    monkeypatch.setattr('opentracing_utils.libs._requests.logger', logger)

    recorder = Recorder()
    t = BasicTracer(recorder=recorder)
    t.register_required_propagators()
    opentracing.tracer = t

    session = requests.Session()
    session.headers.update({CUSTOM_HEADER: CUSTOM_HEADER_VALUE})
    response = session.get(URL)

    assert response.status_code == resp.status_code

    logger.warn.assert_called_once()


@pytest.mark.parametrize('url,masked_q,masked_path,res', (
    ('https://example.org', False, False, 'https://example.org'),
    ('https://www.example.org', False, False, 'https://www.example.org'),
    ('http://example.org/p/1', False, False, 'http://example.org/p/1'),
    ('http://www.example.org/p/1', False, False, 'http://www.example.org/p/1'),
    ('http://www.example.org/p/1?q=abc&v=123&x=some%20thing', False, False,
     'http://www.example.org/p/1?q=abc&v=123&x=some%20thing'),
    ('http://www.example.org/p/1?q=abc#f1', False, False, 'http://www.example.org/p/1?q=abc#f1'),
    ('https://user:pass@www.example.org/p/1?q=abc#f1', False, False, 'https://www.example.org/p/1?q=abc#f1'),
    ('https://user:@www.example.org/p/1?q=abc#f1', False, False, 'https://www.example.org/p/1?q=abc#f1'),
    ('https://user@www.example.org/p/1?q=abc#f1', False, False, 'https://www.example.org/p/1?q=abc#f1'),
    ('https://user:pass@example.org/p/1?q=abc#f1', False, False, 'https://example.org/p/1?q=abc#f1'),
    ('https://user:@sub1.sub2.example.org/p/1?q=abc#f1', False, False, 'https://sub1.sub2.example.org/p/1?q=abc#f1'),
    ('https://user@example.org/p/1/?q=abc#f1', False, False, 'https://example.org/p/1/?q=abc#f1'),
    ('http://user@localhost:8080/p/1/?q=abc#f1', False, False, 'http://localhost:8080/p/1/?q=abc#f1'),
    ('http://user@127.0.0.1:8080/p/1/?q=abc#f1', False, False, 'http://127.0.0.1:8080/p/1/?q=abc#f1'),
    ('http://user@127.0.0.1:8080/p/1/?token=123abc#f1', True, True,
     'http://127.0.0.1:8080/??/?token=%3F#f1'),
))
def test_sanitize_url(url, masked_q, masked_path, res):
    assert sanitize_url(url, mask_url_query=masked_q, mask_url_path=masked_path) == res
