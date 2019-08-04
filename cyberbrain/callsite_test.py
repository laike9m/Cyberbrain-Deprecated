"""Unittests for callsite."""

import ast
import inspect
import sys

import astor
from hamcrest import equal_to, assert_that

from . import callsite
from .basis import ID


def assert_ast(ast_node, code_str):
    assert_that(astor.to_source(ast_node).strip(), equal_to(code_str))


def test_get_callsite_ast():
    x = 1

    def f(*args, **kwargs):
        callsite_frame = sys._getframe(1)
        return callsite.get_callsite_ast(callsite_frame.f_code, callsite_frame.f_lasti)

    def g(*args, **kwargs):
        callsite_frame = sys._getframe(1)
        callsite_ast, outer_callsite_ast = callsite.get_callsite_ast(
            callsite_frame.f_code, callsite_frame.f_lasti
        )
        assert_ast(callsite_ast, "g(1, 1)")
        assert_ast(outer_callsite_ast, "f(x, g(1, 1), True if x else False)")

    callsite_ast, outer_callsite_ast = f(1)
    # We can't use assert here cause pytest will modify source and mess up things.
    assert_ast(callsite_ast, "f(1)")
    assert_that(outer_callsite_ast, equal_to(None))

    callsite_ast, outer_callsite_ast = f(1, x=2)
    # We can't use assert here cause pytest will modify source and mess up things.
    assert_ast(callsite_ast, "f(1, x=2)")
    assert_that(outer_callsite_ast, equal_to(None))

    callsite_ast, outer_callsite_ast = f(x, g(1, 1), True if x else False)
    assert_ast(callsite_ast, "f(x, g(1, 1), True if x else False)")
    assert_that(outer_callsite_ast, equal_to(None))

    # Tests multiline won't affect processing ast.
    # fmt: off
    callsite_ast, outer_callsite_ast = f(x,
                                         g(1, 1),
                                         True if x else False)
    assert_ast(callsite_ast, "f(x, g(1, 1), True if x else False)")
    assert_that(outer_callsite_ast, equal_to(None))
    # fmt: on

    def h(x):
        return x

    callsite_ast, outer_callsite_ast = h(h(h(f(1))))
    assert_ast(callsite_ast, "f(1)")
    assert_ast(outer_callsite_ast, "h(f(1))")


def _get_call(module_ast):
    return module_ast.body[0].value


def test_map_param_to_arg():
    def f(foo, bar, baz=1, *args, **kwargs):
        return inspect.getargvalues(inspect.currentframe())

    CALLER_F = (0,)
    CALLEE_F = (0, 0)

    # Tests passing values directly.
    assert callsite.map_param_to_arg(
        _get_call(ast.parse("f(1,2)")),
        f(1, 2),
        callsite_frame_id=CALLER_F,
        callee_frame_id=CALLEE_F,
    ) == {ID("foo", CALLEE_F): set(), ID("bar", CALLEE_F): set()}

    # Tests passing variables.
    a, b, c = 1, 2, 3
    assert callsite.map_param_to_arg(
        _get_call(ast.parse("f(a,b,c)")),
        f(a, b, z=c),
        callsite_frame_id=CALLER_F,
        callee_frame_id=CALLEE_F,
    ) == {
        ID("foo", CALLEE_F): {ID("a", CALLER_F)},
        ID("bar", CALLEE_F): {ID("b", CALLER_F)},
        ID("baz", CALLEE_F): {ID("c", CALLER_F)},
    }

    # Tests catching extra args.
    d, e = 4, 5
    assert callsite.map_param_to_arg(
        _get_call(ast.parse("f(a,b,c,d,qux=e)")),
        f(a, b, c, d, qux=e),
        callsite_frame_id=CALLER_F,
        callee_frame_id=CALLEE_F,
    ) == {
        ID("foo", CALLEE_F): {ID("a", CALLER_F)},
        ID("bar", CALLEE_F): {ID("b", CALLER_F)},
        ID("baz", CALLEE_F): {ID("c", CALLER_F)},
        ID("args", CALLEE_F): {ID("d", CALLER_F)},
        ID("kwargs", CALLEE_F): {ID("e", CALLER_F)},
    }

    # Tests binding multiple params to one argument.
    assert callsite.map_param_to_arg(
        _get_call(ast.parse("f(a,(b,c),c,qux=(d, e))")),
        f(a, (b, c), c, qux=(d, e)),
        callsite_frame_id=CALLER_F,
        callee_frame_id=CALLEE_F,
    ) == {
        ID("foo", CALLEE_F): {ID("a", CALLER_F)},
        ID("bar", CALLEE_F): {ID("b", CALLER_F), ID("c", CALLER_F)},
        ID("baz", CALLEE_F): {ID("c", CALLER_F)},
        ID("kwargs", CALLEE_F): {ID("d", CALLER_F), ID("e", CALLER_F)},
    }

    # Tests using custom names for args and kwargs.
    def g(*foo, **bar):
        return inspect.getargvalues(inspect.currentframe())

    assert callsite.map_param_to_arg(
        _get_call(ast.parse("g(d,qux=e)")),
        g(d, qux=e),
        callsite_frame_id=CALLER_F,
        callee_frame_id=CALLEE_F,
    ) == {
        ID("foo", CALLEE_F): {ID("d", CALLER_F)},
        ID("bar", CALLEE_F): {ID("e", CALLER_F)},
    }

    # TODO: tests nested call.
