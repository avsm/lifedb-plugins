PYTHON ?= python2.5

.PHONY: build
build:
	$(PYTHON) setup-manifest.py py2app
	$(PYTHON) setup-parse_db.py py2app

.PHONY: install
install:
	if [ ! -d "$(DEST)" ]; then exit 1; fi
	mkdir -p $(DEST)/dist
	cp -r ./dist/manifest.app ./dist/parse_db.app $(DEST)/dist
	cp run.sh $(DEST)
	chmod a+x $(DEST)/run.sh

.PHONY: clean
clean:
	$(PYTHON) setup-manifest.py clean
	$(PYTHON) setup-parse_db.py clean
	rm -rf dist build

.PHONY: builddep
builddep:
	sudo port -v install py25-simplejson
