"""Utilities to get call site."""

import ast
import dis
import io
import sys
import inspect
import itertools
from collections import namedtuple, defaultdict
from functools import lru_cache
from typing import Dict, Tuple, Set, Iterable

import astpretty
import bytecode as b
import uncompyle6

from . import utils
from .basis import ID, FrameID

MARK = "__MARK__"


Args = namedtuple("Args", ["args", "kwargs"])


def _compute_offset(instr):
    if sys.version_info >= (3, 6):
        return 2
    return (1, 3)[instr.opcode < dis.HAVE_ARGUMENT]


def compute_offset(instrs: b.Bytecode, last_i):
    now = 0
    for index, instr in enumerate(instrs):
        # Only real instruction should increase offset
        if type(instr) != b.Instr:
            continue
        now += _compute_offset(instr)
        if now > last_i:
            break
    # When calling a function, caller_frame.last_i points to the instruction just before
    # CALL_XXX. When now > last_i, it stops at CALL_XXX, by adding 1 we get the position
    # after CALL_XXX, and that's where we want to insert __MARK__.
    return index + 1


class MarkedCallVisitor(ast.NodeVisitor):
    """A node visitor that locates and records call node with __MARK__.

    We use __MARK__ to mark a call that's being executed, e.g. f(a, b).__MARK__
    We finds __MARK__ by checking node.attr in visit_Attribute, and node.value is
    f(a, b), which is what we want.

    Meanwhile, this visitor also records the parent of each ast node.
    """

    class RemoveMarkTransformer(ast.NodeTransformer):
        """Node transformer that removes __MARK__.

        f(1).__MARK__ --> f(1)
        """

        def visit_Attribute(self, node):
            if node.attr == MARK:
                return node.value

    remove_remark_transformer = RemoveMarkTransformer()

    def __init__(self):
        self.activated = False
        self.callsite_ast = None

    def get_outer_call(self):
        """Finds outer call in case callsite_ast represents a nested call.

        Given f(g(h()))
        if current callsite_ast is h(), returns g(h()).
        if current callsite_ast is g(h()), returns f(g(h())).
        If current callsite_ast is f(g(h())), returns None.

        This method should be called after calling .visit() to ensure non-None
        callsite_ast. It recursively visits all parent nodes to find the nearest Call
        node.
        """
        if self.callsite_ast is None:
            raise RuntimeError("get_outer_call should be called after .visit()")

        node = self.callsite_ast
        while hasattr(node, "parent"):
            node = node.parent
            if isinstance(node, ast.Call):
                return self.remove_remark_transformer.visit(node)
        return None

    def _add_parent(self, node):
        for child in ast.iter_child_nodes(node):
            child.parent = node

    def generic_visit(self, node):
        self._add_parent(node)
        super().generic_visit(node)

    def visit_Attribute(self, node):
        self._add_parent(node)
        if node.attr == MARK:
            self.activated = True
            self.callsite_ast = node.value
            self.visit(node.value)
            self.activated = False

    def visit_Call(self, node):
        self._add_parent(node)
        self.visit(node.func)
        for each in node.args:
            self.visit(each)
        for each in node.keywords:
            self.visit(each)


@lru_cache()
def get_callsite_ast(code, last_i) -> ast.AST:
    bc = b.Bytecode.from_code(code)
    index = compute_offset(bc, last_i)
    bc.insert(index, b.Instr("LOAD_ATTR", MARK))

    string_io = io.StringIO()
    uncompyle6.deparse_code2str(code=bc.to_code(), out=string_io)
    visitor = MarkedCallVisitor()
    visitor.visit(ast.parse(string_io.getvalue()))
    return visitor.callsite_ast, visitor.get_outer_call()


def get_param_arg_pairs(
    callsite_ast: ast.Call, arg_info: inspect.ArgInfo
) -> Iterable[Tuple[str, str]]:
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
    # we can emit a 1-to-1 pair of (arg, param)
    parameters = arg_info.args[:]

    # There could be no *args or *kwargs in signature.
    if _ARGS is not None:
        parameters += [_ARGS] * len(arg_info.locals[_ARGS])
    if _KWARGS is not None:
        parameters += [_KWARGS] * len(arg_info.locals[_KWARGS])

    for arg, param in zip(itertools.chain(pos_args, kw_args), parameters):
        yield arg, param


def map_param_to_arg(
    callsite_ast: ast.Call,
    arg_info: inspect.ArgInfo,
    *,
    callsite_frame_id: FrameID,
    callee_frame_id: FrameID,
) -> Dict[FrameID, Set[FrameID]]:
    """Maps argument identifiers to parameter identifiers.

    For now we'll flatten parameter identifiers as long as they contribute to the same
    argument, for example:

    def f(x, **kwargs):
        pass
    f(x = {a: 1, b: 2}, y=1, z=2)

    Generates:

    {
        ID('x', (0, 0)): {ID('a', (0,)), ID('b', (0,))},
        ID('kwargs', (0, 0)): {ID('y', (0,)), ID('z', (0,))}
    }

    In the future, we *might* record fine grained info.
    """
    return {
        ID(param, callee_frame_id): utils.find_names(arg, callsite_frame_id)
        for arg, param in get_param_arg_pairs(callsite_ast, arg_info)
    }
