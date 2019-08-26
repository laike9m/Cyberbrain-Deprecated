"""Debugging utilities."""

import json
import os
import sys
from typing import Dict

from absl import flags

from .computation import ComputationManager
from .flow import Flow, Node

FLAGS = flags.FLAGS


def dump_computation(cm: ComputationManager):
    """Converts computations to a JSON and writes to stdout.

    Caller should receive and handle output.
    """
    with open(os.path.join(FLAGS.test_dir, "computation.json"), "w") as f:
        json.dump(
            obj={
                str(fid): [c.to_dict() for c in comps]
                for fid, comps in cm.frame_groups.items()
            },
            fp=f,
            indent=2,
        )


def dump_flow(flow: Flow):
    output = []

    def dump_node(node: Node) -> Dict:
        return {
            "code": node.code_str,
            "next": getattr(node.next, "code_str", ""),
            "prev": getattr(node.prev, "code_str", ""),
            "step_into": getattr(node.step_into, "code_str", ""),
            "returned_from": getattr(node.returned_from, "code_str", ""),
        }

    def traverse_node(node: Node):
        while node is not None:
            output.append(dump_node(node))
            if node.is_callsite():
                traverse_node(node.step_into)
            node = node.next

    traverse_node(flow.start)

    with open(os.path.join(FLAGS.test_dir, "flow.json"), "w") as f:
        json.dump(obj=output, fp=f, indent=2)
