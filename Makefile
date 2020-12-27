# https://www.gnu.org/software/make/manual/html_node/Special-Variables.html
# https://ftp.gnu.org/old-gnu/Manuals/make-3.80/html_node/make_17.html
PROJECT_MKFILE_PATH       := $(word $(words $(MAKEFILE_LIST)),$(MAKEFILE_LIST))
PROJECT_MKFILE_DIR        := $(shell cd $(shell dirname $(PROJECT_MKFILE_PATH)); pwd)

PROJECT_NAME              := typeit
PROJECT_ROOT              := $(PROJECT_MKFILE_DIR)

BUILD_DIR                 := $(PROJECT_ROOT)/build
DIST_DIR                  := $(PROJECT_ROOT)/dist

test:
	pytest -s $(PROJECT_ROOT)/tests/

typecheck:
	mypy --config-file $(PROJECT_ROOT)/setup.cfg --package $(PROJECT_NAME)

publish: test
	rm -rf $(BUILD_DIR) $(DIST_DIR)
	python $(PROJECT_ROOT)/setup.py sdist bdist_wheel
	twine upload $(DIST_DIR)/*
