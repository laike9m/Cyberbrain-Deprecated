"""Unittests for callsite."""

import ast
import inspect

from hamcrest import (
    assert_that,
    contains,
    has_property,
    all_of,
    instance_of,
    has_properties,
)

from . import callsite


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
