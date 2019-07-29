"""Backtraces var change from target to program start."""

import ast
import typing

from deepdiff import DeepDiff

from . import utils
from .basis import ID
from .flow import Flow, VarChange, Node
from .basis import FrameID


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


def trace_var(computation_manager):
    """Backtrace var change."""
    # prints final trace output
    def printer(computation, names):
        print("vars: ")
        for name in names:
            # need to check existence because line event fires before line is executed.
            if name in computation.data[0]:
                print(name, computation.data[0][name], computation.code_str)

    target_identifiers = set()

    # Finally, backtrace the records of each line
    for computation in reversed(computation_manager.computations):
        if computation.event_type == "line":
            names = utils.find_names(parse_code_str(computation.code_str))
            if target_identifiers & names:
                printer(computation, names)
                target_identifiers |= names
        elif computation.event_type == "call":
            names = utils.find_names(parse_code_str(computation.code_str))
            if target_identifiers & names:
                printer(computation, names)
                target_identifiers |= names


def trace_flow(flow: Flow):
    """Traces a flow and generates final output, aka the var change process."""
    current: Node
    next: Node
    current, next = flow.target.prev, flow.target

    while current is not flow.start:
        if not current.is_callsite():
            current.sync_tracking_with(next.tracking)
            var_changes, var_appears = flow.get_var_changes(current, next)
            current.add_var_changes(*var_changes, *var_appears)
            current.add_tracking(*(var_change.id for var_change in var_changes))
            next, current = current, current.prev
            continue

        # TODO: current is callsite
