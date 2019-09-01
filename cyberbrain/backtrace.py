"""Backtraces var change from target to program start."""


from crayons import cyan, yellow

from . import utils
from .flow import Flow, Node, VarSwitch


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
            if any(current.get_and_update_var_changes(next)):
                # If any change happened, track all ids appeared in this node.
                current.add_tracking(*utils.find_names(current.code_ast))
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
                            value=current.vars[arg_id],
                        )
                    )
            next, current = current, current.prev
            continue

        # Case 3: current is a callsite, next is the line after the call.
        current.sync_tracking_with(next)
        args = current.get_args()
        # ids on the left, like 'a', 'b' in 'a, b = f()'
        ids_assigned_to = utils.find_names(current.code_ast) - args
        returned_from = current.returned_from
        for var_change in current.get_and_update_var_changes(next):
            if var_change.id in args:
                returned_from.add_tracking(current.arg_to_param[var_change.id])
            elif var_change.id in ids_assigned_to:
                returned_from.add_tracking(*utils.find_names(returned_from.code_ast))
        returned_from.update_var_changes_before_return()

        next, current = returned_from, returned_from.prev
