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

    def __init__(
        self,
        *,
        filepath: str,
        lineno: int,
        data,
        frame_id: FrameID,
        event: str,
        last_i: int,
        surrounding: Optional[Surrounding] = None
    ):
        self.filepath = filepath
        self.lineno = lineno
        self.data = data
        self.frame_id = frame_id
        self.event = event
        self.last_i = last_i
        self.surrounding = surrounding

    def to_dict(self):
        """Serializes attrs to dict."""
        return {
            "filepath": PurePath(self.filepath).name,
            "lineno": self.lineno,
            "code_str": self.code_str,
            "frame_id": str(self.frame_id),
            "event": self.event,
            "last_i": self.last_i,
            "surrounding": str(self.surrounding),
        }

    def __str__(self):
        return str(self.to_dict())


class Line(Computation):
    """Class that represents a logical line without entering into a new call."""

    def __init__(self, *, code_str: str, **kwargs):
        self._code_str = code_str
        super().__init__(**kwargs)

    @property
    def code_str(self):
        return self._code_str


class Call(Computation):
    """Class that represents a call site."""

    def __init__(self, *, caller_str: str, arg_vlues: inspect.ArgInfo, **kwargs):
        self._caller_str = caller_str
        self._arg_vlues = arg_vlues
        super().__init__(**kwargs)

    @property
    def code_str(self):
        # TODO: return all
        return self._caller_str


class _ComputationManager:
    """Class that stores and manages all computations."""

    def __init__(self):
        self._computations = []

    @property
    def computations(self):
        return self._computations

    def add_computation(self, type, frame):
        if type == "line":
            code_str, surrounding = utils.get_code_str_and_surrounding(frame)
            frame_id = FrameID.create(type)
            # For multiline statement, skips if the logical line has been added.
            if (
                self.computations
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
                    event=type,
                    frame_id=frame_id,
                    last_i=frame.f_lasti,
                    surrounding=surrounding,
                )
            )
        elif type == "call":
            f = frame.f_back
            code_str = caller_ast.get_cache_callsite_code_str(f.f_code, f.f_lasti)
            computation = Call(
                caller_str=code_str.rstrip(),
                arg_vlues=inspect.getargvalues(frame),
                filepath=frame.f_code.co_filename,
                lineno=frame.f_lineno,
                data=utils.traverse_frames(frame),
                event=type,
                frame_id=FrameID.create(type),
                last_i=frame.f_lasti,
            )
            # When entering a new call, replaces previous line(aka func caller) with a
            # call computation.
            if (
                self._computations
                and self.computations[-1].event == "line"
                and computation.frame_id.is_child_of(self.computations[-1].frame_id)
            ):
                self._computations[-1] = computation
            else:
                self._computations.append(computation)


computation_manager = _ComputationManager()
