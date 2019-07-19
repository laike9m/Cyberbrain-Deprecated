"""Execution flow that represents a program's execution."""

import typing

from .utils import ID
from . import backtrace


class Node:
    """Base class."""

    def build_relation(self, **relation_dict: typing.Dict[str, "Node"]):
        """A convenient function to add relations at once.

        Usage:
            node.build_relation({'prev': node_x, 'next': node_y})
        """
        for relation_name, node in relation_dict.items():
            if relation_name not in {"prev", "next", "step_into", "returned_from"}:
                raise Exception("wrong relation_name: " + relation_name)
            setattr(self, relation_name, node)


class Line(Node):
    """Node that forms the execution flow."""

    def __init__(self, code_str: str):
        self.code_str = code_str
        self.code_ast = backtrace.parse_code_str(code_str)
        self.prev = None
        self.next = None


class Call(Node):
    """Node that represents a callsite."""

    def __init__(self, code_str: str, arg_to_param: typing.Dict[ID, ID]):
        self.code_str = code_str
        self.callsite_ast = backtrace.parse_code_str(code_str)
        self.arg_to_param = arg_to_param
        self.prev = None
        self.next = None
        self.step_into = None
        self.returned_from = None


class Flow:
    """Class that represents program's execution.

    A flow consists of multiple Calls and Nodes.
    """

    def __init__(self):
        self.start = None
        self.target = None

    def add(self):
        """Adds a node to flow."""
        pass
