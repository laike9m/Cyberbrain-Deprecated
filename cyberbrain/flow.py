"""Execution flow that represents a program's execution."""

import ast
import itertools
import re
from collections import defaultdict, namedtuple
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union

import astor

from . import utils
from .basis import ID, FrameID, NodeType, _dummy
from .computation import ComputationManager


@dataclass()
class VarAppearance:
    """Variable appears in current frame."""

    id: ID
    value: Any


@dataclass()
class VarModification:
    """Variable value modified in current frame."""

    id: ID
    old_value: Any
    new_value: Any


@dataclass()
class VarSwitch:
    """Variable switches at callsite."""

    arg_id: ID
    param_id: ID
    value: Any


class TrackingMetadata:
    """Class that stores metadata during tracing."""

    def __init__(
        self,
        vars: Dict[ID, Any],
        code_str: str = None,
        code_ast: ast.AST = None,
        param_to_arg: Dict[ID, ID] = None,
        vars_before_return=None,
    ):
        self.code_str = code_str
        self.code_ast = utils.parse_code_str(code_str)
        self.param_to_arg = param_to_arg
        if param_to_arg:
            self.arg_to_param = {}
            for param, args in param_to_arg.items():
                for arg in args:
                    self.arg_to_param[arg] = param

        # It seems that tracking and data should all be flattened, aka they should
        # simply be a mapping of ID -> value. When backtracing, we don't really care
        # about where an identifer is defined in, we only care about whether its value
        # has changed during execution.
        self.tracking: Set[ID] = set()

        self.var_appearances: Set[VarAppearance] = []
        self.var_modifications: Set[VarModification] = []

        # var_switches are set on call node. When some id is switched, it is not counted
        # again in var_appearances.
        self.var_switches: Set[VarSwitch] = []
        self.vars = vars
        self.vars_before_return = vars_before_return
        self.return_value = _dummy

    def set_param_to_arg(self, param_to_arg: Dict[ID, ID]):
        self.param_to_arg = param_to_arg
        self.arg_to_param = {}
        for param, args in param_to_arg.items():
            for arg in args:
                self.arg_to_param[arg] = param

    def get_args(self) -> Set[ID]:
        return set(itertools.chain.from_iterable(self.param_to_arg.values()))

    def add_var_appearances(self, *var_appearances: VarAppearance):
        self.var_appearances.extend(var_appearances)

    def add_var_modifications(self, *var_modifications: VarModification):
        self.var_modifications.extend(var_modifications)

    def add_var_switches(self, *var_switches: VarSwitch):
        self.var_switches.extend(var_switches)

    def sync_tracking_with(self, other: "Node"):
        self.add_tracking(*other.tracking)

    def add_tracking(self, *new_ids: ID):
        """Updates identifiers being tracked.

        Identifiers being tracked must exist in data because we can't track something
        that don't exist in previous nodes.
        """
        for new_id in new_ids:
            if new_id in self.vars:
                self.tracking.add(new_id)


class Node:
    """Basic unit of an execution flow."""

    __slots__ = frozenset(
        ["type", "frame_id", "prev", "next", "step_into", "returned_from", "metadata"]
    )

    def __init__(
        self,
        frame_id: Union[FrameID, Tuple[int, ...]],
        type: Optional[NodeType] = None,
        **kwargs,
    ):
        self.type = type
        if isinstance(frame_id, FrameID):
            self.frame_id = frame_id
        elif isinstance(frame_id, tuple):
            self.frame_id = FrameID(frame_id)
        self.prev = None
        self.next = None
        self.step_into = None
        self.returned_from = None
        self.metadata = TrackingMetadata(**kwargs)

    def __repr__(self):
        return f"<Node {self.code_str}>"

    def __getattr__(self, name):
        return getattr(self.metadata, name)

    def __setattr__(self, name, value):
        if name in self.__slots__:
            super().__setattr__(name, value)
        else:
            setattr(self.metadata, name, value)

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

    def get_and_update_var_changes(
        self, other: "Node"
    ) -> Iterable[Union[VarModification, VarAppearance]]:
        """Gets variable changes and stores them to current node.

        current and next are guaranteed to be in the same frame.
        """
        assert self.frame_id == other.frame_id
        for var_id in other.tracking:
            old_value = self.vars.get(var_id, _dummy)
            new_value = other.vars[var_id]
            if old_value is _dummy:
                var_appearance = VarAppearance(id=var_id, value=new_value)
                self.add_var_appearances(var_appearance)
                yield var_appearance
            elif utils.has_diff(new_value, old_value):
                var_modification = VarModification(var_id, old_value, new_value)
                self.add_var_modifications(var_modification)
                yield var_modification

    def update_var_changes_before_return(self):
        """Compares data with vars_before_return, records changes."""
        if self.vars_before_return is None:
            pass
        for var_id in self.tracking:
            old_value = self.vars.get(var_id, _dummy)
            new_value = self.vars_before_return[var_id]
            if old_value is _dummy:
                var_appearance = VarAppearance(id=var_id, value=new_value)
                self.add_var_appearances(var_appearance)
            elif utils.has_diff(new_value, old_value):
                var_modification = VarModification(var_id, old_value, new_value)
                self.add_var_modifications(var_modification)


class Flow:
    """Class that represents program's execution.

    A flow consists of multiple Calls and Nodes.
    """

    ROOT = object()

    def __init__(self, start: Node, target: Node):
        self.start = start
        self.start.prev = self.ROOT
        self.target = target
        self._update_target_id()

    def _update_target_id(self) -> ID:
        """Gets ID('x') out of cyberbrain.register(x)."""
        register_call_ast = ast.parse(self.target.code_str.strip())
        assert register_call_ast.body[0].value.func.value.id == "cyberbrain"

        # Finds the target identifier by checking argument passed to register().
        # Assuming argument is a single identifier.
        self.target.add_tracking(ID(register_call_ast.body[0].value.args[0].id))


def build_flow(cm: ComputationManager) -> Flow:
    """Builds flow from computations.

    1. Traverse through computations, create node, group nodes by frame id.
    2. For each frame group, flatten nested calls, computes param_to_arg.
    3. Add step_into and returned_from edges.

    call node should pass full code str to node, callsite_ast is only needed to
    generate param_to_arg
    """
    start_node: Node
    target_node: Node
    NodeWithSurrounding = namedtuple("NodeWithSurrounding", ["node", "surrounding"])
    frame_groups: Dict[FrameID, List[NodeWithSurrounding]] = defaultdict(list)

    for frame_id, comps in cm.frame_groups.items():
        for comp in comps:
            if comp.event_type == "line":
                node = Node(
                    type=NodeType.LINE,
                    frame_id=frame_id,
                    vars=comp.vars,
                    code_str=comp.code_str,
                    vars_before_return=comp.vars_before_return,
                )
                if hasattr(comp, "return_value"):
                    node.return_value = comp.return_value
            elif comp.event_type == "call":
                node = Node(
                    type=NodeType.CALL,
                    frame_id=frame_id,
                    vars=comp.vars,
                    code_str=comp.code_str,
                )
            if frame_groups[frame_id]:
                frame_groups[frame_id][-1].node.next = node
                node.prev = frame_groups[frame_id][-1].node
            frame_groups[frame_id].append(NodeWithSurrounding(node, comp.surrounding))
            if comp is cm.target:
                target_node = node

    # Assuming init is called at program start. This may change in the future.
    start_node = frame_groups[(0,)][0].node

    for frame_id, frame in frame_groups.items():
        i = 0  # call index in this frame.
        for _, group in itertools.groupby(frame, lambda x: x.surrounding):
            ast_to_intermediate: Dict[str, str] = {}
            nodes = [g.node for g in group]
            for node in nodes:
                # Replaces nested calls with intermediate vars.
                for inner_call, intermediate in ast_to_intermediate.items():
                    node.code_str = node.code_str.replace(inner_call, intermediate, 1)
                if node.type is NodeType.CALL:
                    # TODO: computes param_to_arg
                    ast_to_intermediate[node.code_str] = f"r{i}_"
                    node.code_str = f"r{i}_ = " + node.code_str
                    node.step_into = frame_groups[node.frame_id + (i,)][0].node
                    node.step_into.prev = node
                    node.returned_from = frame_groups[node.frame_id + (i,)][-1].node
                    # Binds ri_ to next line, becasue it appears during this line.
                    node.next.vars[f"r{i}_"] = node.returned_from.return_value
                    i += 1
                node.code_ast = utils.parse_code_str(node.code_str)

            if len(node.code_ast.body) != 1:
                continue
            stmt = node.code_ast.body[0]

            if (
                isinstance(stmt, ast.Expr)
                and isinstance(stmt.value, ast.Name)
                and re.match(r"r[\d]+_", stmt.value.id)
                and node.prev
            ):
                # Last line is "r0_", removes this node.
                # This happens when "f()" was replaced by "r0_".
                assert node.type is NodeType.LINE
                prev = node.prev
                assert prev.type is NodeType.CALL and prev.code_str.startswith(
                    f"{stmt.value.id}"
                )
                prev.next = node.next
                if node.next:
                    node.next.prev = prev
                prev.code_str = prev.code_str.split("=", 1)[1].lstrip()
                prev.code_ast = utils.parse_code_str(node.code_str)
            elif (
                isinstance(stmt, ast.Assign)
                and isinstance(stmt.value, ast.Name)
                and re.match(r"r[\d]+_", stmt.value.id)
                and node.prev
            ):
                # Current node represents "a = r0_", previous node is "r0_ = f()"
                # Changes previous to 'a = f()', discards current node.
                # We don't need to modify frame_groups, it's not used in tracing.
                value = stmt.value
                prev = node.prev
                assert prev.type is NodeType.CALL and prev.code_str.startswith(
                    f"{value.id} ="
                )
                prev.next = node.next
                if node.next:
                    node.next.prev = prev
                prev.code_ast.body[0].targets = stmt.targets
                prev.code_str = astor.to_source(prev.code_ast).strip()

    return Flow(start_node, target_node)
