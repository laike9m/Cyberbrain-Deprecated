.PHONY: gen_test_data override_test_data

gen_test_data:
	tox -e py37 --run-command "python test/gen_test_data.py"

override_test_data:
	tox -e py37 --run-command "python test/gen_test_data.py --override"
