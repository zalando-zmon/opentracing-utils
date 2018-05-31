import opentracing
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean

from basictracer import BasicTracer

from .conftest import Recorder

from opentracing_utils import trace
from opentracing_utils.libs._sqlalchemy import trace_sqlalchemy

# Actual tracing here!
trace_sqlalchemy()

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    is_active = Column(Boolean)


def assert_sqlalchemy_span(span, operation_name='select'):
    assert span.tags['component'] == 'sqlalchemy'
    assert span.tags['db.type'] == 'sql'
    assert span.tags['db.engine'] == 'sqlite'

    assert span.operation_name == operation_name


@pytest.fixture
def session():
    engine = create_engine('sqlite://')
    User.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


@pytest.fixture
def recorder():
    recorder = Recorder()
    opentracing.tracer = BasicTracer(recorder=recorder)
    return recorder


def test_trace_sqlalchemy(monkeypatch, session, recorder):

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


def test_trace_sqlalchemy_nested(monkeypatch, session, recorder):
    top_span = opentracing.tracer.start_span(operation_name='top_span')

    @trace()
    def create_user():
        user = User(name='Tracer', is_active=True)
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


def test_trace_sqlalchemy_select(monkeypatch, session, recorder):
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
