import logging

import six
import pytest
import opentracing

from mock import MagicMock

from .conftest import Recorder

from basictracer import BasicTracer

from opentracing_utils import init_opentracing_tracer
from opentracing_utils import OPENTRACING_INSTANA, OPENTRACING_BASIC, OPENTRACING_LIGHTSTEP, OPENTRACING_JAEGER


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

    init_opentracing_tracer(OPENTRACING_INSTANA, log_level=logging.DEBUG, service=SERVICE_NAME)

    opts.Options.assert_called_once_with(service=SERVICE_NAME, log_level=logging.DEBUG)
    init.assert_called_once()


def test_init_instana_env_vars(monkeypatch):
    init = MagicMock()
    opts = MagicMock()

    monkeypatch.setattr('instana.tracer.init', init)
    monkeypatch.setattr('instana.options', opts)

    monkeypatch.setenv('OPENTRACING_INSTANA_SERVICE', 'service')

    init_opentracing_tracer(OPENTRACING_INSTANA, log_level=logging.DEBUG, service=SERVICE_NAME)

    opts.Options.assert_called_once_with(service='service', log_level=logging.DEBUG)
    init.assert_called_once()


def test_init_lightstep(monkeypatch):
    tracer = MagicMock()

    monkeypatch.setattr('lightstep.Tracer', tracer)

    init_opentracing_tracer(OPENTRACING_LIGHTSTEP, component_name='test_lightstep', verbosity=2,
                            global_tags='foo=bar;baz=foo', tags={'bar': 'baz'})

    tracer.assert_called_once_with(
        component_name='test_lightstep', access_token=None, collector_host='collector.lightstep.com',
        collector_port=443, verbosity=2, tags={'foo': 'bar', 'baz': 'foo', 'bar': 'baz'})


def test_init_lightstep_env_vars(monkeypatch):
    tracer = MagicMock()

    monkeypatch.setattr('lightstep.Tracer', tracer)
    monkeypatch.setenv('OPENTRACING_LIGHTSTEP_COMPONENT_NAME', 'component')
    monkeypatch.setenv('OPENTRACING_LIGHTSTEP_ACCESS_TOKEN', '1234')
    monkeypatch.setenv('OPENTRACING_LIGHTSTEP_COLLECTOR_HOST', 'tracer.example.org')
    monkeypatch.setenv('OPENTRACING_LIGHTSTEP_COLLECTOR_PORT', '8443')
    monkeypatch.setenv('OPENTRACING_LIGHTSTEP_VERBOSITY', '1')
    monkeypatch.setenv('OPENTRACING_LIGHTSTEP_TAGS', 'foo=bar;baz=foo')

    init_opentracing_tracer(OPENTRACING_LIGHTSTEP)

    tracer.assert_called_once_with(
        component_name='component', access_token='1234', collector_host='tracer.example.org',
        collector_port=8443, verbosity=1, tags={'foo': 'bar', 'baz': 'foo'})


@pytest.mark.skipif(six.PY3, reason='Jaeger does not support PY3')
def test_init_jaeger(monkeypatch):
    config = MagicMock()
    config.return_value.initialize_tracer.return_value = 'jaeger'

    monkeypatch.setattr('jaeger_client.Config', config)

    init_opentracing_tracer(OPENTRACING_JAEGER, service_name='test_jaeger')

    config.assert_called_once_with(config={}, service_name='test_jaeger')

    assert opentracing.tracer == 'jaeger'


@pytest.mark.skipif(six.PY3, reason='Jaeger does not support PY3')
def test_init_jaeger_with_config(monkeypatch):
    config = MagicMock()
    config.return_value.initialize_tracer.return_value = 'jaeger'

    monkeypatch.setattr('jaeger_client.Config', config)
    monkeypatch.setenv('OPENTRACING_JAEGER_SERVICE_NAME', 'component')

    init_opentracing_tracer(OPENTRACING_JAEGER, config={'logging': True})

    config.assert_called_once_with(config={'logging': True}, service_name='component')

    assert opentracing.tracer == 'jaeger'
