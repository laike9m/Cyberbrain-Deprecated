"""Some basic data structures used throughout the project."""

import sys
import typing
from collections import defaultdict


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
Surrounding = typing.NamedTuple(
    "Surrounding", [("start_lineno", int), ("end_lineno", int)]
)

SourceLocation = typing.NamedTuple(
    "SourceLocation", [("filepath", str), ("lineno", int)]
)


class FrameID:

    current_frame_id_ = None

    def __init__(self, parent=None):
        self._parent = parent
        self._children = []
        if parent:
            parent.add_child(self)

    @property
    def parent(self):
        return self._parent

    def is_child_of(self, other):
        return other is self._parent

    def add_child(self, child):
        self._children.append(child)

    def child_index(self):
        assert self.parent is not None
        return self.parent._children.index(self)

    @classmethod
    def create(cls, event: str):
        if cls.current_frame_id_ is None:
            cls.current_frame_id_ = FrameID()

        if event == "line":
            return cls.current_frame_id_
        elif event == "call":
            new_frame_id = FrameID(parent=cls.current_frame_id_)
            cls.current_frame_id_ = new_frame_id
            return new_frame_id.parent  # callsite is in caller frame.
        elif event == "return":
            cls.current_frame_id_ = cls.current_frame_id_.parent
            return cls.current_frame_id_
        else:
            raise AttributeError("event type wrong: ", event)

    def __str__(self):
        """outputs (level, index), frame id whose parent is None is at level 0."""
        level = 0
        curr = self
        while curr.parent is not None:
            level += 1
            curr = curr.parent
        index = 0 if self.parent is None else self.child_index()
        return str((level, index))


class ID(str):
    """A class that represents an identifier.

    TODO: Create a hash function so that ID can be differenciated with string.
    """
