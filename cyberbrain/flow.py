"""Execution flow that represents a program's execution."""

import ast
from dataclasses import dataclass
from typing import Any, Dict, Set, Tuple, List

import astor

from .basis import ID
from . import backtrace
from .basis import FrameID


class TrackingMetadata:
    """Class that stores metadata during tracing."""

    def __init__(
        self,
        data: Dict[ID, Any],
        code_str: str = None,
        code_ast: ast.AST = None,
        arg_to_param: Dict[ID, ID] = None,
    ):
        if not any([code_str, code_ast]):
            raise ValueError("Should provide code_str or code_ast.")
        self.code_str = code_str or astor.to_source(code_ast)
        self.code_ast = code_ast or backtrace.parse_code_str(code_str)
        # It seems that tracking and data should all be flattened, aka they should
        # simply be a mapping of ID -> value. When backtracing, we don't really care
        # about where an identifer is defined in, we only care about whether its value
        # has changed during execution.
        self.tracking: Set[ID] = set()
        self.var_changes = set()
        self.data = data

    def __repr__(self):
        return "%s\ntracking:%s\nvar changes:%s" % (
            code_str,
            self.tracking,
            self.var_changes,
        )

    def add_var_changes(self, *var_changes):
        self.var_changes |= set(var_changes)

    def sync_tracking_with(self, other: "Node"):
        self.add_tracking(*node.tracking)

    def add_tracking(self, *new_ids: ID):
        """Updates identifiers being tracked.

        Identifiers being tracked must exist in data because we can't track something
        that don't exist in previous nodes.
        """
        for new_id in new_ids:
            if new_id in self.data:
                self.tracking.add(new_id)


class Node:
    """Basic unit of an execution flow."""

    def __init__(self, frame_id: FrameID, **kwargs):
        self.frame_id = frame_id
        self.prev = None
        self.next = None
        self.step_into = None
        self.returned_from = None
        self.metadata = TrackingMetadata(**kwargs)

    def __getattr__(self, name):
        """Redirects attributes and calls to metadata.

        __getattr__ is only called when name is not in node's __dict__.
        """
        return getattr(self.metadata, name)

    def __repr__(self):
        return str(self.metadata)

    def is_callsite(self):
        return self.step_into is not None

    def build_relation(self, **relation_dict: Dict[str, "Node"]):
        """A convenient function to add relations at once.

        Usage:
            node.build_relation(prev=node_x, next=node_y)
        """
        for relation_name, node in relation_dict.items():
            if relation_name not in {"prev", "next", "step_into", "returned_from"}:
                raise Exception("wrong relation_name: " + relation_name)
            setattr(self, relation_name, node)


_PLACE_HOLDER = object()


@dataclass
class VarAppear:
    """Variable appears in current frame."""

    id: ID
    value: Any


@dataclass
class VarChange:
    """Variable value changes in current frame."""

    id: ID
    old_value: Any
    new_value: Any


@dataclass
class VarSwitch:
    """Variable switches at callsite."""

    old_id: ID
    new_id: ID
    value: Any


def get_var_changes(
    current: Node, next: Node
) -> Tuple[List[VarChange], List[VarAppear]]:
    """Gets changed variables in the same frame."""
    var_changes = []
    var_appears = []
    for var_id in next.tracking:
        old_value = current.data.get(var_id, _PLACE_HOLDER)
        new_value = next.data[var_id]
        if old_value is _PLACE_HOLDER:
            var_appears.append(VarAppear(id=var_id, value=new_value))
        elif utils.has_diff(new_value, old_value):
            var_changes.append(VarChange(old_value, new_value, id=var_id))
    return var_changes, var_appears


def get_var_switch():
    """Gets var changes at callsite."""


class Flow:
    """Class that represents program's execution.

    A flow consists of multiple Calls and Nodes.
    """

    def __init__(self, start: Node, target: Node):
        self.start = start
        self.target = target
        self._update_target_id()

    def _update_target_id(self) -> ID:
        """Gets ID('x') out of cyberbrain.register(x)."""
        register_call_ast = ast.parse(self.target.code_str.strip())
        assert register_call_ast.body[0].value.func.value.id == "cyberbrain"

        # Finds the target identifier by checking argument passed to register().
        # Assuming argument is a single identifier.
        self.target.add_tracking(
            ID(register_call_ast.body[0].value.args[0].id, self.target.frame_id)
        )
