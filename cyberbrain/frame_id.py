from collections import defaultdict
import sys


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

    @classmethod
    def create(cls, event: str):
        if cls.current_frame_id_ is None:
            cls.current_frame_id_ = FrameID()

        if event == 'line':
            return cls.current_frame_id_
        elif event == 'call':
            new_frame_id = FrameID(parent=cls.current_frame_id_)
            cls.current_frame_id_ = new_frame_id
            return new_frame_id
        elif event == 'return':
            cls.current_frame_id_ = cls.current_frame_id_.parent
            return cls.current_frame_id_
        else:
            raise AttributeError('event type wrong: ', event)

# def __str__(self):
#     output = ''
#     for child in self._children:
#         assert self is not self._parent
#         assert self is not child
#         assert self._parent is not child
#         output += '\n\tchild: %s' % repr(child)
#     return output
# def __str__(self):
#     output = ''
#     for child in self._children:
#         assert self is not self._parent
#         assert self is not child
#         assert self._parent is not child
#         output += '\n\tchild: %s' % repr(child)
#     return output
