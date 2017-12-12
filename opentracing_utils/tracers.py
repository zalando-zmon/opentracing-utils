import logging

import opentracing

OPENTRACING_INSTANA = 'instana'
OPENTRACING_LIGHTSTEP = 'lightstep'
OPENTRACING_JAEGER = 'jaeger'
OPENTRACING_BASIC = 'basic'


def init_opentracing_tracer(tracer, log_level=logging.INFO, recorder=None, **kwargs):
    if tracer == OPENTRACING_BASIC:
        from basictracer import BasicTracer  # noqa

        opentracing.tracer = BasicTracer(recorder=recorder)
    elif tracer == OPENTRACING_INSTANA:
        import instana.options as InstanaOpts
        import instana.tracer  # noqa

        instana.tracer.init(InstanaOpts.Options(log_level=log_level, **kwargs))
    elif tracer == OPENTRACING_LIGHTSTEP:
        import lightstep
        opentracing.tracer = lightstep.Tracer(**kwargs)
    elif tracer == OPENTRACING_JAEGER:
        from jaeger_client import Config
        config = Config(config=kwargs)
        opentracing.tracer = config.initialize_tracer()
    else:
        opentracing.tracer = opentracing.Tracer()
