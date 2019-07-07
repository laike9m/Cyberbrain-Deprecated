"""Backtraces var change from target to program start."""

import ast

from . import utils


# TODO: We need some sort of data structure to consume computations and analyze its
# related computations and build relationships. It should be able to extend with
# infinite layers, and each node should be isomorphic and generic to maintain different
# types of relations.


def parse_code_str(code_str) -> ast.AST:
    """Parses code string in a computation, which can be incomplete.

    Once we found something that leads to error while parsing, we should handle it here.
    """
    if code_str.endswith(":"):
        code_str += "pass"
    try:
        return ast.parse(code_str)
    except IndentationError:
        return ast.parse(code_str.strip())


def trace_var(computation_manager):
    """Backtrace var change."""
    # prints final trace output
    def printer(computation, names):
        print("vars: ")
        for name in names:
            # need to check existence because line event fires before line is executed.
            if name in computation.data[0]:
                print(name, computation.data[0][name], computation.code_str)

    register_call_ast = ast.parse(computation_manager.last_computation.code_str.strip())
    # Asserts last computation is cyberbrain.register(target)
    assert register_call_ast.body[0].value.func.value.id == "cyberbrain"

    # Finds the target identifier by checking argument passed to register().
    target_identifier = register_call_ast.body[0].value.args[0].id
    target_identifiers = {target_identifier}

    # Finally, backtrace the records of each line
    for computation in reversed(computation_manager.computations):
        if computation.event_type == "line":
            print("code_str is:", computation.code_str)
            names = utils.find_names(parse_code_str(computation.code_str))
            if target_identifiers & names:
                printer(computation, names)
                target_identifiers |= names
        elif computation.event_type == "call":
            names = utils.find_names(parse_code_str(computation.code_str))
            if target_identifiers & names:
                printer(computation, names)
                target_identifiers |= names
