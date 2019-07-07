"""Utilities to get call site."""

import ast
import dis
import io
import sys
import inspect
import itertools
from collections import namedtuple, defaultdict
from functools import lru_cache

import bytecode as b
import uncompyle6

from . import utils
from .utils import ID

MARK = "__MARK__"


Args = namedtuple("Args", ["args", "kwargs"])


def _compute_offset(instr):
    if sys.version_info >= (3, 6):
        return 2
    return (1, 3)[instr.opcode < dis.HAVE_ARGUMENT]


def compute_offset(instrs: b.Bytecode, i):
    now = 0
    for index, instr in enumerate(instrs):
        # Only real instruction should increase offset
        if type(instr) != b.Instr:
            continue
        now += _compute_offset(instr)
        if i <= now:
            break
    # We stop at instruction before CALL_XXX, by adding 2 we get instr after CALL_XXX.
    return index + 2


class GetArgInfo(ast.NodeVisitor):
    def __init__(self):
        self.activated = False
        self.result = None
        self.value = None

    def visit_Attribute(self, node):
        if node.attr == MARK:
            self.activated = True
            self.value = node.value
            self.visit(node.value)
            self.activated = False

    def visit_Call(self, node):
        self.visit(node.func)
        if self.activated:
            self.result = Args(node.args, node.keywords)
        for each in node.args:
            self.visit(each)
        for each in node.keywords:
            self.visit(each)


def get_cache_code(code):
    bc = b.Bytecode.from_code(code)
    # arg of loading freevar/cellvar represented via integers
    concrete_bc = bc.to_concrete_bytecode()
    return bc, concrete_bc


@lru_cache()
def get_cache_callsite(code, i) -> ast.AST:
    bc, cbc = get_cache_code(code)
    index = compute_offset(bc, i)

    i = 0
    for real_index, instr in enumerate(bc):
        # Again, we need to skip non-instruction object.
        if i == index:
            bc.insert(real_index, b.Instr("LOAD_ATTR", MARK))
            break
        if type(instr) != b.Instr:
            print("type is ", type(instr))
            continue
        i += 1

    string_io = io.StringIO()
    uncompyle6.deparse_code2str(code=bc.to_code(), out=string_io)
    arginfo_visitor = GetArgInfo()
    arginfo_visitor.visit(ast.parse(string_io.getvalue()))
    # arginfo_visitor.value is ast node, for now just return str.
    return arginfo_visitor.value


def get_param_arg_pairs(callsite_ast: ast.Call, arg_info: inspect.ArgInfo):
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
    # Builds a parameter list that expands *args and **kwargs
    parameters = (
        arg_info.args[:]
        + [_ARGS] * len(arg_info.locals[_ARGS])
        + [_KWARGS] * len(arg_info.locals[_KWARGS])
    )
    for arg, param in zip(itertools.chain(pos_args, kw_args), parameters):
        print(ast.dump(arg), param)
        yield arg, ID(param)


def bind_param_arg(callsite_ast: ast.Call, arg_info: inspect.ArgInfo):
    """Binds argument identifiers to parameter identifiers.

    For now we'll flatten parameter identifiers as long as they contribute to the same
    argument, for example:

    def f(x, **kwargs):
        pass
    f(x = {a: 1, b: 2}, y=1, z=2)

    Generates:

    {ID(x): {ID(a), ID(b)}, ID(kwargs): {ID(y), ID(z)}}

    In the future, we *might* record fine grained info.
    """
    param_to_args = defaultdict(set)
    for arg, param in get_param_arg_pairs(callsite_ast, arg_info):
        param_to_args[param] |= utils.find_names(arg)
    return param_to_args
