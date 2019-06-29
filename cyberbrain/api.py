import sys
import typing
import os
import ast
import io
import inspect
import dis
import copy
from pprint import pprint
from collections import namedtuple, defaultdict
from pathlib import PurePath

import uncompyle6
from crayons import red, blue, green, yellow

from . import caller_ast
from . import utils
from .frame_id import FrameID
from .debugging import dump_computations


computations = []
# 每个 line event，从当前 frame 向上遍历到 global frame，记下所有 frame 的 locals
class Computation:
    def __init__(
        self,
        *,
        filepath,
        lineno,
        data,
        code_str,
        frame_id,
        event,
        last_i,
        surrounding=None  # See utils.get_code_str_and_surrounding for its meaning.
    ):
        self.filepath = filepath
        self.lineno = lineno
        self.data = data
        self.code_str = code_str
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


class NameVisitor(ast.NodeVisitor):
    def __init__(self):
        self.names = set()
        super().__init__()

    def visit_Name(self, node):
        self.names.add(node.id)
        self.generic_visit(node)


# Records variables from bottom to top
def traverse_frames(frame):
    frame_vars = defaultdict(dict)  # [frame_level_up][var_name]
    frame_level_up = 0
    while frame is not None:
        for var_name, var_value in frame.f_locals.items():
            try:
                frame_vars[frame_level_up][var_name] = copy.deepcopy(var_value)
            except TypeError:
                try:
                    frame_vars[frame_level_up][var_name] = copy.copy(var_value)
                except TypeError:
                    frame_vars[frame_level_up][var_name] = var_value
        frame = frame.f_back
        frame_level_up += 1
    return frame_vars


def global_tracer(frame, event, arg):
    """
    Needs to exclude code from Python stdlib, and ideally, 3rd party code as well.
    """
    if utils.should_exclude(frame.f_code.co_filename):
        return
    print("\nthis is global: ", frame, frame.f_code.co_filename, red(event), arg)
    # TODO: get function definition line. like def x()
    if event == "call":
        f = sys._getframe(2)

        code_str = caller_ast.get_cache_callsite_code_str(f.f_code, f.f_lasti)
        computation = Computation(
            filepath=frame.f_code.co_filename,
            lineno=frame.f_lineno,
            data=traverse_frames(frame),
            code_str=code_str.rstrip(),
            event=event,
            frame_id=FrameID.create(event),
            last_i=frame.f_lasti,
        )
        # When entering a new call, replaces previous line(aka func caller) with caller
        # computation.
        if (
            computations
            and computations[-1].event == "line"
            and computation.frame_id.is_child_of(computations[-1].frame_id)
        ):
            computations[-1] = computation
        else:
            computations.append(computation)
    return local_tracer


def local_tracer(frame, event, arg):
    """Local trace function.
    """
    if utils.should_exclude(frame.f_code.co_filename):
        return
    print("\nthis is local: ", frame, blue(event), arg)

    code_str, surrounding = utils.get_code_str_and_surrounding(frame)

    if event == "line":
        frame_id = FrameID.create(event)
        # For multiline statement, skips if the logical line has been added.
        if (
            computations
            and computations[-1].frame_id == frame_id
            and computations[-1].surrounding == surrounding
        ):
            return
        # Records location, computation, data
        computations.append(
            Computation(
                filepath=frame.f_code.co_filename,
                lineno=frame.f_lineno,
                data=traverse_frames(frame),
                code_str=code_str.rstrip(),
                event=event,
                frame_id=frame_id,
                last_i=frame.f_lasti,
                surrounding=surrounding,
            )
        )

    elif event == "return":
        # At this point we don't need to record return but needs to update frame id.
        frame_id = (FrameID.create(event),)


global_frame = None


def init():
    global global_frame

    global_frame = sys._getframe(1)
    print("set tracer for frame: ", global_frame, global_frame.f_lasti)
    sys.settrace(global_tracer)
    global_frame.f_trace = local_tracer


def register(target):
    """Receives target variable and stops recording computation."""
    sys.settrace(None)
    global_frame.f_trace = None
    dump_computations(computations)


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
