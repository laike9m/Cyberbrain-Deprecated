import json
import sys


def dump_computations(computations):
    """Converts computations to a JSON and writes to stdout.

    Caller should receive and handle output.
    """
    json_text = json.dumps(
        [c.to_dict() for c in computations], indent=2, sort_keys=True
    )
    sys.stdout.write("__SEPERATOR__")
    sys.stdout.write(json_text)
