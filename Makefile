PROJECT=typeit

test:
	pytest -s tests/

typecheck:
	mypy --config-file setup.cfg --package $(PROJECT)
