import opentracing
import pytest

from mock import MagicMock
from opentracing.ext import tags as ot_tags

from flask import Flask
from flask import make_response

from basictracer import BasicTracer

from opentracing_utils.libs._flask import trace_flask, extract_span_from_flask_request

from .conftest import Recorder


def get_recorder():
    recorder = Recorder()
    t = BasicTracer(recorder=recorder)
    t.register_required_propagators()
    opentracing.tracer = t

    return recorder


def get_flask_app():
    app = Flask('test_app')

    @app.route('/')
    def root():
        return 'Hello Test'

    @app.route('/error/<code>')
    def error(code):
        return make_response('error', int(code))

    return app


def test_trace_flask(monkeypatch):
    app = get_flask_app()
    recorder = get_recorder()

    trace_flask(app)

    with app.app_context():
        client = app.test_client()

        r = client.get('/')
        assert b'Hello Test' in r.data

    assert len(recorder.spans) == 1

    assert recorder.spans[0].tags['url'] == 'http://localhost/'
    assert recorder.spans[0].tags['method'] == 'GET'
    assert recorder.spans[0].tags['status_code'] == '200'


def test_trace_flask_propagate(monkeypatch):
    app = get_flask_app()
    recorder = get_recorder()

    propagated_span = MagicMock()
    propagated_span.context.trace_id = 123
    propagated_span.context.span_id = 123456

    extract = MagicMock()
    extract.return_value = propagated_span

    monkeypatch.setattr('opentracing.tracer.extract', extract)

    trace_flask(app)

    with app.app_context():
        client = app.test_client()

        r = client.get('/')
        assert b'Hello Test' in r.data

    assert len(recorder.spans) == 1

    assert recorder.spans[0].context.trace_id == propagated_span.context.trace_id
    assert recorder.spans[0].parent_id == propagated_span.context.span_id

    assert recorder.spans[0].tags['url'] == 'http://localhost/'
    assert recorder.spans[0].tags['method'] == 'GET'
    assert recorder.spans[0].tags['status_code'] == '200'

    extract.assert_called_once()


def test_trace_flask_span_none(monkeypatch):
    app = get_flask_app()

    span_mock = MagicMock()

    start_span = MagicMock()
    start_span.side_effect = [None, span_mock]

    monkeypatch.setattr('opentracing.tracer.start_span', start_span)

    trace_flask(app)

    with app.app_context():
        client = app.test_client()

        r = client.get('/')
        assert b'Hello Test' in r.data

    start_span.assert_called()


def test_trace_flask_span_set_tag_error(monkeypatch):
    app = get_flask_app()
    # recorder = get_recorder()

    def set_tag(k, v):
        if k != ot_tags.SPAN_KIND:
            raise RuntimeError

    span_mock = MagicMock()
    span_mock.set_tag.side_effect = RuntimeError
    span_mock.set_tag = set_tag

    start_span = MagicMock()
    start_span.return_value = span_mock

    monkeypatch.setattr('opentracing.tracer.start_span', start_span)

    trace_flask(app, default_tags={'tag-1': 'value-1'})

    with app.app_context():
        client = app.test_client()

        r = client.get('/')
        assert b'Hello Test' in r.data

    start_span.assert_called()


@pytest.mark.parametrize('error_code', (400, 401, 404, 500, 502, 503))
def test_trace_flask_error(monkeypatch, error_code):
    app = get_flask_app()
    recorder = get_recorder()

    trace_flask(app)

    url = '/error/{}'.format(error_code)

    with app.app_context():
        client = app.test_client()

        r = client.get(url)
        assert b'error' in r.data

    assert len(recorder.spans) == 1

    assert 'error' in recorder.spans[0].tags
    assert recorder.spans[0].tags['url'] == 'http://localhost{}'.format(url)
    assert recorder.spans[0].tags['method'] == 'GET'
    assert recorder.spans[0].tags['status_code'] == str(error_code)


def test_trace_flask_default_tags(monkeypatch):
    app = get_flask_app()
    recorder = get_recorder()

    trace_flask(app, default_tags={'tag-1': 'value-1'})

    with app.app_context():
        client = app.test_client()

        r = client.get('/')
        assert b'Hello Test' in r.data

    assert len(recorder.spans) == 1

    assert recorder.spans[0].tags['url'] == 'http://localhost/'
    assert recorder.spans[0].tags['method'] == 'GET'
    assert recorder.spans[0].tags['status_code'] == '200'
    assert recorder.spans[0].tags['tag-1'] == 'value-1'


def test_trace_flask_no_attr_tags(monkeypatch):
    app = get_flask_app()
    recorder = get_recorder()

    trace_flask(app, request_attr=None, response_attr=None)

    with app.app_context():
        client = app.test_client()

        r = client.get('/')
        assert b'Hello Test' in r.data

    assert len(recorder.spans) == 1

    assert 'url' not in recorder.spans[0].tags
    assert 'method' not in recorder.spans[0].tags
    assert 'status_code' not in recorder.spans[0].tags


@pytest.mark.parametrize('error_code', (400, 401, 404, 500, 502, 503))
def test_trace_flask_no_4xx_error(monkeypatch, error_code):
    app = get_flask_app()
    recorder = get_recorder()

    trace_flask(app, error_on_4xx=False)

    url = '/error/{}'.format(error_code)

    with app.app_context():
        client = app.test_client()

        r = client.get(url)
        assert b'error' in r.data

    assert len(recorder.spans) == 1

    if error_code >= 500:
        assert 'error' in recorder.spans[0].tags

    assert recorder.spans[0].tags['url'] == 'http://localhost{}'.format(url)
    assert recorder.spans[0].tags['method'] == 'GET'
    assert recorder.spans[0].tags['status_code'] == str(error_code)


def test_extract_span_from_request(monkeypatch):
    app = get_flask_app()
    recorder = get_recorder()

    trace_flask(app)

    trace_id = ''
    root_span_id = ''

    with app.app_context():
        def assert_flask_request_span():
            span = extract_span_from_flask_request()
            assert span is not None

            child_span = opentracing.tracer.start_span(operation_name='internal', child_of=span)

            with child_span:
                child_span.set_tag('tag-1', 'value-1')

            return '{},{}'.format(span.context.trace_id, span.context.span_id)

        app.add_url_rule('/get-span', view_func=assert_flask_request_span)

        client = app.test_client()

        r = client.get('/get-span')
        trace_id, root_span_id = r.get_data(as_text=True).split(',')

    assert len(recorder.spans) == 2

    assert trace_id == str(recorder.spans[-1].context.trace_id)
    assert root_span_id == str(recorder.spans[-1].context.span_id)

    assert recorder.spans[0].operation_name == 'internal'
    assert recorder.spans[0].tags['tag-1'] == 'value-1'


def test_extract_span_from_request_failed(monkeypatch):
    assert extract_span_from_flask_request() is None
