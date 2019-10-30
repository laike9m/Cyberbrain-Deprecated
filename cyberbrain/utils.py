"""Utility functions."""

import ast
import dis
import inspect
import io
import sysconfig
import token
import tokenize
import typing
from functools import lru_cache

import astor
import black
import bytecode
import deepdiff

from .basis import ID, Surrounding

try:
    from token import NL as token_NL
except ImportError:
    from tokenize import NL as token_NL

_INSTALLATION_PATHS = list(sysconfig.get_paths().values())


@lru_cache()
def should_exclude(filename):
    """Determines whether we should log events from file.

    As of now, we exclude files from installation path, which usually means:
    .../3.7.1/lib/python3.7
    .../3.7.1/include/python3.7m
    .../lib/python3.7/site-packages

    Also we exclude frozen modules, as well as some weird cases.
    """
    if any(filename.startswith(path) for path in _INSTALLATION_PATHS) or any(
        name in filename
        for name in (
            "importlib._boostrap",
            "importlib._bootstrap_external",
            "zipimport",
            "<string>",  # Dynamically generated frames, like
        )
    ):
        return True

    return False


def grouped(iterable, n):
    """Copies from https://stackoverflow.com/a/5389547/2142577.

    s -> (s0,s1,s2,...sn-1), (sn,sn+1,sn+2,...s2n-1), (s2n,s2n+1,s2n+2,...s3n-1), ...
    """
    return zip(*[iter(iterable)] * n)


def _get_lineno(frame) -> int:
    """Gets line number given current state of the frame.

    Line number is the absolute line number in the module where current execution is at.
    In the past we used to calculate lineno based on lnotab, but since
    `dis.findlinestarts` already does that, there's no need to do it ourselves.
    """
    f_lasti = frame.f_lasti
    lineno_at_lasti = 0
    for offset, lineno in dis.findlinestarts(frame.f_code):
        if offset > f_lasti:
            break
        lineno_at_lasti = lineno
    # Returns here if this is last line in that frame.
    return lineno_at_lasti


def _tokenize_string(s):
    return tokenize.tokenize(io.BytesIO(s.encode("utf-8")).readline)


def get_code_str_and_surrounding(frame):
    """Gets code string and surrounding information for line event.

    The reason to record both code_str and surrounding is because code_str is not
    guaranteed to be unique, for example "a = true" appeared twice. While
    (frame_id, surrounding) is distinct, therefore we can detect duplicate computations
    by checking their (frame_id, surrounding).

    Both lineno and surrounding are 1-based, aka the smallest lineno is 1.
    """
    # Step 0. Gets lineno relative to frame.
    frame_source = inspect.getsource(inspect.getmodule(frame))  # TODO: Caches result.
    toks = list(_tokenize_string(frame_source))  # assuming no exception.
    lineno = _get_lineno(frame)

    # Step 1. Groups toks by logical lines.
    logical_line_start = 1  # skips first element token.ENCODING
    groups = []
    for i in range(logical_line_start, len(toks)):
        if toks[i].type == token.NEWLINE:
            groups.append(toks[logical_line_start : i + 1])
            logical_line_start = i + 1

    # Step 2. Finds matching group.
    if len(groups) == 1:
        return (frame_source, Surrounding(start_lineno=lineno, end_lineno=lineno))

    for group, next_group in zip(groups[:-1], groups[1:]):
        start_lineno, end_lineno = group[0].start[0], group[-1].end[0]
        if start_lineno <= lineno <= end_lineno:
            break
    else:
        # Reachs end of groups
        group = next_group

    # Removes leading NL and DEDENT as they cause untokenize to fail.
    while group[0].type in {token_NL, token.DEDENT, token.INDENT}:
        group.pop(0)
    # When untokenizing, Python adds \\\n for absent lines(because lineno in
    # group doesn't start from 1), removes them.
    return (
        tokenize.untokenize(group).lstrip("\\\n"),
        Surrounding(start_lineno=group[0].start[0], end_lineno=group[-1].end[0]),
    )


class _NameVisitor(ast.NodeVisitor):
    def __init__(self):
        self.names: typing.Set[ID] = set()
        super().__init__()

    def visit_Name(self, node):
        self.names.add(node.id)
        self.generic_visit(node)


def find_names(code_ast: ast.AST) -> typing.Set[ID]:
    """Finds idenditifiers in given ast node."""
    visitor = _NameVisitor()
    visitor.visit(code_ast)
    return {ID(name) for name in visitor.names}


def has_diff(x, y):
    return deepdiff.DeepDiff(x, y) != {}


def parse_code_str(code_str) -> ast.AST:
    """Parses code string in a computation, which can be incomplete.

    Once we found something that leads to error while parsing, we should handle it here.
    """
    if code_str.endswith(":"):
        code_str += "pass"
    try:
        return ast.parse(code_str)
    except IndentationError:
        return ast.parse(code_str.strip())


def ast_to_str(code_ast: ast.AST) -> str:
    # Makes sure code is always in the same format.
    return black.format_str(astor.to_source(code_ast), mode=black.FileMode()).strip()


def dedent(text: str):
    return "\n".join([line.strip() for line in text.splitlines()])


def is_call_instruction(instr: bytecode.Instr):
    return instr.name.startswith("CALL_")
