"""Debugging utilities."""

import json
import os
from typing import Dict

from absl import flags
from crayons import yellow

from .computation import ComputationManager
from .flow import Flow, Node

FLAGS = flags.FLAGS

COMPUTATION_TEST_OUTPUT = "computation.json"
COMPUTATION_GOLDEN = "computation.golden.json"
FLOW_TEST_OUTPUT = "flow.json"
FLOW_GOLDEN = "flow.golden.json"


def dump_computation(cm: ComputationManager):
    """Converts computations to a JSON and writes to stdout.

    Caller should receive and handle output.
    """
    if FLAGS.mode == "test":
        filepath = os.path.join(FLAGS.test_dir, COMPUTATION_TEST_OUTPUT)
    elif FLAGS.mode == "golden":
        filepath = os.path.join(FLAGS.test_dir, COMPUTATION_GOLDEN)
        print(yellow("Generating test data: " + filepath))

    with open(filepath, "w") as f:
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

    if FLAGS.mode == "test":
        filepath = os.path.join(FLAGS.test_dir, FLOW_TEST_OUTPUT)
    elif FLAGS.mode == "golden":
        filepath = os.path.join(FLAGS.test_dir, FLOW_GOLDEN)
        print(yellow("Generating test data: " + filepath))

    with open(filepath, "w") as f:
        json.dump(obj=output, fp=f, indent=2)
