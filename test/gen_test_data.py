# Collect and run all test scripts.

import os
import glob
from subprocess import Popen, PIPE

from crayons import green, yellow, cyan


def generate_test_data(test_dir, filename):
    expected_output = os.path.join(test_dir, filename.strip("py") + "json")
    if os.path.exists(expected_output):
        print(green("Test data already exists, skips " + expected_output))
        return

    test_filepath = os.path.join(test_dir, filename)
    print(cyan("Running test: " + test_filepath))
    out, _ = Popen(["python", test_filepath], stdout=PIPE).communicate()

    previous, json_text = out.decode("utf-8").split("__SEPERATOR__")

    print(yellow("Generating test data: " + expected_output))
    with open(expected_output, "w") as f:
        f.write(json_text)
        f.write("\n")


def collect_and_run_test_files():
    files = glob.glob("./test/*/*.py")
    for f in files:
        generate_test_data(os.path.dirname(f), os.path.basename(f))


if __name__ == "__main__":
    collect_and_run_test_files()
