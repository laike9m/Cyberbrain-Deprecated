# Collect and run all test scripts.

import glob
import os
from subprocess import PIPE, Popen

from crayons import cyan, green, yellow


def generate_test_data(test_dir, filename):
    expected_output = os.path.join(test_dir, filename.strip("py") + "json")
    if os.path.exists(expected_output):
        print(green("Test data already exists, skips " + expected_output))
        return

    test_filepath = os.path.join(test_dir, filename)
    print(cyan("Running test: " + test_filepath))
    out, _ = Popen(["python", test_filepath], stdout=PIPE).communicate()

    previous, json_text = out.decode("utf-8").split("__SEPERATOR__")
    print(previous)

    print(yellow("Generating test data: " + expected_output))
    with open(expected_output, "w") as f:
        f.write(json_text)
        f.write("\n")


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
