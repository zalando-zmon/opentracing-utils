import functools

from opentracing_utils.span import get_new_span, adjust_span


def trace(component=None, operation_name=None, tags=None, pass_span=False, inspect_stack=True, ignore_parent_span=False,
          **kwargs):
    """Opentracing docrator"""

    def trace_decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            span_arg_name, current_span = get_new_span(
                f, inspect_stack=inspect_stack, ignore_parent_span=ignore_parent_span, **kwargs)

            if not pass_span and span_arg_name:
                kwargs.pop(span_arg_name, None)

            current_span = adjust_span(current_span, operation_name, component, tags)

            with current_span:
                return f(*args, **kwargs)

        return wrapper

    return trace_decorator


# TODO: Enable once we drop support for py 2.7
# def trace_async(component=None, operation_name=None, tags=None, pass_span=False, ignore_parent_span=False, **kwargs):
#     """Opentracing Async decorator. Suitable for asyncio coroutines."""

#     def trace_decorator(f):
#         @functools.wraps(f)
#         async def wrapper(*args, **kwargs):
#             span_arg_name, current_span = get_new_span(
#                 f, inspect_stack=False, ignore_parent_span=ignore_parent_span, **kwargs)

#             if not pass_span and span_arg_name:
#                 kwargs.pop(span_arg_name, None)

#             current_span = adjust_span(current_span, operation_name, component, tags)

#             with current_span:
#                 return await f(*args, **kwargs)

#         return wrapper

#     return trace_decorator
