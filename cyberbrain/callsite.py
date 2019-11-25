"""Utilities to get call site."""

import ast
import inspect
import itertools
from collections import namedtuple
from typing import Dict, Iterable, Set, Tuple

from . import utils
from .basis import ID

Args = namedtuple("Args", ["args", "kwargs"])


def get_param_arg_pairs(
    callsite_ast: ast.Call, arg_info: inspect.ArgInfo
) -> Iterable[Tuple[ast.AST, str]]:
    """Generates parameter, argument pairs.

    Example:

    def def f(foo, bar, baz=1, *args, **kwargs):
        pass
    f(a,b,c,d,qux=e)

    Generates:

    Name(id='a', ctx=Load()), foo
    Name(id='b', ctx=Load()), bar
    Name(id='c', ctx=Load()), baz
    Name(id='d', ctx=Load()), args
    keyword(arg='qux', value=Name(id='e', ctx=Load())), kwargs
    """
    _ARGS = arg_info.varargs  # extra arguments' name, could be anything.
    _KWARGS = arg_info.keywords  # extra kw-arguments' name, could be anything.

    pos_args = callsite_ast.args
    kw_args = callsite_ast.keywords
    # Builds a parameter list that expands *args and **kwargs to their length, so that
    # we can emit a 1-to-1 pair of (arg, param).
    # Excludes self since it's not explicitly passed from caller.
    parameters = [arg for arg in arg_info.args if arg != "self"]

    # There could be no *args or *kwargs in signature.
    if _ARGS is not None:
        parameters += [_ARGS] * len(arg_info.locals[_ARGS])
    if _KWARGS is not None:
        parameters += [_KWARGS] * len(arg_info.locals[_KWARGS])

    for arg, param in zip(itertools.chain(pos_args, kw_args), parameters):
        yield arg, param


def get_param_to_arg(
    callsite_ast: ast.Call, arg_info: inspect.ArgInfo
) -> Dict[ID, Set[ID]]:
    """Maps argument identifiers to parameter identifiers.

    For now we'll flatten parameter identifiers as long as they contribute to the same
    argument, for example:

    def f(x, **kwargs):
        pass
    f(x = {a: 1, b: 2}, y=1, z=2)

    Generates:
    {
        ID('x'): {ID('a'), ID('b')},
        ID('kwargs'): {ID('y'), ID('z')}
    }

    In the future, we *might* record fine grained info.
    """
    return {
        ID(param): utils.find_names(arg)
        for arg, param in get_param_arg_pairs(callsite_ast, arg_info)
    }
