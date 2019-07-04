import sys
from collections import defaultdict

from crayons import blue, green, red, yellow


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
            return new_frame_id
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
