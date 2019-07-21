"""Execution flow that represents a program's execution."""

import ast
import typing

import astor

from .utils import ID
from . import backtrace


class Node:
    """Basic unit of an execution flow."""

    def __init__(
        self,
        *,
        code_str: str = None,
        code_ast: ast.AST = None,
        data: typing.Dict,
        arg_to_param: typing.Dict[ID, ID] = None
    ):
        if not any([code_str, code_ast]):
            raise ValueError("Should provide code_str or code_ast.")
        self.code_str = code_str or astor.to_source(code_ast)
        self.code_ast = code_ast or backtrace.parse_code_str(code_str)
        self.prev = None
        self.next = None
        self.step_into = None
        self.returned_from = None
        # For simplicity, uses a dict to represent data for now.
        self.data = data

    def build_relation(self, **relation_dict: typing.Dict[str, "Node"]):
        """A convenient function to add relations at once.

        Usage:
            node.build_relation(prev=node_x, next=node_y)
        """
        for relation_name, node in relation_dict.items():
            if relation_name not in {"prev", "next", "step_into", "returned_from"}:
                raise Exception("wrong relation_name: " + relation_name)
            setattr(self, relation_name, node)


class Flow:
    """Class that represents program's execution.

    A flow consists of multiple Calls and Nodes.
    """

    def __init__(self, start: Node, target: Node):
        self.start = start
        self.target = target
