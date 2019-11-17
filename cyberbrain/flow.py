"""Execution flow that represents a program's execution."""

import ast
import inspect
import itertools
import re
from collections import defaultdict, namedtuple
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union

import astor

from . import callsite, utils
from .basis import ID, FrameID, NodeType, SourceLocation, _dummy
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
        vars_before_return=None,
        source_location: SourceLocation = None,
    ):
        self.vars = vars
        self.source_location = source_location
        self.code_str = code_str
        self.code_ast = utils.parse_code_str(code_str)

        # It seems that tracking and data should all be flattened, aka they should    sdss
        # simply be a mapping of ID -> value. When backtracing, we don't really care
        # about where an identifer is defined in, we only care about whether its value
        # has changed during execution.
        self.tracking: Set[ID] = set()

        self.var_appearances: Set[VarAppearance] = []
        self.var_modifications: Set[VarModification] = []

        # var_switches are set on call node. When some id is switched, it is not counted
        # again in var_appearances.
        self.var_switches: Set[VarSwitch] = []
        self.vars_before_return = vars_before_return
        self.return_value = _dummy
        self.is_relevant_return = False

    def set_param_arg_mapping(self, arg_values: inspect.ArgInfo):
        param_to_arg = callsite.get_param_to_arg(
            self.code_ast.body[0].value, arg_values
        )
        self.param_values = arg_values.locals  # Maps param name to its value.
        self.param_to_arg = param_to_arg
        self.arg_to_param = {}
        for param, args in param_to_arg.items():
            for arg in args:
                self.arg_to_param[arg] = param

    def get_args(self) -> Set[ID]:
        # pytype: disable=bad-return-type
        return set(itertools.chain.from_iterable(self.param_to_arg.values()))
        # pytype: enable=bad-return-type

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
        [
            "type",
            "frame_id",
            "prev",
            "next",
            "step_into",
            "returned_from",
            "metadata",
            "is_target",
        ]
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
        self.prev: Optional[Node] = None
        self.next: Optional[Node] = None
        self.step_into: Optional[Node] = None
        self.returned_from: Optional[Node] = None
        self.metadata = TrackingMetadata(**kwargs)
        self.is_target = False

    def __repr__(self):
        return f"<Node {self.code_str}>"

    def __getattr__(self, name):
        return getattr(self.metadata, name)

    def __setattr__(self, name, value):
        if name in self.__slots__:
            super().__setattr__(name, value)
        else:
            setattr(self.metadata, name, value)

    @property
    def shown_in_output(self) -> bool:
        """Whether this node should be shown in output."""
        # TODO: Only inserts call node if there are var changes inside the call.
        return (
            self.metadata.is_relevant_return
            or self.metadata.var_appearances
            or self.metadata.var_modifications
            or self.is_target
            or self.is_callsite
        )

    @property
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

        Current and next must live in the same frame.
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
        self.target.is_target = True
        self._update_target_id()
        self._cursor = None  # Current position in iteration.

    def _update_target_id(self):
        """Gets ID('x') out of cyberbrain.register(x)."""
        register_call_ast = ast.parse(self.target.code_str.strip())
        assert register_call_ast.body[0].value.func.value.id == "cyberbrain"

        # Finds the target identifier by checking argument passed to register().
        # Assuming argument is a single identifier.
        self.target.add_tracking(ID(register_call_ast.body[0].value.args[0].id))

    def __iter__(self):
        yield from self._trace_frame(self.start)

    def _trace_frame(self, current: Node):
        """Iterates and yields node in the frame where node is at."""
        while current is not None:
            self._cursor = current
            if current.is_callsite:
                yield from self._trace_frame(current.step_into)
            yield current
            current = current.next


NodeInfo = namedtuple("NodeInfo", ["node", "surrounding", "arg_values"])


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
    frame_groups: Dict[FrameID, List[NodeInfo]] = defaultdict(list)

    for frame_id, comps in cm.frame_groups.items():
        for comp in comps:
            if comp.event_type == "line":
                node = Node(
                    type=NodeType.LINE,
                    frame_id=frame_id,
                    vars=comp.vars,
                    code_str=comp.code_str,
                    vars_before_return=comp.vars_before_return,
                    source_location=comp.source_location,
                )
                if hasattr(comp, "return_value"):
                    node.return_value = comp.return_value
            elif comp.event_type == "call":
                node = Node(
                    type=NodeType.CALL,
                    frame_id=frame_id,
                    vars=comp.vars,
                    code_str=comp.code_str,
                    source_location=comp.source_location,
                )
            if frame_groups[frame_id]:
                frame_groups[frame_id][-1].node.next = node
                node.prev = frame_groups[frame_id][-1].node
            frame_groups[frame_id].append(
                NodeInfo(node, comp.surrounding, getattr(comp, "arg_values", None))
            )
            if comp is cm.target:
                target_node = node

    replace_calls(frame_groups)

    # Assuming init is called at program start. This may change in the future.
    start_node = frame_groups[(0,)][0].node

    return Flow(start_node, target_node)


def replace_calls(frame_groups: Dict[FrameID, List[NodeInfo]]):
    """Replaces call exprs with intermediate variables."""
    for _, frame in frame_groups.items():
        i = 0  # call index in this frame.
        for _, group in itertools.groupby(frame, lambda x: x.surrounding):
            ast_to_intermediate: Dict[str, str] = {}
            intermediate_vars = {}  # Mapping of intermediate vars and their values.
            for node, _, arg_values in group:
                # ri_ appeared before should be captured in node.vars.
                node.vars.update(intermediate_vars)
                # Replaces nested calls with intermediate vars.
                for inner_call, intermediate in ast_to_intermediate.items():
                    node.code_str = node.code_str.replace(inner_call, intermediate, 1)
                if node.type is NodeType.CALL:
                    ast_to_intermediate[node.code_str] = f"r{i}_"
                    node.code_str = f"r{i}_ = " + node.code_str
                    node.step_into = frame_groups[node.frame_id + (i,)][0].node
                    node.step_into.prev = node
                    node.returned_from = frame_groups[node.frame_id + (i,)][-1].node
                    intermediate_vars[f"r{i}_"] = node.returned_from.return_value
                    i += 1
                node.code_ast = utils.parse_code_str(node.code_str)
                if node.type is NodeType.CALL:
                    assert arg_values, "call node should have arg_values."
                    node.set_param_arg_mapping(arg_values)

            # Deals with some special cases.
            assert len(node.code_ast.body) == 1
            stmt = node.code_ast.body[0]

            # Checks if LHS is ri_ and ri_ only, e.g. r1_ = f(1, 2)
            lhs_is_ri = lambda stmt: (
                isinstance(stmt.value, ast.Name) and re.match(r"r[\d]+_", stmt.value.id)
            )

            if isinstance(stmt, ast.Expr) and lhs_is_ri(stmt):
                # Current node is "r0_", previous node is "r0_ = f()".
                # This happens when the whole line is just "f()".
                # Solution: removes current node, restores previous node to "f()".
                assert node.type is NodeType.LINE
                prev = node.prev
                assert (
                    prev
                    and prev.type is NodeType.CALL
                    and prev.code_str.startswith(f"{stmt.value.id}")
                )
                prev.next = node.next
                if node.next:
                    node.next.prev = prev
                prev.code_str = prev.code_str.split("=", 1)[1].lstrip()
                prev.code_ast = utils.parse_code_str(node.code_str)
            elif isinstance(stmt, ast.Assign) and lhs_is_ri(stmt):
                # Current node represents "a = r0_", previous node is "r0_ = f()"
                # Solution: changes previous to 'a = f()', discards current node.
                # We don't need to modify frame_groups, it's not used in tracing.
                value = stmt.value
                prev = node.prev
                assert (
                    prev
                    and prev.type is NodeType.CALL
                    and prev.code_str.startswith(f"{value.id} =")
                )
                prev.next = node.next
                if node.next:
                    node.next.prev = prev
                prev.code_ast.body[0].targets = stmt.targets
                prev.code_str = astor.to_source(prev.code_ast).strip()
