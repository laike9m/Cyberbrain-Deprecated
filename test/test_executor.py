"""Collects and run all test scripts."""

import os
from subprocess import PIPE, Popen

import pytest

os.environ["CYBERBRAIN_DEV_PC"] = "true"


@pytest.fixture
def run_scripts_and_compare():
    def runner(directory, filename):
        test_dir = os.path.abspath(os.path.join("test", directory))
        golden = os.path.join(test_dir, filename.strip("py") + "json")
        output_computation = os.path.join(test_dir, "computation.json")
        out, _ = Popen(
            [
                "python",
                os.path.join(test_dir, filename),
                "--mode=test",
                f"--test_dir={test_dir}",
            ],
            stdout=PIPE,
        ).communicate()

        if out:
            print(out)  # Shows scripts output.

        with open(output_computation, "r") as f1, open(golden, "r") as f2:
            assert f1.read().replace("\r\n", "\n").replace(
                r"\r\n", r"\n"
            ) == f2.read().strip("\r\n")

        os.remove(output_computation)

    return runner


def test_hello_world(run_scripts_and_compare):
    run_scripts_and_compare("hello_world", "hello.py")


def test_function(run_scripts_and_compare):
    run_scripts_and_compare("function", "simple_func.py")


def test_multiline(run_scripts_and_compare):
    run_scripts_and_compare("multiline", "multiline_statement.py")


def test_exclude_events(run_scripts_and_compare):
    run_scripts_and_compare("exclude_events", "call_libs.py")


def test_modules(run_scripts_and_compare):
    run_scripts_and_compare("modules", "main.py")


def test_loop(run_scripts_and_compare):
    run_scripts_and_compare("loop", "loop.py")


def test_list_comp(run_scripts_and_compare):
    run_scripts_and_compare("list_comp", "list_comp.py")


def test_multicall(run_scripts_and_compare):
    run_scripts_and_compare("multicall", "multicall.py")
