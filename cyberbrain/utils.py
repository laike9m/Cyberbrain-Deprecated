"""Utility functions."""

import ast
import dis
import inspect
import io
import itertools
import sysconfig
import token
import tokenize
import typing
from functools import lru_cache
from types import FrameType
from typing import List, Tuple

import astor
import black
import deepdiff
import executing

from .basis import ID, Surrounding, FrameBelongingType

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


_tokens_cache = {}


def _get_module_token_groups(frame) -> List[List[tokenize.TokenInfo]]:
    """Tokenizes module's source code that the frame belongs to, yields tokens.

    Return value is a list, with every element being a list of tokens that belong to the
    same logical line.
    """
    module, filename = inspect.getmodule(frame), inspect.getsourcefile(frame)
    if filename in _tokens_cache:
        return _tokens_cache[filename]

    source_code = inspect.getsource(module)
    it = tokenize.tokenize(io.BytesIO(source_code.encode("utf-8")).readline)
    next(it, None)  # Skips the first element which is always token.ENCODING
    # Groups tokens by logical lines.
    # [tok1, tok2, NEWLINE, tok3, NEWLINE, tok4, NEWLINE] will result in
    # [[tok1, tok2], [tok3], [tok4]]
    groups = [
        list(group)
        for is_newline, group in itertools.groupby(
            it, lambda tok: tok.type == token.NEWLINE
        )
        if not is_newline
    ]
    _tokens_cache[filename] = groups
    return groups


def get_code_str_and_surrounding(frame) -> Tuple[str, Surrounding]:
    """Gets code string and surrounding information for line event.

    The reason to record both code_str and surrounding is because code_str is not
    guaranteed to be unique, for example "a = true" appeared twice. While
    (frame_id, surrounding) is distinct, therefore we can detect duplicate computations
    by checking their (frame_id, surrounding).

    Both lineno and surrounding are 1-based, aka the smallest lineno is 1.
    """
    lineno = _get_lineno(frame)
    groups: List[List[tokenize.TokenInfo]] = _get_module_token_groups(frame)

    # Given a lineno, locates the logical line that contains this line.
    if len(groups) == 1:
        return (
            inspect.getsource(frame),
            Surrounding(start_lineno=lineno, end_lineno=lineno),
        )

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
    # Note that since we've removed the leading ENCODING token, untokenize will return
    # a str instead of encoded bytes.
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


def get_frame_belonging_type(frame: FrameType) -> FrameBelongingType:
    """Detects the belonging type of the given frame.

    Solution comes from https://github.com/alexmojaki/executing/issues/4.
    """
    executing_obj = executing.Source.executing(frame)
    node = list(executing_obj.statements)[0]
    nodes_from_current_to_top = [node]

    while hasattr(node, "parent") and node.parent:
        nodes_from_current_to_top.append(node.parent)
        node = node.parent

    for n1, n2 in zip(nodes_from_current_to_top[:-1], nodes_from_current_to_top[1:]):
        if isinstance(n1, ast.FunctionDef) and isinstance(n2, ast.ClassDef):
            if frame.f_code.co_name == "__init__":
                return FrameBelongingType.INIT_METHOD
            return FrameBelongingType.INSTANCE_METHOD
    else:  # pylint: disable=W0120
        return FrameBelongingType.UNKNOWN
