"""Unittests for callsite."""

import ast
import inspect

from . import callsite
from .basis import ID


def _get_call(module_ast: ast.Module) -> ast.Call:
    assert isinstance(
        module_ast.body[0], ast.Expr
    ), "Passed in code is not a call expression."

    return module_ast.body[0].value


def test_get_param_to_arg():
    def f(foo, bar, baz=1, *args, **kwargs):
        return inspect.getargvalues(inspect.currentframe())

    # Tests passing values directly.
    assert callsite.get_param_to_arg(_get_call(ast.parse("f(1,2)")), f(1, 2)) == {
        ID("foo"): set(),
        ID("bar"): set(),
    }

    # Tests passing variables.
    a, b, c = 1, 2, 3
    assert callsite.get_param_to_arg(
        _get_call(ast.parse("f(a,b,c)")), f(a, b, z=c)
    ) == {ID("foo"): {ID("a")}, ID("bar"): {ID("b")}, ID("baz"): {ID("c")}}

    # Tests catching extra args.
    d, e = 4, 5
    assert callsite.get_param_to_arg(
        _get_call(ast.parse("f(a,b,c,d,qux=e)")), f(a, b, c, d, qux=e)
    ) == {
        ID("foo"): {ID("a")},
        ID("bar"): {ID("b")},
        ID("baz"): {ID("c")},
        ID("args"): {ID("d")},
        ID("kwargs"): {ID("e")},
    }

    # Tests binding multiple params to one argument.
    assert callsite.get_param_to_arg(
        _get_call(ast.parse("f(a,(b,c),c,qux=(d, e))")), f(a, (b, c), c, qux=(d, e))
    ) == {
        ID("foo"): {ID("a")},
        ID("bar"): {ID("b"), ID("c")},
        ID("baz"): {ID("c")},
        ID("kwargs"): {ID("d"), ID("e")},
    }

    # Tests using custom names for args and kwargs.
    def g(*foo, **bar):
        return inspect.getargvalues(inspect.currentframe())

    assert callsite.get_param_to_arg(
        _get_call(ast.parse("g(d,qux=e)")), g(d, qux=e)
    ) == {ID("foo"): {ID("d")}, ID("bar"): {ID("e")}}

    # Tests signature without args or kwargs.
    def h(x):
        return inspect.getargvalues(inspect.currentframe())

    assert callsite.get_param_to_arg(_get_call(ast.parse("h(a)")), h(a)) == {
        ID("x"): {ID("a")}
    }

    # TODO: tests nested call.
