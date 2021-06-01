import opentracing
import pytest
import ctypes

from sqlalchemy import event
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine import Engine
from sqlalchemy import Column, Integer, String, Boolean

from basictracer import BasicTracer

from .conftest import Recorder

from opentracing_utils import trace
from opentracing_utils.libs._sqlalchemy import trace_sqlalchemy


Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    is_active = Column(Boolean)


def untrace_sqlalchemy():
    try:
        args = []
        for key in event.registry._key_to_collection:
            identifier = key[1]
            if identifier not in ('before_cursor_execute', 'after_cursor_execute', 'handle_error'):
                continue
            fn = ctypes.cast(key[2], ctypes.py_object).value
            args.append([identifier, fn])

        for arg in args:
            event.remove(Engine, *arg)
    except Exception:
        pass


def assert_sqlalchemy_span(span, operation_name='select'):
    assert span.tags['component'] == 'sqlalchemy'
    assert span.tags['db.type'] == 'sql'
    assert span.tags['db.engine'] == 'sqlite'

    assert span.operation_name == operation_name


@pytest.fixture
def session():
    engine = create_engine('sqlite://')
    User.metadata.create_all(engine)
    yield sessionmaker(bind=engine)()
    untrace_sqlalchemy()


@pytest.fixture
def recorder():
    recorder = Recorder()
    recorder.spans = []
    opentracing.tracer = BasicTracer(recorder=recorder)
    yield recorder
    del(recorder)


def test_trace_sqlalchemy(monkeypatch, session, recorder):
    trace_sqlalchemy()

    top_span = opentracing.tracer.start_span(operation_name='top_span')

    with top_span:
        user = User(name='Tracer', is_active=True)
        session.add(user)
        session.commit()

    assert len(recorder.spans) == 2

    sql_span = recorder.spans[0]
    assert sql_span.context.trace_id == top_span.context.trace_id
    assert sql_span.parent_id == top_span.context.span_id

    assert sql_span.tags['db.statement'] == 'INSERT INTO users (name, is_active) VALUES (?, ?)'
    assert_sqlalchemy_span(sql_span, operation_name='insert')


def test_trace_sqlalchemy_scope(monkeypatch, session, recorder):
    trace_sqlalchemy()

    top_span = None
    with opentracing.tracer.start_active_span(operation_name='top_span') as scope:
        top_span = scope.span
        user = User(name='Tracer', is_active=True)
        session.add(user)
        session.commit()

        assert top_span == opentracing.tracer.active_span

    assert len(recorder.spans) == 2

    sql_span = recorder.spans[0]
    assert sql_span.context.trace_id == top_span.context.trace_id
    assert sql_span.parent_id == top_span.context.span_id

    assert sql_span.tags['db.statement'] == 'INSERT INTO users (name, is_active) VALUES (?, ?)'
    assert_sqlalchemy_span(sql_span, operation_name='insert')


def test_trace_sqlalchemy_nested(monkeypatch, session, recorder):
    trace_sqlalchemy()

    top_span = opentracing.tracer.start_span(operation_name='top_span')

    @trace()
    def create_user():
        user = User(name='Tracer')
        session.add(user)
        session.commit()

    with top_span:
        create_user()

    assert len(recorder.spans) == 3

    sql_span = recorder.spans[0]
    assert sql_span.context.trace_id == top_span.context.trace_id
    assert sql_span.parent_id == recorder.spans[1].context.span_id

    assert sql_span.tags['db.statement'] == 'INSERT INTO users (name, is_active) VALUES (?, ?)'
    assert_sqlalchemy_span(sql_span, operation_name='insert')


def test_trace_sqlalchemy_nested_use_scope_manager(monkeypatch, session, recorder):
    trace_sqlalchemy(use_scope_manager=True)

    @trace()
    def create_user():
        user = User(name='Tracer')
        assert opentracing.tracer.active_span.operation_name == 'create_user'
        session.add(user)
        session.commit()

    top_span = None
    with opentracing.tracer.start_active_span(operation_name='top_span') as scope:
        top_span = scope.span
        create_user()

        assert top_span == opentracing.tracer.active_span

    assert len(recorder.spans) == 3

    sql_span = recorder.spans[0]
    assert sql_span.context.trace_id == top_span.context.trace_id
    assert sql_span.parent_id == recorder.spans[1].context.span_id

    assert sql_span.tags['db.statement'] == 'INSERT INTO users (name, is_active) VALUES (?, ?)'
    assert_sqlalchemy_span(sql_span, operation_name='insert')


def test_trace_sqlalchemy_select(monkeypatch, session, recorder):
    trace_sqlalchemy()

    user = User(name='Tracer', is_active=True)
    session.add(user)
    session.commit()

    top_span = opentracing.tracer.start_span(operation_name='top_span')

    with top_span:
        users = [u for u in session.query(User).all()]
        assert len(users) == 1

    sql_span = recorder.spans[1]
    assert sql_span.context.trace_id == top_span.context.trace_id
    assert sql_span.parent_id == top_span.context.span_id

    assert sql_span.tags['db.statement'] == ('SELECT users.id AS users_id, users.name AS users_name, users.is_active '
                                             'AS users_is_active \nFROM users')
    assert_sqlalchemy_span(sql_span)


def test_trace_sqlalchemy_update(monkeypatch, session, recorder):
    trace_sqlalchemy()

    user = User(name='Tracer', is_active=True)
    session.add(user)
    session.commit()

    top_span = opentracing.tracer.start_span(operation_name='top_span')

    with top_span:
        user = session.query(User).first()
        user.is_active = False
        session.add(user)
        session.commit()

    sql_span = recorder.spans[2]
    assert sql_span.context.trace_id == top_span.context.trace_id
    assert sql_span.parent_id == top_span.context.span_id

    assert sql_span.tags['db.statement'] == 'UPDATE users SET is_active=? WHERE users.id = ?'
    assert_sqlalchemy_span(sql_span, operation_name='update')


def test_trace_sqlalchemy_delete(monkeypatch, session, recorder):
    trace_sqlalchemy()

    user = User(name='Tracer', is_active=True)
    session.add(user)
    session.commit()

    top_span = opentracing.tracer.start_span(operation_name='top_span')

    with top_span:
        user = session.query(User).first()
        session.delete(user)
        session.commit()

    sql_span = recorder.spans[2]
    assert sql_span.context.trace_id == top_span.context.trace_id
    assert sql_span.parent_id == top_span.context.span_id

    assert sql_span.tags['db.statement'] == 'DELETE FROM users WHERE users.id = ?'
    assert_sqlalchemy_span(sql_span, operation_name='delete')


def test_trace_sqlalchemy_select_where(monkeypatch, session, recorder):
    trace_sqlalchemy()

    user = User(name='Tracer', is_active=True)
    session.add(user)
    session.commit()

    top_span = opentracing.tracer.start_span(operation_name='top_span')

    with top_span:
        users = [u for u in session.query(User).filter(User.name == 'Tracer')]
        assert len(users) == 1

    sql_span = recorder.spans[1]
    assert sql_span.context.trace_id == top_span.context.trace_id
    assert sql_span.parent_id == top_span.context.span_id

    assert sql_span.tags['db.statement'] == ('SELECT users.id AS users_id, users.name AS users_name, users.is_active '
                                             'AS users_is_active \nFROM users \nWHERE users.name = ?')
    assert_sqlalchemy_span(sql_span)


@pytest.mark.parametrize('error', (False, True))
def test_trace_sqlalchemy_error(monkeypatch, session, recorder, error):
    trace_sqlalchemy(set_error_tag=error)

    top_span = opentracing.tracer.start_span(operation_name='top_span')

    with top_span:
        user = User(name='Tracer', is_active=True)
        session.add(user)
        session.commit()

        with pytest.raises(IntegrityError):
            user = User(name='Tracer', is_active=True)
            session.add(user)
            session.commit()

    # This is ugly but somehow overcomes the inconsistency of spans order!
    span_error = False
    for span in recorder.spans:
        if 'error' in span.tags:
            span_error = True
            break
    assert span_error is error


def test_trace_sqlalchemy_operation_name(monkeypatch, session, recorder):

    def get_operation_name(conn, cursor, statement, parameters, context, executemany):
        return 'custom_query'

    trace_sqlalchemy(operation_name=get_operation_name)

    user = User(name='Tracer', is_active=True)
    session.add(user)
    session.commit()

    assert recorder.spans[0].operation_name == 'custom_query'


def test_trace_sqlalchemy_span_extractor(monkeypatch, session, recorder):
    ignored_span = opentracing.tracer.start_span(operation_name='ignored_span')
    custom_span = opentracing.tracer.start_span(operation_name='custom_span')

    def get_custom_parent_span(conn, cursor, statement, parameters, context, executemany):
        return custom_span

    trace_sqlalchemy(span_extractor=get_custom_parent_span)

    user = User(name='Tracer', is_active=True)
    session.add(user)
    session.commit()

    assert recorder.spans[0].parent_id == custom_span.context.span_id

    custom_span.finish()
    ignored_span.finish()


def test_trace_sqlalchemy_skip_span(monkeypatch, session, recorder):

    def skip_span(conn, cursor, statement, parameters, context, executemany):
        return statement.lower().startswith('insert')

    trace_sqlalchemy(skip_span=skip_span)

    user = User(name='Tracer', is_active=True)
    session.add(user)
    session.commit()

    session.query(User).first()

    assert len(recorder.spans) == 1
    assert recorder.spans[0].operation_name != 'insert'


def test_trace_sqlalchemy_enrich_span(monkeypatch, session, recorder):
    parameters_tag = 'parameters'
    user_name = 'Tracer'

    def enrich_span(span, conn, cursor, statement, parameters, context, executemany):
        span.set_tag(parameters_tag, parameters)

    trace_sqlalchemy(enrich_span=enrich_span)

    user = User(name=user_name, is_active=True)
    session.add(user)
    session.commit()

    assert len(recorder.spans) == 1
    assert parameters_tag in recorder.spans[0].tags
    assert recorder.spans[0].tags[parameters_tag] == (user_name, 1)
