"""Backtraces var change from target to program start."""

import ast
import typing

from deepdiff import DeepDiff
from crayons import yellow, cyan

from . import utils
from .basis import ID
from .flow import Node, Flow, VarAppearance, VarModification, VarSwitch
from .basis import FrameID


def _print_node(current: Node, next: Node):
    """For debug."""
    print(yellow("current is: "), f"{current}\n", cyan("next is: "), f"{next}\n")


def trace_flow(flow: Flow):
    """Traces a flow and adds information regarding var changes to its nodes.

    This function is the *core* of Cyberbrain.
    """
    current: Node
    next: Node
    current, next = flow.target.prev, flow.target

    while current is not flow.ROOT:
        # Case 1: non-callsite
        if not current.is_callsite():
            current.sync_tracking_with(next)
            if any(flow.get_and_update_var_changes(current, next)):
                # If any change happened, track all ids appeared in this node.
                current.add_tracking(
                    *utils.find_names(current.code_ast, current.frame_id)
                )
            _print_node(current, next)
            next, current = current, current.prev
            continue

        # Case 2: current is a callsite, next is the first line within the called
        # function.
        if current.step_into is next:
            for identifier in next.tracking:
                for arg_id in current.param_to_arg[identifier]:
                    current.add_tracking(arg_id)
                    current.add_var_switches(
                        VarSwitch(
                            arg_id=arg_id,
                            param_id=identifier,
                            value=current.data[arg_id],
                        )
                    )
            _print_node(current, next)
            next, current = current, current.prev
            continue

        # Case 3: current is a callsite, next is the line after the call.
        current.sync_tracking_with(next)
        args = current.get_args()
        # ids on the left, like 'a', 'b' in 'a, b = f()'
        ids_assigned_to = utils.find_names(current.code_ast, current.frame_id) - args
        returned_from = current.returned_from
        for var_change in flow.get_and_update_var_changes(current, next):
            if var_change.id in args:
                returned_from.add_tracking(current.arg_to_param[var_change.id])
            elif var_change.id in ids_assigned_to:
                returned_from.add_tracking(
                    *utils.find_names(returned_from.code_ast, returned_from.frame_id)
                )
        # TODO: add var changes to returned_from

        _print_node(current, next)
        next, current = returned_from, returned_from.prev
