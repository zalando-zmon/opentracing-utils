import inspect
import logging

import opentracing

from opentracing import child_of, follows_from
from opentracing.ext import tags as opentracing_tags


DEFAULT_SPAN_ARG_NAME = '__OPENTRACINGUTILS_SPAN'  # hmmm!


logger = logging.getLogger(__name__)


def get_new_span(
        f, func_args, func_kwargs, operation_name=None, inspect_stack=True, ignore_parent_span=False,
        span_extractor=None, use_follows_from=False):
    parent_span = None
    span_arg_name = DEFAULT_SPAN_ARG_NAME

    if not ignore_parent_span:
        if callable(span_extractor):
            try:
                parent_span = span_extractor(*func_args, **func_kwargs)
            except Exception:
                logger.exception('Failed to extract span from: {}'.format(span_extractor.__name__))

        if not parent_span:
            span_arg_name, parent_span = get_parent_span(inspect_stack=inspect_stack, **func_kwargs)

    op_name = f.__name__ if not operation_name else operation_name

    references = None
    if parent_span:
        references = [follows_from(parent_span.context)] if use_follows_from else [child_of(parent_span.context)]

    return span_arg_name, opentracing.tracer.start_span(operation_name=op_name, references=references)


def adjust_span(span, operation_name, component, tags):
    if operation_name:
        span.set_operation_name(operation_name)

    if tags and type(tags) is dict:
        for k, v in tags.items():
            try:
                span.set_tag(k, v)
            except Exception:
                pass

    if component:
        span.set_tag(opentracing_tags.COMPONENT, component)

    return span


def get_span_from_kwargs(**kwargs):
    for k, v in kwargs.items():
        if isinstance(v, opentracing.Span):
            return k, v

    return None, None


def inspect_span_from_stack(depth=100):
    cframe = inspect.currentframe()
    frame = cframe.f_back

    span = None
    for _ in range(depth):
        if span or not frame:
            break

        for k, v in frame.f_locals.items():
            if isinstance(v, opentracing.Span):
                span = v

        frame = frame.f_back

    return span


def get_parent_span(inspect_stack=True, **kwargs):
    span_arg_name, parent_span = get_span_from_kwargs(**kwargs)

    if not parent_span and inspect_stack:
        span_arg_name = DEFAULT_SPAN_ARG_NAME
        parent_span = inspect_span_from_stack()

    return span_arg_name, parent_span


def extract_span_from_kwargs(**kwargs):
    """Return current span from kwargs"""
    _, span = get_span_from_kwargs(**kwargs)

    if not span:
        span = opentracing.tracer.start_span()
        span.log_kv({'opentracing_utils.warning': 'Cannot find span in kwargs. Starting new span!'})

    return span


def remove_span_from_kwargs(**kwargs):
    span_key, _ = get_span_from_kwargs(**kwargs)
    kwargs.pop(span_key, None)
    return kwargs
