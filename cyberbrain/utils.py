"""Utility functions."""

import copy
import inspect
import io
import os
import sysconfig
import token
import tokenize
import typing
from collections import defaultdict
from functools import lru_cache

try:
    from token import ENCODING as token_ENCODING
    from token import NL as token_NL
    from token import COMMENT as token_COMMENT
except ImportError:
    from tokenize import ENCODING as token_ENCODING
    from tokenize import NL as token_NL
    from tokenize import COMMENT as token_COMMENT

# "surrounding" is a 2-element tuple (start_lineno, end_lineno), representing a
# logical line. Line number is frame-wise.
#
# For single-line statement, start_lineno = end_lineno, and is the line number of the
# physical line returned by get_lineno_from_lnotab.
#
# For multiline statement, start_lineno is the line number of the first physical line,
# end_lineno is the last. Lines from start_lineno to end_lineno -1 should end with
# token.NL(or tokenize.NL before 3.7), line end_lineno should end with token.NEWLINE.
#
# Example:
# 0    a = true
# 1    a = true
# 2    b = {
# 3        'foo': 'bar'
# 4    }
# 5    c = false
#
# For the assignment of b, start_lineno = 2, end_lineno = 4
Surrounding = typing.NamedTuple(
    "Surrounding", [("start_lineno", int), ("end_lineno", int)]
)

SourceLocation = typing.NamedTuple(
    "SourceLocation", [("filepath", str), ("lineno", int)]
)

installation_paths = list(sysconfig.get_paths().values())


@lru_cache()
def _on_laike9m_pc():
    return os.environ.get("MY_PC") == "true"


@lru_cache()
def should_exclude(filename):
    """Determines whether we should log events from file.

    As of now, we exclude files from installation path, which usually means:
    .../3.7.1/lib/python3.7
    .../3.7.1/include/python3.7m
    .../lib/python3.7/site-packages

    Also we exclude frozen modules, as well as some weird cases.
    """
    if any(filename.startswith(path) for path in installation_paths) or any(
        name in filename
        for name in (
            "importlib._boostrap",
            "importlib._bootstrap_external",
            "zipimport",
            "<string>",  # Dynamically generated frames, like
        )
    ):
        return True

    # Exclude tracking Cyberbrain's own execution on dev PC to enable pytest.
    return _on_laike9m_pc() and "cyberbrain" in filename


def grouped(iterable, n):
    """Copies from https://stackoverflow.com/a/5389547/2142577.

    s -> (s0,s1,s2,...sn-1), (sn,sn+1,sn+2,...s2n-1), (s2n,s2n+1,s2n+2,...s3n-1), ...
    """
    return zip(*[iter(iterable)] * n)


def _get_lineno_base(toks) -> int:
    """Gets line number for the initial instruction in frame.

    The reason we need this method is because I haven't found a good way to find the
    start line number in a frame(it's not always zero).

    For example, in a module like this:

    1   # encoding: utf-8
    2   '''
    3   doc string
    4   '''
    5
    6   import foo

    co_firstlineno tells us lineno is actually 4, not zero, but more importantly, this
    lineno is relative to the entire source file, not frame.

    The first two pairs of lnotab are (4, 2), (8, 1). The '2' represents byte offset
    from end of docstring to import statement, so the lineno of 'import foo' is 4+2=6,
    relative to the file start, but what is the lineno of 'import foo' in that frame?

    One possible solution could be to always tokenize the entire file, but I don't want
    to do that. Instead, I choose to manually the base line number. Leading doc string
    and comments seems to be the only case that base lineno is not 1.

    Let me know if you have a better solution.
    """
    for i, tok in enumerate(toks):
        if tok.type not in {token_ENCODING, token_NL, token.STRING, token_COMMENT}:
            return tok.end[0]


def _get_lineno_offset(frame) -> int:
    """Gets line number given byte code index.

    Line number in lnotab is frame-wise, starts at 0, so is returned line number.

    Algorithm is from
    https://svn.python.org/projects/python/branches/pep-0384/Objects/lnotab_notes.txt

    Note that lnotab represents increment, so we need to add first lineno to get real
    lineno.
    """
    co_lnotab = frame.f_code.co_lnotab
    f_lasti = frame.f_lasti
    lineno = addr = 0
    for addr_incr, line_incr in grouped(co_lnotab, 2):
        addr += addr_incr
        if addr > f_lasti:
            return lineno
        lineno += line_incr
    # Returns here if this is last line in that frame.
    return lineno


def _tokenize_string(s):
    return tokenize.tokenize(io.BytesIO(s.encode("utf-8")).readline)


def get_code_str_and_surrounding(frame):
    """Gets code string and surrounding information for line event.

    The reason to record both code_str and surrounding is because code_str is not
    guaranteed to be unique, for example "a = true" appeared twice. While
    (frame_id, surrounding) is distinct, therefore we can detect duplicate computations
    by checking their (frame_id, surrounding).

    Both lineno in _get_lineno_offset_from_lnotab and tokens starts at 1.
    """
    # Step 0. Gets lineno relative to frame.
    frame_source = inspect.getsource(frame)
    toks = list(_tokenize_string(frame_source))  # assuming no exception.
    lineno_in_frame = _get_lineno_base(toks) + _get_lineno_offset(frame)

    # Step 1. Groups toks by logical lines.
    logical_line_start = 1  # skips first element token.ENCODING
    groups = []
    for i in range(logical_line_start, len(toks)):
        if toks[i].type == token.NEWLINE:
            groups.append(toks[logical_line_start : i + 1])
            logical_line_start = i + 1

    # Step 2. Finds matching group.
    if len(groups) == 1:
        return (
            frame_source,
            Surrounding(start_lineno=lineno_in_frame, end_lineno=lineno_in_frame),
        )

    for group, next_group in zip(groups[:-1], groups[1:]):
        start_lineno, end_lineno = group[0].start[0], group[-1].end[0]
        if start_lineno <= lineno_in_frame <= end_lineno:
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
        Surrounding(
            start_lineno=group[0].start[0] - 1, end_lineno=group[-1].end[0] - 1
        ),
    )


def traverse_frames(frame):
    """Records variables from bottom to top."""
    frame_vars = defaultdict(dict)  # [frame_level_up][var_name]
    frame_level_up = 0
    while frame is not None:
        for var_name, var_value in frame.f_locals.items():
            try:
                frame_vars[frame_level_up][var_name] = copy.deepcopy(var_value)
            except TypeError:
                try:
                    frame_vars[frame_level_up][var_name] = copy.copy(var_value)
                except TypeError:
                    frame_vars[frame_level_up][var_name] = var_value
        frame = frame.f_back
        frame_level_up += 1
    return frame_vars
