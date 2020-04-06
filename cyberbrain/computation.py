"""Vars structures for recording program execution."""

import abc
import ast
import inspect
from collections import defaultdict
from pathlib import PurePath
from typing import Dict, List, Union

import black
import executing
from pympler import asizeof

from . import utils
from .basis import FrameID, SourceLocation, Surrounding
from .vars import Vars


class Computation(metaclass=abc.ABCMeta):
    """Base class to represent a computation unit of the program."""

    code_str: str
    event_type: str
    source_location: SourceLocation
    VARS_ATTR_NAME = "vars"
    vars_total_size = 0

    def __new__(cls, **kwargs):
        """Automatically sums up the size of vars."""
        assert cls.VARS_ATTR_NAME in kwargs
        Computation.vars_total_size += asizeof.asizeof(kwargs[cls.VARS_ATTR_NAME])
        return super().__new__(cls)

    @abc.abstractmethod
    def to_dict(self):
        """Serializes attrs to dict. Subclasses must override this method."""
        surrounding = self.source_location.surrounding
        if surrounding.start_lineno == surrounding.end_lineno:
            lineno_str = surrounding.start_lineno
        else:
            lineno_str = f"{surrounding.start_lineno} ~ {surrounding.end_lineno}"
        return {
            "event": self.event_type,
            "filepath": PurePath(self.source_location.filepath).name,
            "lineno": lineno_str,
            "code_str": self.code_str,
        }

    def __repr__(self):
        return self.code_str

    def __str__(self):
        return str(self.to_dict())


class Line(Computation):
    """Class that represents a logical line without entering into a new call."""

    def __init__(
        self,
        *,
        code_str: str,
        source_location: SourceLocation,
        vars: Vars,
        frame_id: FrameID,
        event_type: str,
        surrounding: Surrounding,
    ):
        self.code_str = code_str
        try:
            self.code_str = black.format_str(
                self.code_str, mode=black.FileMode()
            ).strip()
        except black.InvalidInput:
            pass
        self.source_location = source_location
        self.vars = vars
        self.event_type = event_type
        self.frame_id = frame_id
        self.surrounding = surrounding
        self.vars_before_return = None

    def to_dict(self):
        return {**super().to_dict(), "frame_id": str(self.frame_id)}


class Call(Computation):
    """Class that represents a call site."""

    def __init__(
        self,
        *,
        callsite_ast: ast.AST,
        source_location: SourceLocation,
        arg_values: inspect.ArgInfo,
        func_name: str,
        vars: Vars,
        event_type: str,
        frame_id: FrameID,
        callee_frame_id: FrameID,
        surrounding: Surrounding,
    ):
        self.callsite_ast = callsite_ast
        self.source_location = source_location
        self.arg_values = arg_values
        self.func_name = func_name
        self.vars = vars
        self.event_type = event_type
        self.frame_id = frame_id
        self.callee_frame_id = callee_frame_id
        self.code_str = utils.ast_to_str(self.callsite_ast)
        self.vars_before_return = None
        self.surrounding = surrounding

    def to_dict(self):
        return {
            **super().to_dict(),
            "caller_frame_id": str(self.frame_id),
            "callee_frame_id": str(self.callee_frame_id),
        }

    @staticmethod
    def create(frame):
        caller_frame = frame.f_back
        _, surrounding = utils.get_code_str_and_surrounding(caller_frame)
        callsite_ast = executing.Source.executing(caller_frame).node
        # If it's not ast.Call, like ast.ListComp, ignore for now.
        if not isinstance(callsite_ast, ast.Call):
            return None
        frame_id = FrameID.create("call")
        frame_id.co_name = caller_frame.f_code.co_name
        frame_id.frame_belonging_type = utils.get_frame_belonging_type(frame)
        print(f"{frame} frame_belonging_type: {frame_id.frame_belonging_type}")
        return Call(
            callsite_ast=callsite_ast,
            source_location=SourceLocation(
                filepath=caller_frame.f_code.co_filename, surrounding=surrounding
            ),
            arg_values=inspect.getargvalues(frame),
            func_name=frame.f_code.co_name,
            vars=Vars(caller_frame),
            event_type="call",
            frame_id=frame_id,
            callee_frame_id=FrameID.current(),
            surrounding=surrounding,
        )


class ComputationManager:
    """Class that stores and manages all computations."""

    REGISTER_CALL = "cyberbrain.register"

    def __init__(self):
        # TODO: Uses frame info(a wrapper around FrameID) to organize comps, instead of FrameID.
        # Frame info should be reused in Flow. Don't store frame_id in comp.
        self.frame_groups: Dict[FrameID, List[Union[Line, Call]]] = defaultdict(list)
        self.target = None

    def add_computation(self, event_type, frame, arg) -> bool:
        """Adds a computation to manager.

        Returns Whether a new computation has been created and added.
        """
        assert event_type in {"line", "call", "return"}
        if event_type == "line":
            code_str, surrounding = utils.get_code_str_and_surrounding(frame)
            frame_id = FrameID.create(event_type)
            frame_id.co_name = frame.f_code.co_name
            frame_id.frame_belonging_type = utils.get_frame_belonging_type(frame)
            # Skips if the same logical line has been added.
            if (
                self.frame_groups[frame_id]
                and self.frame_groups[frame_id][-1].surrounding == surrounding
            ):
                return False
            comp = Line(
                code_str=code_str.rsplit("#", 1)[0].strip(),  # Removes comment.
                source_location=SourceLocation(
                    filepath=frame.f_code.co_filename, surrounding=surrounding
                ),
                vars=Vars(frame),
                event_type=event_type,
                frame_id=frame_id,
                surrounding=surrounding,
            )
            if comp.code_str.startswith(self.REGISTER_CALL):
                self.target = comp
            self.frame_groups[frame_id].append(comp)
            return True

        if event_type == "call":
            # In Python 3.8, for multiline statement, after the events triggered by each
            # line, there will be an extra line event triggered by the first line. This
            # will cause the lineno for call comp to be different in different Python
            # verions.
            computation = Call.create(frame)
            # Don't trace cyberbrain.register.
            if not computation or computation.code_str.startswith(self.REGISTER_CALL):
                return False
            frame_id = computation.frame_id
            # When entering a new call, replaces previous line(aka caller) with a
            # call computation.
            if (
                self.frame_groups[frame_id]
                and self.frame_groups[frame_id][-1].event_type == "line"
            ):
                # Always keeps Line computation at the end.
                self.frame_groups[frame_id].insert(
                    len(self.frame_groups[frame_id]) - 1, computation
                )
            else:
                self.frame_groups[frame_id].append(computation)

            return True

        # event is "return".
        frame_id = FrameID.create(event_type)
        assert self.frame_groups[frame_id][-1].event_type == "line"
        self.frame_groups[frame_id][-1].return_value = arg
        self.frame_groups[frame_id][-1].vars_before_return = Vars(frame)
        return True


computation_manager = ComputationManager()
