"""Data structures for recording program execution."""

import abc
import inspect
from pathlib import PurePath
from typing import Optional

from . import caller_ast, utils
from .frame_id import FrameID
from .utils import Surrounding


class Computation(metaclass=abc.ABCMeta):
    """Base class to represent a computation unit of the program."""

    def to_dict(self):
        """Serializes attrs to dict."""
        return {
            "filepath": PurePath(self.filepath).name,
            "lineno": self.lineno,
            "code_str": self.code_str,
            "frame_id": str(self.frame_id),
            "event": self.event_type,
            "last_i": self.last_i,
        }

    def __str__(self):
        return str(self.to_dict())


class Line(Computation):
    """Class that represents a logical line without entering into a new call."""

    def __init__(
        self,
        *,
        code_str: str,
        filepath: str,
        lineno: int,
        data,
        frame_id: FrameID,
        event_type: str,
        last_i: int,
        surrounding: Optional[Surrounding],
    ):
        self.code_str = code_str
        self.filepath = filepath
        self.lineno = lineno
        self.data = data
        self.event_type = event_type
        self.frame_id = frame_id
        self.last_i = last_i
        self.surrounding = surrounding


class Call(Computation):
    """Class that represents a call site."""

    def __init__(
        self,
        *,
        call_site: str,
        arg_vlues: inspect.ArgInfo,
        filepath: str,
        lineno: int,
        data,
        event_type: str,
        frame_id: FrameID,
        last_i: int,
    ):
        self.call_site = call_site
        self.arg_vlues = arg_vlues
        self.filepath = filepath
        self.lineno = lineno
        self.data = data
        self.event_type = event_type
        self.frame_id = frame_id
        self.last_i = last_i

    @property
    def code_str(self):
        # TODO: return all
        return self.call_site

    @staticmethod
    def create(frame, code_str):
        return Call(
            call_site=code_str.rstrip(),
            arg_vlues=inspect.getargvalues(frame),
            filepath=frame.f_code.co_filename,
            lineno=frame.f_lineno,
            data=utils.traverse_frames(frame),
            event_type="call",
            frame_id=FrameID.create("call"),
            last_i=frame.f_lasti,
        )


class _ComputationManager:
    """Class that stores and manages all computations."""

    def __init__(self):
        self._computations = []

    @property
    def computations(self):
        return self._computations

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
                    last_i=frame.f_lasti,
                    surrounding=surrounding,
                )
            )
        elif event_type == "call":
            f = frame.f_back
            code_str = caller_ast.get_cache_callsite_code_str(f.f_code, f.f_lasti)
            computation = Call.create(frame, code_str)
            # When entering a new call, replaces previous line(aka func caller) with a
            # call computation.
            if (
                self._computations
                and self.computations[-1].event_type == "line"
                and computation.frame_id.is_child_of(self.last_computation().frame_id)
            ):
                self._computations[-1] = computation
            else:
                self._computations.append(computation)


computation_manager = _ComputationManager()
