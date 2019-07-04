"""Data structures for recording program execution."""

import inspect
from pathlib import PurePath
from typing import Optional, Tuple

from .frame_id import FrameID


class Computation:
    """Base class to represent a computation unit of the program.
    """

    def __init__(
        self,
        *,
        filepath: str,
        lineno: int,
        data,
        frame_id: FrameID,
        event: str,
        last_i: int,
        surrounding: Optional[
            Tuple[int, int]
        ] = None  # See utils.get_code_str_and_surrounding for its meaning.
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
    """Class that represents a logical line without entering into a new call.
    """

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
