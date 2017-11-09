import logging

import opentracing

OPENTRACING_INSTANA = 'instana'
OPENTRACING_LIGHTSTEP = 'lightstep'
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
    else:
        opentracing.tracer = opentracing.Tracer()
