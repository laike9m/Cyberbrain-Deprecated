"""Some basic data structures used throughout the project."""

from collections import defaultdict
from enum import Enum
from typing import Dict, NamedTuple, Tuple, Union

# "surrounding" is a 2-element tuple (start_lineno, end_lineno), representing a
# logical line. Line number is frame-wise.
#
# For single-line statement, start_lineno = end_lineno, and is the line number of the
# physical line returned by get_lineno_from_lnotab.
#
# For multiline statement, start_lineno is the line number of the first physical line,
# end_lineno is the last. Lines from start_lineno to end_lineno -1 should end with
# token.NL(or tokenize.NL before 3.7), line end_lineno should end with token.NEWLINE.
#
# Example:
# 0    a = true
# 1    a = true
# 2    b = {
# 3        'foo': 'bar'
# 4    }
# 5    c = false
#
# For the assignment of b, start_lineno = 2, end_lineno = 4
Surrounding = NamedTuple("Surrounding", [("start_lineno", int), ("end_lineno", int)])

SourceLocation = NamedTuple("SourceLocation", [("filepath", str), ("lineno", int)])

_dummy = object()


class NodeType(Enum):
    """Just node types."""

    LINE = 1
    CALL = 2


class FrameID:
    """Class that represents a frame.

    Basically, a frame id is just a tuple, where each element represents the frame index
    within the same parent frame. For example, consider this snippet:

    def f(): g()

    def g(): pass

    f()
    f()

    Assuming the frame id for global frame is (0,). We called f two times with two
    frames (0, 0) and (0, 1). f calls g, which also generates two frames (0, 0, 0) and
    (0, 1, 0). By comparing prefixes, it's easy to know whether one frame is the parent
    frame of the other.

    We also maintain the frame id of current code location. New frame ids are generated
    based on event type and current frame id.

    TODO: record function name.
    """

    current_ = (0,)

    # Mapping from parent frame id to max child frame index.
    child_index: Dict[Tuple, int] = defaultdict(int)

    def __init__(self, frame_id_tuple: Tuple[int, ...], co_name: str = ""):
        self._frame_id_tuple = frame_id_tuple
        self.co_name = co_name

    def __eq__(self, other: Union["FrameID", Tuple[int, ...]]):
        if isinstance(other, FrameID):
            return self._frame_id_tuple == other._frame_id_tuple
        elif isinstance(other, Tuple):
            return self._frame_id_tuple == other

    def __hash__(self):
        return hash(self._frame_id_tuple)

    def __add__(self, other: Tuple):
        return FrameID(self._frame_id_tuple + other)

    @property
    def tuple(self):
        return self._frame_id_tuple

    @classmethod
    def current(cls):
        return FrameID(cls.current_)

    @property
    def parent(self):
        return FrameID(self._frame_id_tuple[:-1])

    def is_child_of(self, other):
        return other == self._frame_id_tuple

    def is_parent_of(self, other):
        return self == other._frame_id_tuple

    @classmethod
    def create(cls, event: str):
        if event == "line":
            return cls.current()
        elif event == "call":
            frame_id = cls.current()
            cls.current_ = cls.current_ + (cls.child_index[cls.current_],)
            return frame_id  # callsite is in caller frame.
        elif event == "return":
            call_frame = cls.current()
            cls.current_ = cls.current_[:-1]
            # After exiting call frame, increments call frame's child index.
            cls.child_index[cls.current_] += 1
            return call_frame
        else:
            raise AttributeError("event type wrong: ", event)

    def __str__(self):
        """Prints the tuple representation."""
        return f"{str(self._frame_id_tuple)} {self.co_name}"


class ID(str):
    """A class that represents an identifier.

    There's no need to save frame info, because at a ceratain time, a computation or
    node only sees one value for one identifier, and we can omit others.
    """
