PYTHON ?= python2.5

.PHONY: build
build:
	cd $(PWD)/offlineimap && $(PYTHON) setup.py py2app

.PHONY: clean
clean:
	cd offlineimap && $(PYTHON) setup.py clean
	rm -rf $(PWD)/offlineimap/build $(PWD)/offlineimap/dist

.PHONY: install
install:
	if [ ! -d "$(DEST)" ]; then exit 1; fi
	mkdir -p $(DEST)/offlineimap/dist
	cp -r ./offlineimap/dist/main.app $(DEST)/offlineimap/dist
	cp run.sh $(DEST)
	chmod a+x $(DEST)/run.sh

