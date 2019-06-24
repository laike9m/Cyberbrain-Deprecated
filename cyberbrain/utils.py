import sysconfig
import types
import sys
import bytecode
from functools import lru_cache
import uncompyle6
from crayons import red, blue, yellow


paths = list(sysconfig.get_paths().values())


@lru_cache()
def should_exclude(filename):
    if (
        "importlib._boostrap" in filename
        or 'importlib._bootstrap_external' in filename
        or 'zipimport' in filename
    ):
        return True
    for path in paths:
        if filename.startswith(path):
            return True
    return False


# Copied from https://stackoverflow.com/a/5389547/2142577
def grouped(iterable, n):
    "s -> (s0,s1,s2,...sn-1), (sn,sn+1,sn+2,...s2n-1), (s2n,s2n+1,s2n+2,...s3n-1), ..."
    return zip(*[iter(iterable)] * n)


@lru_cache()
def get_lineno_from_lnotab(co_lnotab: bytes, f_lasti: int) -> int:
    """Gets line number given byte code index.

    Line number in lnotab is frame-wise, so is returned line number.

    Algorithm is from
    https://svn.python.org/projects/python/branches/pep-0384/Objects/lnotab_notes.txt
    """
    # print(yellow('in get_lineno_from_lnotab: '), co_lnotab, f_lasti)
    lineno = addr = 0
    for addr_incr, line_incr in grouped(co_lnotab, 2):
        addr += addr_incr
        if addr > f_lasti:
            return lineno
        lineno += line_incr
    return lineno  # Returns here if this is last line in that frame.
