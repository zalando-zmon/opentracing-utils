import opentracing

try:
    from sqlalchemy.engine import Engine
    from sqlalchemy.event import listens_for
except ImportError:  # pragma: no cover
    pass

from opentracing.ext import tags as ot_tags
from opentracing_utils.span import get_parent_span


def trace_sqlalchemy(operation_name=None, span_extractor=None, set_error_tag=False, skip_span=None):
    """
    Trace Sqlalchemy database queries.

    :param operation_name: Callable to return the operation name of the query. By default, operation_name will be the
                           clause of the SQL statement (e.g. select, update, delete).
    :type operation_name: Callable[conn, cursor, statement, parameters, context, executemany]

    :param span_extractor: Callable to return the parent span. Default is ``None``, and trace_sqlachemy will attempt
                           to detect the parent span.
    :type span_extractor: Callable[conn, cursor, statement, parameters, context, executemany]

    :param set_error_tag: Database query span will set error tag in case of any exceptions. Default is False.
    :type set_error_tag: bool

    :param skip_span: Callable to determine whether to skip this SQL query(ies) spans. If returned ``True`` then span
                      will be skipped.
    :type skip_span: Callable[conn, cursor, statement, parameters, context, executemany]
    """

    @listens_for(Engine, 'before_cursor_execute')
    def trace_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        if callable(skip_span) and skip_span(conn, cursor, statement, parameters, context, executemany):
            return

        if callable(span_extractor):
            parent_span = span_extractor(conn, cursor, statement, parameters, context, executemany)
        else:
            _, parent_span = get_parent_span()

        if context:
            op_name = statement.split(' ')[0].lower() or 'query'
            if callable(operation_name):
                op_name = operation_name(conn, cursor, statement, parameters, context, executemany)

            query_span = opentracing.tracer.start_span(operation_name=op_name, child_of=parent_span)

            if context:
                (query_span
                    .set_tag(ot_tags.COMPONENT, 'sqlalchemy')
                    .set_tag('db.type', 'sql')
                    .set_tag('db.engine', context.dialect.name)
                    .set_tag('db.statement', statement))

                context._query_span = query_span

    @listens_for(Engine, 'after_cursor_execute')
    def tarce_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        if hasattr(context, '_query_span'):
            context._query_span.finish()

    @listens_for(Engine, 'handle_error')
    def trace_handle_error(exception_context):
        context = exception_context.execution_context
        if hasattr(context, '_query_span'):
            context._query_span.log_kv({'exception': str(exception_context.original_exception)})

            if set_error_tag:
                context._query_span.set_tag('error', True)

            context._query_span.finish()
