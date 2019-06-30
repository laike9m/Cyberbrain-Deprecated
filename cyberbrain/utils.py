import sysconfig
import types
import sys
import bytecode
from functools import lru_cache
import uncompyle6
from crayons import red, blue, yellow
import token
import tokenize
import inspect
import io


installation_paths = list(sysconfig.get_paths().values())


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
            "<string>",  # not sure what this is, but it somehow exists.
        )
    ):
        return True

    return False


# Copied from https://stackoverflow.com/a/5389547/2142577
def grouped(iterable, n):
    "s -> (s0,s1,s2,...sn-1), (sn,sn+1,sn+2,...s2n-1), (s2n,s2n+1,s2n+2,...s3n-1), ..."
    return zip(*[iter(iterable)] * n)


def _get_lineno_from_lnotab(frame) -> int:
    """Gets line number given byte code index.

    Line number in lnotab is frame-wise, starts at 0, so is returned line number.

    Algorithm is from
    https://svn.python.org/projects/python/branches/pep-0384/Objects/lnotab_notes.txt

    Note that lnotab represents increment, so we need to add first lineno to get real
    lineno.
    """
    print("co_firstlineno is: ", frame.f_code.co_firstlineno)
    co_lnotab = frame.f_code.co_lnotab
    f_lasti = frame.f_lasti
    lineno = addr = 0
    for addr_incr, line_incr in grouped(co_lnotab, 2):
        addr += addr_incr
        if addr > f_lasti:
            return lineno + frame.f_code.co_firstlineno
        lineno += line_incr
    # Returns here if this is last line in that frame.
    return lineno + frame.f_code.co_firstlineno


def _tokenize_string(s):
    return tokenize.tokenize(io.BytesIO(s.encode("utf-8")).readline)


def get_code_str_and_surrounding(frame):
    """Gets code string and surrounding information for line event.

    "surrounding" is a 2-element tuple (start_lineno, end_lineno), representing a
    logical line. Line number is frame-wise.

    For single-line statement, start_lineno = end_lineno, and is the line number of the
    physical line returned by get_lineno_from_lnotab.

    For multiline statement, start_lineno is the line number of the first physical line,
    end_lineno is the last. Lines from start_lineno to end_lineno -1 should end with
    token.NL(or tokenize.NL before 3.7), line end_lineno should end with token.NEWLINE.

    Example:
    0    a = true
    1    a = true
    2    b = {
    3        'foo': 'bar'
    4    }
    5    c = false

    For the assignment of b, start_lineno = 2, end_lineno = 4

    The reason to record both code_str and surrounding is because code_str is not
    guaranteed to be unique, for example "a = true" appeared twice. While
    (frame_id, surrounding) is distinct, therefore we can detect duplicate computations
    by checking their (frame_id, surrounding).

    Both lineno in _get_lineno_from_lnotab and tokens starts at 1.
    """
    lineno = _get_lineno_from_lnotab(frame)
    frame_source = inspect.getsource(frame)
    toks = list(_tokenize_string(frame_source))  # assuming no exception.

    # Step 1. Groups toks by logical lines.
    logical_line_start = 1  # skips first element token.ENCODING
    groups = []
    for i in range(logical_line_start, len(toks)):
        if toks[i].type == token.NEWLINE:
            groups.append(toks[logical_line_start : i + 1])
            logical_line_start = i + 1

    # Step 2. Finds matching group.
    if len(groups) == 1:
        return frame_source, (lineno, lineno)

    for group, next_group in zip(groups[:-1], groups[1:]):
        start_lineno, end_lineno = group[0].start[0], group[-1].end[0]
        if start_lineno <= lineno <= end_lineno:
            print(group, start_lineno, end_lineno)
            break
    else:
        # Reachs end of groups
        group = next_group

    # Removes leading NL and DEDENT as they cause untokenize to fail.
    while group[0].type in {token.NL, token.DEDENT, token.INDENT}:
        group.pop(0)
    # When untokenizing, Python adds \\\n for absent lines(because lineno in
    # group doesn't start from 1), removes them.
    return (
        tokenize.untokenize(group).lstrip("\\\n"),
        (group[0].start[0] - 1, group[-1].end[0] - 1),
    )
