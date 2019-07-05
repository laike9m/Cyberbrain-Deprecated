"""Data structures for recording program execution."""

import abc
import ast
import inspect
from pathlib import PurePath
from typing import Optional

from . import caller_ast, utils
from .frame_id import FrameID
from .utils import Surrounding, SourceLocation


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
        arg_vlues: inspect.ArgInfo,
        callee_source_location: SourceLocation,
        data,
        event_type: str,
        frame_id: FrameID,
    ):
        self.call_site_ast = call_site_ast
        self.call_site_source_location = call_site_source_location
        self.arg_vlues = arg_vlues
        self.callee_source_location = callee_source_location
        self.data = data
        self.event_type = event_type
        self.frame_id = frame_id

    @property
    def code_str(self):
        # TODO: return all
        return ast.dump(self.call_site_ast).rstrip()

    @property
    def source_location(self):
        return self.callee_source_location

    @staticmethod
    def create(frame):
        caller_frame = frame.f_back
        return Call(
            call_site_ast=caller_ast.get_cache_callsite(
                caller_frame.f_code, caller_frame.f_lasti
            ),
            call_site_source_location=SourceLocation(
                filepath=caller_frame.f_code.co_filename, lineno=caller_frame.f_lineno
            ),
            arg_vlues=inspect.getargvalues(frame),
            callee_source_location=SourceLocation(
                filepath=frame.f_code.co_filename, lineno=frame.f_lineno
            ),
            data=utils.traverse_frames(caller_frame),
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

    def add_computation(self, event_type, frame):
        if event_type == "line":
            code_str, surrounding = utils.get_code_str_and_surrounding(frame)
            frame_id = FrameID.create(event_type)
            # For multiline statement, skips if the logical line has been added.
            if (
                self.computations
                and self.computations[-1].event_type == "line"
                and self.computations[-1].frame_id == frame_id
                and self.computations[-1].surrounding == surrounding
            ):
                return
            # Records location, computation, data
            self._computations.append(
                Line(
                    code_str=code_str.rstrip(),
                    filepath=frame.f_code.co_filename,
                    lineno=frame.f_lineno,
                    data=utils.traverse_frames(frame),
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
                and self.computations[-1].event_type == "line"
                and computation.frame_id.is_child_of(self.last_computation.frame_id)
            ):
                self._computations[-1] = computation
            else:
                # raise Exception()
                self._computations.append(computation)


computation_manager = _ComputationManager()
