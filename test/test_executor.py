# Collect and run all test scripts.

import os
from subprocess import Popen


def test_hello_world():
    test_dir = "test/hello_world/"
    test_output = os.path.join(test_dir, "output.json")
    expected_output = os.path.join(test_dir, "expected.json")
    Popen(["python", "test/hello_world/hello.py"]).wait()
    with open(test_output, "r") as f1, open(expected_output, "r") as f2:
        assert f1.read() == f2.read()
    os.remove(test_output)
