"""Collects and run all test scripts."""

import os
from subprocess import Popen

import pytest
from cyberbrain.testing import (
    COMPUTATION_GOLDEN,
    COMPUTATION_TEST_OUTPUT,
    FLOW_GOLDEN,
    FLOW_TEST_OUTPUT,
)


@pytest.fixture
def run_scripts_and_compare():
    def runner(directory, filename):
        test_dir = os.path.abspath(os.path.join("test", directory))

        Popen(
            [
                "python",
                os.path.join(test_dir, filename),
                "--mode=test",
                f"--test_dir={test_dir}",
            ]
        ).wait()

        # Checks computation is equal.
        output_path = os.path.join(test_dir, COMPUTATION_TEST_OUTPUT)
        with open(output_path, "r") as test_out, open(
            os.path.join(test_dir, COMPUTATION_GOLDEN), "r"
        ) as golden:
            assert test_out.read().replace("\r\n", "\n").replace(
                r"\r\n", r"\n"
            ) == golden.read().strip("\r\n")

        os.remove(output_path)

        # Checks flow is equal.
        output_path = os.path.join(test_dir, FLOW_TEST_OUTPUT)
        with open(output_path, "r") as test_out, open(
            os.path.join(test_dir, FLOW_GOLDEN), "r"
        ) as golden:
            assert test_out.read().replace("\r\n", "\n").replace(
                r"\r\n", r"\n"
            ) == golden.read().strip("\r\n")

        os.remove(output_path)

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


def test_doc_example(run_scripts_and_compare):
    run_scripts_and_compare("doc_example", "doc_example.py")


def test_method(run_scripts_and_compare):
    run_scripts_and_compare("method", "method.py")
