import logging

import opentracing

from mock import MagicMock

from .conftest import Recorder

from basictracer import BasicTracer

from opentracing_utils import init_opentracing_tracer
from opentracing_utils import OPENTRACING_INSTANA, OPENTRACING_BASIC


SERVICE_NAME = 'service'


def test_init_noop():
    init_opentracing_tracer(None)

    assert isinstance(opentracing.tracer, opentracing.Tracer)


def test_init_basic():
    recorder = Recorder()

    init_opentracing_tracer(OPENTRACING_BASIC, recorder=recorder)

    assert isinstance(opentracing.tracer, BasicTracer)
    assert opentracing.tracer.recorder == recorder


def test_init_instana(monkeypatch):
    init = MagicMock()
    opts = MagicMock()

    monkeypatch.setattr('instana.tracer.init', init)
    monkeypatch.setattr('instana.options', opts)

    init_opentracing_tracer(OPENTRACING_INSTANA, log_level=logging.DEBUG, service_name=SERVICE_NAME)

    opts.Options.assert_called_once_with(service=SERVICE_NAME, log_level=logging.DEBUG)
    init.assert_called_once()
