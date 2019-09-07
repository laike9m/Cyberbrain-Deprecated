"""Formats trace result to user friendly output."""

import html
import itertools
from os.path import abspath, expanduser, join
from typing import List

from graphviz import Digraph

from .flow import Flow, Node

DESKTOP = abspath(join(expanduser("~"), "Desktop"))

g = Digraph(name="Cyberbrain Output")


class NodeView:
    """Class that wraps a node and deal with visualization."""

    _portname_cache = {}  # Maps node address to their node to avoid duplicates.
    _incrementor = itertools.count()  # Generates 1, 2, 3, ...

    def __init__(self, node: Node):
        self._node = node
        self._portname = self._generate_portname()

    def __getattr__(self, name):
        """Redirects attribute access to stored node."""
        return getattr(self._node, name)

    def _generate_portname(self):
        node_addr = id(self._node)
        if node_addr not in self._portname_cache:
            self._portname_cache[node_addr] = str(next(self._incrementor))
        return self._portname_cache[node_addr]

    @property
    def portname(self):
        return self._portname

    @property
    def tracking(self):
        """Tracking does not necessarily need to be displayed."""
        return str(self._node.tracking)

    @property
    def var_changes(self):
        """Formats var changes."""
        output = ""
        for ap in self.var_appearances:
            output += f"{ap.id} = {ap.value}\n"

        for mod in self.var_modifications:
            output += f"{mod.id} {mod.old_value} -> {mod.new_value}\n"

        # TODO: add var_switch to edge
        return output

    @property
    def next(self):
        return NodeView(self._node.next) if self._node.next else None

    @property
    def step_into(self):
        return NodeView(self._node.step_into) if self._node.step_into else None

    @property
    def returned_from(self):
        return NodeView(self._node.returned_from) if self._node.returned_from else None


def generate_subgraph(frame_start: NodeView):
    current = frame_start
    name = str(frame_start.frame_id) + "_code"
    lines: List[str] = []
    while current is not None:
        # TODO: Only inserts code if there are var changes on this node.
        # or it is a call node and there are var changes inside the call.
        # if current.var_changes or current.is_target:
        lines.append(
            (
                f"<tr><td align='left' port='{current.portname}'>{html.escape(current.code_str)}</td>"
                f"<td align='left' bgcolor='yellow'>&#9700;&nbsp;{html.escape(current.var_changes)}</td></tr>"
            )
        )
        # if current.var_changes:
        #     name_metadata = current.portname + "_metadata"
        #     g.node(name_metadata, label=current.var_changes, shape="cds")
        #     g.edge(name_metadata, f"{name}:{current.portname}")
        if current.is_callsite():
            g.edge(f"{name}:{current.portname}", generate_subgraph(current.step_into))
        current = current.next
    print("".join(lines))
    g.node(
        name,
        label="<<table cellspacing='0' CELLBORDER='0'>%s</table>>" % "".join(lines),
        xlabel=str(frame_start.frame_id),
        shape="plaintext",
    )
    return name


def generate_output(flow: Flow, filename=None):
    generate_subgraph(NodeView(flow.start))
    g.render(join(DESKTOP, filename or "output"), view=True)
