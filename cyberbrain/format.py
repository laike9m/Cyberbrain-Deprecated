"""Formats trace result to user friendly output."""

import itertools

from graphviz import Digraph

from .flow import Flow, Node

# g = Digraph(
#     name="Cyberbrain Output", graph_attr=[("forcelabels", "true")], format="canon"
# )
g = Digraph(name="Cyberbrain Output")


class NodeView:
    """Class that wraps a node and deal with visualization."""

    _name_cache = {}  # Maps node address to their node to avoid duplicates.
    _incrementor = itertools.count()  # Generates 1, 2, 3, ...

    def __init__(self, node: Node):
        self._node = node
        self._name = self._generate_name()

    def __getattr__(self, name):
        """Redirects attribute access to stored node."""
        return getattr(self._node, name)

    def _generate_name(self):
        node_addr = id(self._node)
        if node_addr not in self._name_cache:
            self._name_cache[node_addr] = str(next(self._incrementor))
        return self._name_cache[node_addr]

    @property
    def name(self):
        return self._name

    @property
    def tracking(self):
        """tracking does not necessarily need to be displayed."""
        return str(self._node.tracking)

    @property
    def var_changes(self):
        """Formats var changes."""
        output = ""
        for ap in self.var_appearances:
            output += f"appear {ap.id.name}={ap.value}\n"

        for mod in self.var_modifications:
            output += f"modify {mod.id.name} {mod.old_value} -> {mod.new_value}\n"

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
    with g.subgraph(
        name="cluster_" + str(frame_start.frame_id),
        graph_attr=[
            ("style", "filled"),
            ("color", "lightgrey"),
            ("label", str(frame_start.frame_id)),
            ("overlap", "scale"),
        ],
        node_attr=[("style", "filled"), ("color", "white")],
    ) as sub:
        while current is not None:
            sub.node(
                current.name,
                label=current.code_str,
                fillcolor="lightblue",
                style="filled",
            )
            if current.var_changes:
                # Creates a subgraph so that node and metadata are on the same height.
                with g.subgraph(name=current.name + "_meta_sub") as meta_sub:
                    name_metadata = current.name + "_metadata"
                    meta_sub.node(current.name)
                    meta_sub.node(name_metadata, label=current.var_changes, shape="cds")
                    meta_sub.attr(rank="same")
                    meta_sub.edge(name_metadata, current.name, style="invis")
            if current.next:
                sub.edge(current.name, current.next.name)
            if current.is_callsite():
                generate_subgraph(current.step_into)
                sub.edge(current.name, current.step_into.name)
                if current.returned_from:
                    sub.edge(current.returned_from.name, current.name)
            current = current.next


def generate_output(flow: Flow):
    generate_subgraph(NodeView(flow.start))

    # print(g.pipe().decode("utf-8"))
    g.render("output1.svg", view=True)
