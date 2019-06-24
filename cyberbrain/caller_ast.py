# Moves logic from no_magic to here.

from functools import lru_cache
from collections import namedtuple
import math
import bytecode as b
import uncompyle6
import sys
import ast
import io
import dis

MARK = "__MARK__"


Args = namedtuple("Args", ["args", "kwargs"])


def _compute_offset(instr):
    if sys.version_info >= (3, 6):
        return 2
    return (1, 3)[instr._opcode < _opcode.HAVE_ARGUMENT]


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
def get_cache_callsite_code_str(code, i):
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
    uncompyle6.deparse_code2str(bc.to_code(), out=string_io)
    arginfo_visitor = GetArgInfo()
    arginfo_visitor.visit(ast.parse(string_io.getvalue()))
    # arginfo_visitor.value is ast node, for now just return str.
    return ast.dump(arginfo_visitor.value)
