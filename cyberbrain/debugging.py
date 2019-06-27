import json
import os
from pprint import pprint


def dump_computations(computations, output_path=""):
    """Dump computations to a text JSON file."""
    print("dump_computations")

    with open(os.path.join(output_path, "output.json"), "w") as f:
        json.dump([c.to_dict() for c in computations], f, indent=2, sort_keys=True)
