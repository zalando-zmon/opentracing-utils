import functools

import opentracing

from opentracing_utils.span import get_new_span, adjust_span, get_span_from_kwargs, remove_span_from_kwargs


def trace(component=None, operation_name=None, tags=None, use_follows_from=False, pass_span=False, inspect_stack=True,
          ignore_parent_span=False, span_extractor=None, skip_span=None, use_scope_manager=False):
    """
    Opentracing tracer decorator. Attempts to extract parent span and create a new span for the decorated function.

    The order of parent span inspection:

    1. Using ``span_extractor``.
    2. Detecting span in kwargs.
    3. Using ``opentracing.tracer.active_span`` managed by the tracer context manager. The new span will be using the
    scope manager.
    4. Using call stack frames inspection.

    :param commponent: commponent name.
    :type commponent: str

    :param operation: Span operation name. If not set then it will be the ``function.__name__``.
    :type operation: str

    :param tags: Span tags. If tags is not a dict, then it will be ignored.
    :type tags: dict

    :param use_follows_from: Use a ``follows_from`` reference instead of the default ``child_of``.
    :type use_follows_from: bool

    :param pass_span: Whether to pass the newly created span to the decorated function. Default is False.
                      This is useful if the traced function would add extra tags to the span.
                      *IMPORTANT*: This will not pass the parent span if any, it will only pass the new span decorating
                      the traced function even if the caller passed the parent span explicitly.
    :type pass_span: bool

    :param inspect_stack: Whether to inspect call stack frames to retrieve the parent span. Default is True.
    :type inspect_stack: bool

    :param ignore_parent_span: Always start a fresh span for this decorated function. Default is False.
    :type ignore_parent_span: bool

    :param span_extractor: A callable that retrieves the current parent span. This is useful when decorator is used
                           in a context aware application and there is an alternative way to retrieve the span.
                           Callable should expect the traced function *args & **kwargs.
                           If None is returned from the callable, then normal span extraction will be applied.
    :type span_extractor: Callable[*args, **kwargs]

    :param skip_span: A callable which can be used to determine if the span should be skipped.
    :type skip_span: Callable[*args, **kwargs]

    :param use_scope_manager: Always use the scope manager when starting the span.
    :type use_scope_manager: bool
    """

    def trace_decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            if skip_span is not None and skip_span(*args, **kwargs):
                return f(*args, **remove_span_from_kwargs(**kwargs))

            # Get a new current span wrapping this traced function.
            # ``get_new_span`` should retrieve parent_span if any!
            span_arg_name, using_scope_manager, current_span = get_new_span(
                f, args, kwargs, inspect_stack=inspect_stack, ignore_parent_span=ignore_parent_span,
                span_extractor=span_extractor, use_follows_from=use_follows_from)

            if pass_span and span_arg_name:
                kwargs[span_arg_name] = current_span
            else:
                if span_extractor:
                    kwarg_span, _ = get_span_from_kwargs(**kwargs)
                    kwargs.pop(kwarg_span, None)

                kwargs.pop(span_arg_name, None)

            current_span = adjust_span(current_span, operation_name, component, tags)

            with _activate_span(current_span, using_scope_manager or use_scope_manager):
                return f(*args, **kwargs)

        return wrapper

    return trace_decorator


def _activate_span(current_span, using_scope_manager):
    if using_scope_manager:
        return opentracing.tracer.scope_manager.activate(current_span, finish_on_close=True)

    return current_span
