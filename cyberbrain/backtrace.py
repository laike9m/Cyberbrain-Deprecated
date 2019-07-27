"""Backtraces var change from target to program start."""

import ast
import typing

from deepdiff import DeepDiff

from . import utils
from .utils import ID
from .flow import Flow, VarChange, Node
from .frame_id import FrameID


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
            print("code_str is:", computation.code_str)
            names = utils.find_names(parse_code_str(computation.code_str))
            if target_identifiers & names:
                printer(computation, names)
                target_identifiers |= names
        elif computation.event_type == "call":
            names = utils.find_names(parse_code_str(computation.code_str))
            if target_identifiers & names:
                printer(computation, names)
                target_identifiers |= names


def _has_diff(x, y):
    return DeepDiff(x, y) != {}


def trace_flow(flow: Flow):
    """Traces a flow and generates final output, aka the var change process."""
    current: Node
    next: Node
    current, next = flow.target.prev, flow.target

    # while current is not flow.start:
    #     if not current.is_callsite():
    #         current.update_tracking(*next.tracking)
    #     next, step_into, returned_from = (
    #         current.next,
    #         current.step_into,
    #         current.returned_from,
    #     )
    #     local_targets = targets.get(current.frame_id, set())
    #     if current.returned_from is None:  # is not call node
    #         for identifier in targets[current.frame_id]:
    #             if _has_diff(current.data[identifier], next.data[identifier]):
    #                 # Note that we add var change to current, because data contains the
    #                 # value before executing this node.
    #                 current.add_var_change(
    #                     VarChange(
    #                         id=identifier,
    #                         old_value=current.data[identifier],
    #                         new_value=next.data[identifier],
    #                     )
    #                 )
    #     else:
    #         # TODO: deal with callsite.
    #         pass
