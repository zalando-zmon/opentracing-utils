import opentracing
import requests
from basictracer import BasicTracer
from requests.models import Response

from opentracing_utils import trace_requests
from tests.conftest import Recorder


def assert_send_request_mock(resp):

    def send_request_mock(self, request, **kwargs):
        assert 'ot-tracer-traceid' in request.headers
        assert 'ot-tracer-spanid' in request.headers

        return resp

    return send_request_mock


def test_trace_requests_span_extractor(monkeypatch):
    resp = Response()
    resp.status_code = 200
    resp.url = "http://example.com/"

    recorder = Recorder()
    t = BasicTracer(recorder=recorder)
    t.register_required_propagators()
    opentracing.tracer = t

    top_span = opentracing.tracer.start_span(operation_name='top_span')

    def span_extractor(*args, **kwargs):
        return top_span

    trace_requests(span_extractor=span_extractor)

    monkeypatch.setattr('opentracing_utils.libs._requests.__requests_http_send',
                        assert_send_request_mock(resp))
    # disable getting the span from stack
    monkeypatch.setattr('opentracing_utils.span.inspect_span_from_stack',
                        lambda: None)

    response = requests.get("http://example.com/")

    top_span.finish()

    assert len(recorder.spans) == 2
    assert recorder.spans[0].context.trace_id == top_span.context.trace_id
    assert recorder.spans[0].parent_id == recorder.spans[1].context.span_id
    assert recorder.spans[0].operation_name == 'http_send_get'
    assert recorder.spans[-1].operation_name == 'top_span'
    assert response.status_code == resp.status_code
