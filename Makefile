# https://www.gnu.org/software/make/manual/html_node/Special-Variables.html
# https://ftp.gnu.org/old-gnu/Manuals/make-3.80/html_node/make_17.html
PROJECT_MKFILE_PATH       := $(word $(words $(MAKEFILE_LIST)),$(MAKEFILE_LIST))
PROJECT_MKFILE_DIR        := $(shell cd $(shell dirname $(PROJECT_MKFILE_PATH)); pwd)

PROJECT_NAME              := typeit
PROJECT_ROOT              := $(PROJECT_MKFILE_DIR)

BUILD_DIR                 := $(PROJECT_ROOT)/build
DIST_DIR                  := $(PROJECT_ROOT)/dist

update:
	python -m pip install -U pip
	python -m pip install -r $(PROJECT_ROOT)/requirements/minimal.txt
	python -m pip install -r $(PROJECT_ROOT)/requirements/test.txt
	python -m pip install -r $(PROJECT_ROOT)/requirements/extras/third_party.txt
	python -m pip install -e $(PROJECT_ROOT)

test:
	python -m pytest -s $(PROJECT_ROOT)/tests/

typecheck:
	mypy --config-file $(PROJECT_ROOT)/setup.cfg --package $(PROJECT_NAME)

publish: test
	rm -rf $(BUILD_DIR) $(DIST_DIR)
	python $(PROJECT_ROOT)/setup.py sdist bdist_wheel
	twine upload $(DIST_DIR)/*


shell:
	# pyopenssl on m1 issue https://github.com/NixOS/nixpkgs/issues/175875
	NIXPKGS_ALLOW_BROKEN=1 nix-shell $(PROJECT_ROOT)/shell.nix
