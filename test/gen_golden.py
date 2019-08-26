"""Run all test scripts and generates golden data."""

import argparse
import glob
import os
from subprocess import Popen

from crayons import cyan, green
from cyberbrain.testing import COMPUTATION_GOLDEN, FLOW_GOLDEN

parser = argparse.ArgumentParser(description="Process some integers.")
parser.add_argument(
    "--override", action="store_true", help="Whether to override test data."
)


def generate_test_data(test_dir, filename):
    override = parser.parse_args().override

    if (
        os.path.exists(os.path.join(test_dir, COMPUTATION_GOLDEN))
        and os.path.exists(os.path.join(test_dir, FLOW_GOLDEN))
        and not override
    ):
        print(green("Test data already exists, skips " + test_dir))
        return

    test_filepath = os.path.join(test_dir, filename)
    print(cyan("Running test: " + test_filepath))
    Popen(["python", test_filepath, "--mode=golden", f"--test_dir={test_dir}"]).wait()


def collect_and_run_test_files():
    """Collects all test scripts under test/, run them and generate test data.

    If there are multiple files or sub-folders in a folder under test, main.py is always
    the entry point. All test files should respect this convention.
    """
    test_dirs = glob.glob("./test/*/")
    for test_dir in test_dirs:
        if test_dir.startswith("__"):
            # Excludes __pycache__
            continue
        py_files = [f for f in glob.glob(test_dir + "*") if f.endswith(".py")]
        if not py_files:
            continue
        target_file = (
            py_files[0]
            if len(py_files) == 1
            else next(filter(lambda f: f.endswith("main.py"), py_files))
        )
        generate_test_data(os.path.dirname(target_file), os.path.basename(target_file))


if __name__ == "__main__":
    collect_and_run_test_files()
