.PHONY: gen_test_data override_test_data

gen_golden:
	tox -e py37 --run-command "python test/gen_golden.py"

override_golden:
	tox -e py37 --run-command "python test/gen_golden.py --override"
