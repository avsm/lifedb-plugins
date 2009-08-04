PYTHON ?= python2.5

.PHONY: build
build:
	$(PYTHON) setup.py py2app

.PHONY: run
run:
	@/usr/bin/python sync.py

.PHONY: install
install:
	if [ ! -d "$(DEST)" ]; then exit 1; fi
	mkdir -p $(DEST)/dist
	cp -r ./dist/main.app $(DEST)/dist
	cp run.sh $(DEST)
	chmod a+x $(DEST)/run.sh

.PHONY: clean
clean:
	$(PYTHON) setup.py clean
	rm -rf dist build
