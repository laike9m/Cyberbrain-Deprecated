"""Collects and run all test scripts."""

import os
from subprocess import PIPE, Popen

import pytest


@pytest.fixture
def run_scripts_and_compare():
    def runner(directory, filename):
        test_dir = os.path.join("test", directory)
        expected_output = os.path.join(test_dir, filename.strip("py") + "json")
        out, _ = Popen(
            ["python", os.path.join(test_dir, filename)], stdout=PIPE
        ).communicate()

        previous, json_text = out.decode("utf-8").split("__SEPERATOR__")
        print(previous)  # Shows scripts output.

        with open(expected_output, "r") as f:
            assert json_text.replace("\r\n", "\n").replace(
                r"\r\n", r"\n"
            ) == f.read().strip("\r\n")

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
