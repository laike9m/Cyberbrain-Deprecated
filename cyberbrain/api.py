"""Cyberbrain API."""

import sys

from crayons import blue, red

from . import utils
from .computation import computation_manager
from .debugging import dump_computations
from .frame_id import FrameID


# class NameVisitor(ast.NodeVisitor):
#     def __init__(self):
#         self.names = set()
#         super().__init__()
#
#     def visit_Name(self, node):
#         self.names.add(node.id)
#         self.generic_visit(node)


def global_tracer(frame, event_type, arg):
    """Global trace function."""
    if utils.should_exclude(frame.f_code.co_filename):
        return
    print("\nthis is global: ", frame, frame.f_code.co_filename, red(event_type), arg)

    if event_type == "call":
        computation_manager.add_computation(event_type, frame)
    return local_tracer


def local_tracer(frame, event_type, arg):
    """Local trace function."""
    if utils.should_exclude(frame.f_code.co_filename):
        return
    print("\nthis is local: ", frame, blue(event_type), arg)

    if event_type == "line":
        computation_manager.add_computation(event_type, frame)
    elif event_type == "return":
        # At this point we don't need to record return but needs to update frame id.
        FrameID.create(event_type)


global_frame = None


def init():
    """Inits tracing."""
    global global_frame

    global_frame = sys._getframe(1)
    print("set tracer for frame: ", global_frame, global_frame.f_lasti)
    sys.settrace(global_tracer)
    global_frame.f_trace = local_tracer


def register(target=None):
    """Receives target variable and stops recording computation.

    If target is None, it means it is only called to terminate tracing and dump data.
    """
    sys.settrace(None)
    global_frame.f_trace = None
    dump_computations(computation_manager.computations)


#
# # prints final trace output
# def printer(lineno, frame_vars, ast_node, names):
#     print("code: ", lines[lineno - 1], end="")
#     print("vars: ")
#     for name in names:
#         # need to check existence because line event fires before line is executed.
#         if name in frame_vars[0]:
#             print(name, frame_vars[0][name])
#
#
# # A set to record
# target_identifier = {"y"}
# # Finally, backtrace the records of each line
# for computation in reversed(computations):
#     visitor = NameVisitor()
#     visitor.visit(computation.ast)
#     if target_identifier & visitor.names:
#         printer(computation.lineno, computation.data, computation.ast, visitor.names)
#         target_identifier |= visitor.names
