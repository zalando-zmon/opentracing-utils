import os
import logging

import opentracing

OPENTRACING_INSTANA = 'instana'
OPENTRACING_LIGHTSTEP = 'lightstep'
OPENTRACING_JAEGER = 'jaeger'
OPENTRACING_BASIC = 'basic'


logger = logging.getLogger(__name__)


def init_opentracing_tracer(tracer, **kwargs):
    if tracer == OPENTRACING_BASIC:
        from basictracer import BasicTracer  # noqa

        recorder = kwargs.get('recorder')
        sampler = kwargs.get('sampler')

        opentracing.tracer = BasicTracer(recorder=recorder, sampler=sampler)
    elif tracer == OPENTRACING_INSTANA:
        import instana.options as InstanaOpts
        import instana.tracer  # noqa

        service = kwargs.pop(
            'service',
            os.environ.get('OPENTRACING_INSTANA_SERVICE'))
        log_level = kwargs.pop('log_level', logging.INFO)

        instana.tracer.init(InstanaOpts.Options(service=service, log_level=log_level, **kwargs))
    elif tracer == OPENTRACING_LIGHTSTEP:
        import lightstep

        # Get Lightstep specific config vars
        component_name = kwargs.pop(
            'component_name',
            os.environ.get('OPENTRACING_LIGHTSTEP_COMPONENT_NAME'))
        access_token = kwargs.pop(
            'access_token',
            os.environ.get('OPENTRACING_LIGHTSTEP_ACCESS_TOKEN'))
        collector_host = kwargs.pop(
            'collector_host',
            os.environ.get('OPENTRACING_LIGHTSTEP_COLLECTOR_HOST', 'collector.lightstep.com'))
        collector_port = kwargs.pop(
            'collector_port',
            int(os.environ.get('OPENTRACING_LIGHTSTEP_COLLECTOR_PORT', 443)))
        verbosity = kwargs.pop(
            'verbosity',
            int(os.environ.get('OPENTRACING_LIGHTSTEP_VERBOSITY', 0)))

        if not access_token:
            logger.warn('Initializing LighStep tracer with no access_token!')

        opentracing.tracer = lightstep.Tracer(
            component_name=component_name, access_token=access_token, collector_host=collector_host,
            collector_port=collector_port, verbosity=verbosity, **kwargs)
    elif tracer == OPENTRACING_JAEGER:
        from jaeger_client import Config

        service_name = kwargs.pop('service_name', os.environ.get('OPENTRACING_JAEGER_SERVICE_NAME'))
        config = kwargs.pop('config', {})

        jaeger_config = Config(config=config, service_name=service_name)
        opentracing.tracer = jaeger_config.initialize_tracer()
    else:
        opentracing.tracer = opentracing.Tracer()
