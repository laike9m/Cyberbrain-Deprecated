"""Debugging utilities."""

import json
import os
import sys

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
    def traverse_node(node: Node):
        while node is not None:
            # print(node)
            if node.is_callsite():
                traverse_node(node.step_into)
            node = node.next

    traverse_node(flow.start)
