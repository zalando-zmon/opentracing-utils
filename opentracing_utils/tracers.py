import logging

import opentracing

OPENTRACING_INSTANA = 'instana'
OPENTRACING_BASIC = 'basic'


def init_opentracing_tracer(tracer, service_name=None, log_level=logging.INFO, recorder=None, **kwargs):
    if tracer == OPENTRACING_BASIC:
        from basictracer import BasicTracer  # noqa

        opentracing.tracer = BasicTracer(recorder=recorder)
    elif tracer == OPENTRACING_INSTANA:
        import instana.options as InstanaOpts
        import instana.tracer  # noqa

        instana.tracer.init(InstanaOpts.Options(service=service_name, log_level=log_level))

    # Add more tracers
    else:
        opentracing.tracer = opentracing.Tracer()
