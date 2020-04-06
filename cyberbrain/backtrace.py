"""Backtraces var change from target to program start."""

from absl import flags

from . import utils
from .basis import ID, FrameBelongingType
from .flow import Flow, Node, VarSwitch

FLAGS = flags.FLAGS


def trace_flow(flow: Flow):
    """Traces a flow and adds information regarding var changes to its nodes.

    This function is the *core* of Cyberbrain.
    """
    current: Node
    next: Node
    current, next = flow.target.prev, flow.target

    while current is not flow.ROOT:
        # Case 1: non-callsite
        if not current.is_callsite:
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
                # Skips 'self' parameter for __init__ call, since it's not passed in
                # from caller.
                # For simplicity, assume the first argument is always named 'self'.
                if (
                    next.frame_id.frame_belonging_type == FrameBelongingType.INIT_METHOD
                    and identifier == "self"
                ):
                    continue
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

        # If this is calling __init__, tracks self.
        if (
            returned_from.frame_id.frame_belonging_type
            == FrameBelongingType.INIT_METHOD
        ):
            returned_from.add_tracking(ID("self"))

        for var_change in current.get_and_update_var_changes(next):
            if var_change.id in args:
                returned_from.add_tracking(current.arg_to_param[var_change.id])
            # TODO: 这里对于 __init__ 应当有一些特殊处理。比如 inst = MyClass()，这里会有 VarAppearance(id='inst')
            # 因此就会进入下面这个 elif，track returned_from 中出现的所有 identifiers.
            # 然而实际上 __init__ 没有 explict return，所以这种处理可能会 track 多余的 id.
            # 这个很好解决，只要 track 函数的第一个参数就行了
            #
            # 另一个问题是，即使真的要 track self，self 并不是从 caller 传入的，导致
            # for arg_id in current.param_to_arg[identifier] 出现 KeyError。
            # 解决方法是在 FrameID 中记录这个 frame 是不是 method.

            # __init__ has no return statement.
            if (
                returned_from.frame_id.frame_belonging_type
                == FrameBelongingType.INIT_METHOD
            ):
                continue

            if var_change.id in ids_assigned_to:
                # The return statement contributes to relevant changes. This value will
                # be used in formatting to determine whether to show returned value.
                returned_from.is_relevant_return = True
                returned_from.add_tracking(*utils.find_names(returned_from.code_ast))
        returned_from.update_var_changes_before_return()

        next, current = returned_from, returned_from.prev
