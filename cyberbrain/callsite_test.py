"""Unittests for callsite."""

import ast
import inspect
import sys

import astor
from hamcrest import (
    equal_to,
    all_of,
    assert_that,
    contains,
    has_properties,
    has_property,
    instance_of,
)

from . import callsite


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

    callsite_ast, outer_call_site_ast = f(1, x=2)
    # We can't use assert here cause pytest will modify source and mess up things.
    assert_ast(callsite_ast, "f(1, x=2)")
    assert_that(outer_call_site_ast, equal_to(None))

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


def test_get_param_arg_pairs():
    def f(foo, bar, baz=1, *args, **kwargs):
        return inspect.getargvalues(inspect.currentframe())

    # Tests passing values directly.
    assert_that(
        callsite.get_param_arg_pairs(_get_call(ast.parse("f(1,2)")), f(1, 2)),
        contains(
            contains(all_of(instance_of(ast.Num), has_property("n", 1)), "foo"),
            contains(all_of(instance_of(ast.Num), has_property("n", 2)), "bar"),
        ),
    )

    # Tests passing variables.
    a, b, c = 1, 2, 3
    assert_that(
        callsite.get_param_arg_pairs(_get_call(ast.parse("f(a,b,c)")), f(a, b, z=c)),
        contains(
            contains(all_of(instance_of(ast.Name), has_property("id", "a")), "foo"),
            contains(all_of(instance_of(ast.Name), has_property("id", "b")), "bar"),
            contains(all_of(instance_of(ast.Name), has_property("id", "c")), "baz"),
        ),
    )

    # Tests catching extra args.
    d, e = 4, 5
    assert_that(
        callsite.get_param_arg_pairs(
            _get_call(ast.parse("f(a,b,c,d,qux=e)")), f(a, b, c, d, qux=e)
        ),
        contains(
            contains(all_of(instance_of(ast.Name), has_property("id", "a")), "foo"),
            contains(all_of(instance_of(ast.Name), has_property("id", "b")), "bar"),
            contains(all_of(instance_of(ast.Name), has_property("id", "c")), "baz"),
            contains(all_of(instance_of(ast.Name), has_property("id", "d")), "args"),
            contains(
                all_of(
                    instance_of(ast.keyword),
                    has_properties(
                        {
                            "arg": "qux",
                            "value": all_of(
                                instance_of(ast.Name), has_property("id", "e")
                            ),
                        }
                    ),
                ),
                "kwargs",
            ),
        ),
    )


def test_bind_param_arg():
    def f(foo, bar, baz=1, *args, **kwargs):
        return inspect.getargvalues(inspect.currentframe())

    # Tests passing values directly.
    assert callsite.bind_param_arg(_get_call(ast.parse("f(1,2)")), f(1, 2)) == {
        "foo": set(),
        "bar": set(),
    }

    # Tests passing variables.
    a, b, c = 1, 2, 3
    assert callsite.bind_param_arg(_get_call(ast.parse("f(a,b,c)")), f(a, b, z=c)) == {
        "foo": {"a"},
        "bar": {"b"},
        "baz": {"c"},
    }

    # Tests catching extra args.
    d, e = 4, 5
    assert callsite.bind_param_arg(
        _get_call(ast.parse("f(a,b,c,d,qux=e)")), f(a, b, c, d, qux=e)
    ) == {"foo": {"a"}, "bar": {"b"}, "baz": {"c"}, "args": {"d"}, "kwargs": {"e"}}

    # Tests binding multiple params to one argument.
    assert callsite.bind_param_arg(
        _get_call(ast.parse("f(a,(b,c),c,qux=(d, e))")), f(a, (b, c), c, qux=(d, e))
    ) == {"foo": {"a"}, "bar": {"b", "c"}, "baz": {"c"}, "kwargs": {"d", "e"}}

    # Tests using custom names for args and kwargs.
    def g(*foo, **bar):
        return inspect.getargvalues(inspect.currentframe())

    assert callsite.bind_param_arg(_get_call(ast.parse("g(d,qux=e)")), g(d, qux=e)) == {
        "foo": {"d"},
        "bar": {"e"},
    }

    # TODO: tests nested call.
