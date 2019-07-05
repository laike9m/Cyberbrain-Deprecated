"""Cyberbrain API."""

import sys

from crayons import blue, red

from . import utils
from .computation import computation_manager
from .debugging import dump_computations
from .frame_id import FrameID


def global_tracer(frame, event_type, arg):
    """Global trace function."""
    if utils.should_exclude(frame.f_code.co_filename):
        return
    print("\nthis is global: ", frame, frame.f_code.co_filename, red(event_type), arg)

    if event_type == "call":
        computation_manager.add_computation(event_type, frame)

    del frame  # https://docs.python.org/3/library/inspect.html#the-interpreter-stack
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

    del frame


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
