"""Execution flow that represents a program's execution."""

import ast
import typing
from dataclasses import dataclass

import astor

from .utils import ID
from . import backtrace
from .frame_id import FrameID


@dataclass
class VarAppear:
    """Variable/Idenfier appears in current frame."""

    id: ID
    value: typing.Any


@dataclass
class VarChange:
    """Variable/Idenfier changes in current frame."""

    id: ID
    old_value: typing.Any
    old_value: typing.Any


@dataclass
class VarSwitch:
    """Variable/Idenfier switches at callsite."""

    old_id: ID
    new_id: ID
    value: typing.Any


class TrackingMetadata:
    """Class that stores metadata during tracing."""

    def __init__(
        self,
        data: typing.Dict,
        code_str: str = None,
        code_ast: ast.AST = None,
        arg_to_param: typing.Dict[ID, ID] = None,
    ):
        if not any([code_str, code_ast]):
            raise ValueError("Should provide code_str or code_ast.")
        self.code_str = code_str or astor.to_source(code_ast)
        self.code_ast = code_ast or backtrace.parse_code_str(code_str)
        self.var_changes = set()
        self.tracking: typing.Set[ID] = set()
        # For simplicity, uses a dict to represent data for now.
        self.data = data

    def add_var_change(self, var_change):
        self.var_changes.add(var_change)

    def update_tracking(self, *new_ids: ID):
        """Updates identifiers being tracked.

        When updating tracking, identifiers need to exist in data because we can't
        tracking identifiers that don't exist.
        """
        for new_id in new_ids:
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

    def is_callsite(self):
        return self.step_into is not None

    def add_var_change(self, var_change):
        self.metadata.add_var_change(var_change)

    def update_tracking(self, tracking: typing.Set[ID]):
        self.metadata.update_tracking(tracking)

    def build_relation(self, **relation_dict: typing.Dict[str, "Node"]):
        """A convenient function to add relations at once.

        Usage:
            node.build_relation(prev=node_x, next=node_y)
        """
        for relation_name, node in relation_dict.items():
            if relation_name not in {"prev", "next", "step_into", "returned_from"}:
                raise Exception("wrong relation_name: " + relation_name)
            setattr(self, relation_name, node)


class Flow:
    """Class that represents program's execution.

    A flow consists of multiple Calls and Nodes.
    """

    def __init__(self, start: Node, target: Node):
        self.start = start
        self.target = target
        self._get_target_id()

    def _get_target_id(self) -> ID:
        """Gets ID('x') out of cyberbrain.register(x)."""
        register_call_ast = ast.parse(self.target.metadata.code_str.strip())
        assert register_call_ast.body[0].value.func.value.id == "cyberbrain"

        # Finds the target identifier by checking argument passed to register().
        # Assuming argument is a single identifier.
        self.target.metadata.update_tracking(
            ID(register_call_ast.body[0].value.args[0].id)
        )
