"""Data structures for recording program execution."""

import abc
import ast
import inspect
from pathlib import PurePath
from typing import Optional

from . import callsite, utils
from .frame_id import FrameID
from .utils import SourceLocation, Surrounding
from .data import DataContainer


class Computation(metaclass=abc.ABCMeta):
    """Base class to represent a computation unit of the program."""

    def to_dict(self):
        """Serializes attrs to dict."""
        return {
            "filepath": PurePath(self.source_location.filepath).name,
            "lineno": self.source_location.lineno,
            "code_str": self.code_str,
            "frame_id": str(self.frame_id),
            "event": self.event_type,
        }

    def __str__(self):
        return str(self.to_dict())


class Line(Computation):
    """Class that represents a logical line without entering into a new call."""

    def __init__(
        self,
        *,
        code_str: ast.AST,
        filepath: str,
        lineno: int,
        data,
        frame_id: FrameID,
        event_type: str,
        surrounding: Optional[Surrounding],
    ):
        self.code_str = code_str
        self.source_location = SourceLocation(filepath=filepath, lineno=lineno)
        self.data = data
        self.event_type = event_type
        self.frame_id = frame_id
        self.surrounding = surrounding


class Call(Computation):
    """Class that represents a call site."""

    def __init__(
        self,
        *,
        call_site_ast: ast.AST,
        call_site_source_location: SourceLocation,
        arg_values: inspect.ArgInfo,
        callee_source_location: SourceLocation,
        data,
        event_type: str,
        frame_id: FrameID,
    ):
        self.call_site_ast = call_site_ast
        self.call_site_source_location = call_site_source_location
        self.arg_values = arg_values
        self.callee_source_location = callee_source_location
        self.data = data
        self.event_type = event_type
        self.frame_id = frame_id
        self.code_str = ast.dump(self.call_site_ast).rstrip()

    @property
    def source_location(self):
        return self.callee_source_location

    @staticmethod
    def create(frame):
        caller_frame = frame.f_back
        call_site_ast, outer_call_site_ast = callsite.get_callsite_ast(
            caller_frame.f_code, caller_frame.f_lasti
        )
        return Call(
            call_site_ast=call_site_ast,
            call_site_source_location=SourceLocation(
                filepath=caller_frame.f_code.co_filename, lineno=caller_frame.f_lineno
            ),
            arg_values=inspect.getargvalues(frame),
            callee_source_location=SourceLocation(
                filepath=frame.f_code.co_filename, lineno=frame.f_lineno
            ),
            data=DataContainer(caller_frame),
            event_type="call",
            frame_id=FrameID.create("call"),
        )


class _ComputationManager:
    """Class that stores and manages all computations."""

    def __init__(self):
        self._computations = []

    @property
    def computations(self):
        return self._computations

    @property
    def last_computation(self):
        return self._computations[-1]

    @last_computation.setter
    def last_computation(self, c: Computation):
        self._computations[-1] = c

    def add_computation(self, event_type, frame):
        if event_type == "line":
            code_str, surrounding = utils.get_code_str_and_surrounding(frame)
            frame_id = FrameID.create(event_type)
            # For multiline statement, skips if the logical line has been added.
            if (
                self.computations
                and self.last_computation.event_type == "line"
                and self.last_computation.frame_id == frame_id
                and self.last_computation.surrounding == surrounding
            ):
                return
            # Records location, computation, data
            self._computations.append(
                Line(
                    code_str=code_str.rstrip(),
                    filepath=frame.f_code.co_filename,
                    lineno=frame.f_lineno,
                    data=DataContainer(frame),
                    event_type=event_type,
                    frame_id=frame_id,
                    surrounding=surrounding,
                )
            )
        elif event_type == "call":
            computation = Call.create(frame)
            # When entering a new call, replaces previous line(aka func caller) with a
            # call computation.
            if (
                self._computations
                and self.last_computation.event_type == "line"
                and computation.frame_id.is_child_of(self.last_computation.frame_id)
            ):
                self.last_computation = computation
            else:
                # raise Exception()
                self._computations.append(computation)


computation_manager = _ComputationManager()
