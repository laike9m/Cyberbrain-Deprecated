"""Debugging utilities."""

import json
import sys

from . import computation


def dump_computations(cm: computation.ComputationManager):
    """Converts computations to a JSON and writes to stdout.

    Caller should receive and handle output.
    """

    json_text = json.dumps(
        {
            str(fid): [c.to_dict() for c in comps]
            for fid, comps in cm.frame_groups.items()
        },
        indent=2,
    )
    sys.stdout.write("__SEPERATOR__")
    sys.stdout.write(json_text)
