"""Debugging utilities."""

import json
import os
from collections import defaultdict
from os.path import basename
from pprint import pprint
from typing import Dict

from absl import flags
from crayons import yellow  # pylint: disable=E0611

from .computation import ComputationManager
from .flow import Flow, Node

FLAGS = flags.FLAGS

COMPUTATION_TEST_OUTPUT = "computation.json"
COMPUTATION_GOLDEN = "computation.golden.json"
FLOW_TEST_OUTPUT = "flow.json"
FLOW_GOLDEN = "flow.golden.json"


class _SetEncoder(json.JSONEncoder):
    """Custom encoder to dump set as list."""

    def default(self, o):  # pylint: disable=E0202
        if isinstance(o, set):
            return sorted(list(o))
        return json.JSONEncoder.default(self, o)


def dump_computation(cm: ComputationManager):
    """Converts computations to a JSON and writes to stdout.

    Caller should receive and handle output.
    """
    if FLAGS.mode == "test":
        filepath = os.path.join(FLAGS.test_dir, COMPUTATION_TEST_OUTPUT)
    elif FLAGS.mode == "golden":
        filepath = os.path.join(FLAGS.test_dir, COMPUTATION_GOLDEN)
        print(yellow("Generating test data: " + filepath))

    output = {
        str(fid): [c.to_dict() for c in comps] for fid, comps in cm.frame_groups.items()
    }
    if FLAGS.mode == "debug":
        pprint(f"Computation is:\n{output}")
        return

    with open(filepath, "w") as f:
        json.dump(obj=output, fp=f, indent=2, cls=_SetEncoder)


def _dump_node(node: Node) -> Dict:
    result = defaultdict(list)
    result.update(
        {
            "code": node.code_str,
            "next": getattr(node.next, "code_str", ""),
            "prev": getattr(node.prev, "code_str", ""),
            "step_into": getattr(node.step_into, "code_str", ""),
            "returned_from": getattr(node.returned_from, "code_str", ""),
        }
    )
    for ap in node.var_appearances:
        result["var_changes"].append(f"appear {ap.id}={ap.value}\n")
    for mod in node.var_modifications:
        result["var_changes"].append(
            f"modify {mod.id} {mod.old_value} -> {mod.new_value}\n"
        )
    result[
        "location"
    ] = f"{basename(node.source_location.filepath)}: {node.frame_id.co_name}"
    if node.tracking:
        result["tracking"] = node.tracking
    if hasattr(node, "param_to_arg"):
        result["param_to_arg"] = node.param_to_arg
    return result


def dump_flow(flow: Flow):
    output = []

    def traverse_node(node: Node):
        while node is not None:
            output.append(_dump_node(node))
            if node.is_callsite:
                traverse_node(node.step_into)
            node = node.next

    traverse_node(flow.start)

    if FLAGS.mode == "test":
        filepath = os.path.join(FLAGS.test_dir, FLOW_TEST_OUTPUT)
    elif FLAGS.mode == "golden":
        filepath = os.path.join(FLAGS.test_dir, FLOW_GOLDEN)
        print(yellow("Generating test data: " + filepath))

    if FLAGS.mode == "debug":
        pprint(f"Flow is:\n{output}")
        return

    with open(filepath, "w") as f:
        json.dump(obj=output, fp=f, indent=2, cls=_SetEncoder)
