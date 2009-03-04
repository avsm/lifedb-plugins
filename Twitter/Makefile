USERNAME ?= foo
PASSWORD ?= bar
include Makefile.conf

.PHONY: run
run:
	@env PYTHONPATH=../obj/py/lib/python2.5/site-packages /usr/bin/python sync.py $(USERNAME) $(PASSWORD) $(LIFEDB_DIR)
