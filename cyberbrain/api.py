"""Cyberbrain public API and tracer setup."""

import sys

from absl import flags

from . import backtrace, flow, format, testing, utils
from .basis import _dummy
from .computation import computation_manager

FLAGS = flags.FLAGS

# run: Invoked by users.
# test: Verifies cyberbrain's internal state is the same as golden.
# golden: Generates golden file.
# debug: Prints cyberbrain's internal state, but don't do assertion.
flags.DEFINE_enum(
    "mode",
    "run",
    ["run", "test", "golden", "debug"],
    "The mode which Cyberbrain runs in.",
)
flags.DEFINE_string("test_dir", None, "Directory to save test output to.")


def global_tracer(frame, event_type, arg):
    """Global trace function."""
    if utils.should_exclude(frame.f_code.co_filename):
        return
    # print("\nglobal: ", frame, event_type, frame.f_code.co_filename, frame.f_lineno)

    if event_type == "call":
        succeeded = computation_manager.add_computation(event_type, frame, arg)
        # https://docs.python.org/3/library/inspect.html#the-interpreter-stack
        del frame
        if succeeded:
            return local_tracer


def local_tracer(frame, event_type, arg):
    """Local trace function."""
    if utils.should_exclude(frame.f_code.co_filename):
        return
    # print("\nlocal: ", frame, event_type, frame.f_code.co_filename, frame.f_lineno)

    if event_type in {"line", "return"}:
        computation_manager.add_computation(event_type, frame, arg)

    del frame


global_frame = None


def init():
    """Inits tracing."""
    global global_frame

    global_frame = sys._getframe(1)
    sys.settrace(global_tracer)
    global_frame.f_trace = local_tracer


def register(target=_dummy):
    """Receives target variable and stops recording computation.

    If target is not given, it is only called to terminate tracing and dump data.
    """
    FLAGS(sys.argv)  # See https://github.com/chris-chris/pysc2-examples/issues/5.
    sys.settrace(None)
    global_frame.f_trace = None
    if target is not _dummy:
        execution_flow = flow.build_flow(computation_manager)
        backtrace.trace_flow(execution_flow)
        # format.generate_output(execution_flow)

    if FLAGS.mode in {"test", "golden", "debug"}:
        testing.dump_computation(computation_manager)
        testing.dump_flow(execution_flow)
