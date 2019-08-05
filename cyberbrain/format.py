"""Formats trace result to user friendly output."""

from graphviz import Digraph

from .flow import Flow, Node

# The global graph.
g = Digraph(name="Cyberbrain Output", graph_attr=[("forcelabels", "true")])


def generate_subgraph(frame_start: Node):
    current = frame_start
    with g.subgraph(name="cluster_" + str(frame_start.frame_id)) as sub:
        sub.attr(style="filled", color="lightgrey", label=str(frame_start.frame_id))
        sub.node_attr.update(style="filled", color="white")
        while current is not None:
            sub.node(current.name, label=current.code_str, xlabel=str(current))
            if current.next:
                sub.edge(current.name, current.next.name)
            if current.is_callsite():
                generate_subgraph(current.step_into)
                sub.edge(current.name, current.step_into.name)
                if current.returned_from:
                    sub.edge(current.returned_from.name, current.name)
            current = current.next


def generate_output(flow: Flow):
    generate_subgraph(flow.start)

    # print(graph.pipe().decode("utf-8"))
    g.render("output.svg", view=True)
