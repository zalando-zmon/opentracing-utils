import pytest

import opentracing

from mock import MagicMock

from opentracing.ext import tags as opentracing_tags

from basictracer import BasicTracer

from .conftest import Recorder
from opentracing_utils import trace, extract_span_from_kwargs


def is_span_in_kwargs(**kwargs):
    for _, v in kwargs.items():
        if isinstance(v, opentracing.Span):
            return True

    return False


def test_trace_single():

    @trace()
    def f1():
        pass

    recorder = Recorder()
    opentracing.tracer = BasicTracer(recorder=recorder)

    test_span = opentracing.tracer.start_span(operation_name='test_trace')

    with test_span:
        f1()
        f1()
        f1()

    assert len(recorder.spans) == 4
    for span in recorder.spans[:3]:
        assert span.context.trace_id == test_span.context.trace_id
        assert span.parent_id == test_span.context.span_id


def test_trace_follows_from():
    @trace(use_follows_from=True)
    def f1():
        pass

    recorder = Recorder()
    opentracing.tracer = BasicTracer(recorder=recorder)

    test_span = opentracing.tracer.start_span(operation_name='test_trace')

    with test_span:
        f1()

    assert len(recorder.spans) == 2
    assert recorder.spans[0].context.trace_id == test_span.context.trace_id
    assert recorder.spans[0].parent_id == test_span.context.span_id


def test_trace_method():

    class C:
        @trace()
        def func(self):
            pass

    recorder = Recorder()
    opentracing.tracer = BasicTracer(recorder=recorder)

    test_span = opentracing.tracer.start_span(operation_name='test_trace')

    with test_span:
        C().func()

    assert len(recorder.spans) == 2

    assert recorder.spans[0].context.trace_id == test_span.context.trace_id
    assert recorder.spans[0].parent_id == recorder.spans[1].context.span_id


def test_trace_generator():

    @trace()
    def f1():
        list(l2_gen())

    @trace()
    def f2():
        pass

    @trace(pass_span=True)
    def l2_gen(**kwargs):
        s = extract_span_from_kwargs(**kwargs)  # noqa
        f2(span=s)
        for i in range(10):
            yield i

    recorder = Recorder()
    opentracing.tracer = BasicTracer(recorder=recorder)

    test_span = opentracing.tracer.start_span(operation_name='test_trace')

    with test_span:
        f1()

    assert len(recorder.spans) == 4

    assert recorder.spans[0].context.trace_id == test_span.context.trace_id
    assert recorder.spans[0].parent_id == recorder.spans[2].context.span_id

    # Inside generator takes generator as parent!
    assert recorder.spans[1].context.trace_id == test_span.context.trace_id
    assert recorder.spans[1].parent_id == recorder.spans[0].context.span_id

    assert recorder.spans[2].context.trace_id == test_span.context.trace_id
    assert recorder.spans[2].parent_id == recorder.spans[3].context.span_id


@pytest.mark.parametrize('pass_span', (False, True))
def test_trace_nested(pass_span):

    @trace(pass_span=pass_span)
    def parent(**kwargs):
        assert is_span_in_kwargs(**kwargs) is pass_span

        if pass_span:
            current_span = extract_span_from_kwargs(**kwargs)
            assert current_span.operation_name == 'parent'

        nested()

    @trace(pass_span=pass_span)
    def nested(**kwargs):
        assert is_span_in_kwargs(**kwargs) is pass_span

        if pass_span:
            current_span = extract_span_from_kwargs(**kwargs)
            assert current_span.operation_name == 'nested'

    recorder = Recorder()
    opentracing.tracer = BasicTracer(recorder=recorder)

    test_span = opentracing.tracer.start_span(operation_name='test_trace')

    with test_span:
        parent()

    assert len(recorder.spans) == 3

    assert recorder.spans[0].context.trace_id == test_span.context.trace_id
    assert recorder.spans[0].parent_id == recorder.spans[1].context.span_id

    assert recorder.spans[1].context.trace_id == test_span.context.trace_id
    assert recorder.spans[1].parent_id == test_span.context.span_id

    assert recorder.spans[-1].parent_id is None


def test_trace_nested_with_args():

    @trace()
    def parent(arg1, arg2):
        nested(arg1)

    @trace()
    def nested(arg1, **kwargs):
        assert is_span_in_kwargs(**kwargs) is False

    @trace(pass_span=True)
    def expect_span(**kwargs):
        assert is_span_in_kwargs(**kwargs) is True

    recorder = Recorder()
    opentracing.tracer = BasicTracer(recorder=recorder)

    test_span = opentracing.tracer.start_span(operation_name='test_trace')

    with test_span:
        parent(1, 2)

        expect_span()

    assert len(recorder.spans) == 4

    assert recorder.spans[0].context.trace_id == test_span.context.trace_id
    assert recorder.spans[0].parent_id == recorder.spans[1].context.span_id

    assert recorder.spans[1].context.trace_id == test_span.context.trace_id
    assert recorder.spans[1].parent_id == test_span.context.span_id

    assert recorder.spans[-1].parent_id is None


def test_trace_mutliple_spans():

    @trace()
    def parent():
        nested()

    @trace()
    def nested(**kwargs):
        assert is_span_in_kwargs(**kwargs) is False

    recorder = Recorder()
    opentracing.tracer = BasicTracer(recorder=recorder)

    test_span_first = opentracing.tracer.start_span(operation_name='test_trace_first')

    with test_span_first:
        parent()

    assert len(recorder.spans) == 3

    assert recorder.spans[0].context.trace_id == test_span_first.context.trace_id
    assert recorder.spans[0].parent_id == recorder.spans[1].context.span_id

    assert recorder.spans[1].context.trace_id == test_span_first.context.trace_id
    assert recorder.spans[1].parent_id == test_span_first.context.span_id

    assert recorder.spans[-1].parent_id is None
    assert recorder.spans[-1].operation_name == 'test_trace_first'

    # reset recorder
    recorder.reset()
    test_span_second = opentracing.tracer.start_span(operation_name='test_trace_second')

    with test_span_second:
        nested(span=test_span_second)

    assert len(recorder.spans) == 2

    assert recorder.spans[0].context.trace_id == test_span_second.context.trace_id
    assert recorder.spans[0].parent_id == recorder.spans[1].context.span_id

    assert recorder.spans[-1].parent_id is None
    assert recorder.spans[-1].operation_name == 'test_trace_second'


def test_trace_nested_broken_traces():

    @trace()
    def f1():
        pass

    @trace()
    def f2():
        pass

    recorder = Recorder()
    opentracing.tracer = BasicTracer(recorder=recorder)

    test_span = opentracing.tracer.start_span(operation_name='test_trace')

    with test_span:
        f1()

        broken_span = opentracing.tracer.start_span(operation_name='broken_trace')
        with broken_span:
            f1(span=broken_span)

        # Broken traces does not work with stack inspection, it is better to pass the span in this case!
        f2(span=test_span)

    assert len(recorder.spans) == 5

    assert recorder.spans[0].context.trace_id == test_span.context.trace_id
    assert recorder.spans[0].parent_id == recorder.spans[-1].context.span_id

    assert recorder.spans[1].context.trace_id == broken_span.context.trace_id
    assert recorder.spans[1].parent_id == recorder.spans[2].context.span_id

    assert recorder.spans[3].context.trace_id == test_span.context.trace_id
    assert recorder.spans[3].parent_id == recorder.spans[-1].context.span_id

    assert recorder.spans[2].parent_id is None
    assert recorder.spans[2].operation_name == 'broken_trace'

    assert recorder.spans[-1].parent_id is None
    assert recorder.spans[-1].operation_name == 'test_trace'


def test_trace_single_with_tracer_args():

    tags = {'t1': 'v1'}
    operation_name = 'op_name'
    component = 'component'

    @trace(tags=tags, operation_name=operation_name, component=component)
    def f1():
        pass

    recorder = Recorder()
    opentracing.tracer = BasicTracer(recorder=recorder)

    test_span = opentracing.tracer.start_span(operation_name='test_trace')

    with test_span:
        f1()

    tags.update({opentracing_tags.COMPONENT: component})
    assert recorder.spans[0].tags == tags


@pytest.mark.parametrize('return_span', (True, False))
def test_trace_single_with_extractor(return_span):
    recorder = Recorder()
    opentracing.tracer = BasicTracer(recorder=recorder)

    test_span = opentracing.tracer.start_span(operation_name='test_trace')

    other_span = opentracing.tracer.start_span(operation_name='other_span')

    extractor = MagicMock()
    extractor.return_value = test_span if return_span else None

    @trace(span_extractor=extractor)
    def f1():
        pass

    with other_span:
        # other_span could be ignored if extractor returned a span!
        f1(span=other_span)

    if return_span:
        assert recorder.spans[0].context.trace_id == test_span.context.trace_id
        assert recorder.spans[0].parent_id == test_span.context.span_id
    else:
        assert recorder.spans[0].context.trace_id == other_span.context.trace_id
        assert recorder.spans[0].parent_id == other_span.context.span_id


def test_trace_single_with_ignore_parent():

    @trace(ignore_parent_span=True)
    def f1():
        pass

    recorder = Recorder()
    opentracing.tracer = BasicTracer(recorder=recorder)

    test_span = opentracing.tracer.start_span(operation_name='test_trace')

    with test_span:
        # test_span will be ignored!
        f1()

    assert recorder.spans[0].context.trace_id != test_span.context.trace_id
    assert recorder.spans[0].parent_id is None


def test_trace_separate_functions():
    @trace()
    def f1():
        pass

    recorder = Recorder()
    opentracing.tracer = BasicTracer(recorder=recorder)

    dummy_span = opentracing.tracer.start_span(operation_name='dummy_trace')
    dummy_span.finish()

    def actual():
        test_span = opentracing.tracer.start_span(operation_name='test_trace')

        with test_span:
            f1()

        assert len(recorder.spans) == 3
        assert recorder.spans[1].context.trace_id == test_span.context.trace_id
        assert recorder.spans[1].parent_id == test_span.context.span_id

    actual()


def test_trace_loop():
    @trace()
    def f1():
        pass

    def f0():
        f1()

    recorder = Recorder()
    opentracing.tracer = BasicTracer(recorder=recorder)

    for i in range(3):
        test_span = opentracing.tracer.start_span(operation_name='test_trace')
        test_span.set_tag('loop', i)

        with test_span:
            f0()

    assert len(recorder.spans) == 6

    root_spans = recorder.spans[1::2]

    for idx, span in enumerate(recorder.spans[::2]):
        parent_span = root_spans[idx]
        assert parent_span.tags == {'loop': idx}
        assert span.context.trace_id == parent_span.context.trace_id
        assert span.parent_id == parent_span.context.span_id


def test_trace_skip_span():
    def skip_span(skip_me, *args, **kwargs):
        return skip_me

    @trace(skip_span=skip_span)
    def f1(skip_me):
        pass

    recorder = Recorder()
    opentracing.tracer = BasicTracer(recorder=recorder)

    test_span = opentracing.tracer.start_span(operation_name='test_trace')

    with test_span:
        f1(False)
        f1(True)

    assert len(recorder.spans) == 2

    assert recorder.spans[0].context.trace_id == test_span.context.trace_id
    assert recorder.spans[0].parent_id == test_span.context.span_id


def test_trace_with_scope_active():
    @trace()
    def f1():
        pass

    recorder = Recorder()
    opentracing.tracer = BasicTracer(recorder=recorder)

    root_span = None
    with opentracing.tracer.start_active_span(operation_name='test_trace', finish_on_close=True) as scope:
        root_span = scope.span
        f1()
        f1()
        f1()

    assert len(recorder.spans) == 4
    assert root_span is not None
    for span in recorder.spans[:3]:
        assert span.context.trace_id == root_span.context.trace_id
        assert span.parent_id == root_span.context.span_id


def test_trace_with_use_scope_manager():

    # Always use the scope manager
    @trace(use_scope_manager=True)
    def f1():
        assert opentracing.tracer.active_span is not None

    recorder = Recorder()
    opentracing.tracer = BasicTracer(recorder=recorder)

    f1()
    f1()
    f1()

    assert len(recorder.spans) == 3
