PYTHON ?= python

.PHONY: build
build:
	cd $(PWD)/offlineimap && $(PYTHON) setup.py build

.PHONY: clean
clean:
	cd offlineimap && $(PYTHON) setup.py clean
	rm -rf $(PWD)/offlineimap/build
