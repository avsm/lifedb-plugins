PYTHON ?= /usr/bin/python
OBJDIR ?= $(PWD)/obj
APPS ?= Contacts Twitter IMAP Adium Phone Skype
DATA_DIR ?= $(HOME)/Documents/LifeDB
CACHE_DIR ?= $(HOME)/Library/Caches/LifeDB

.DEFAULT: all

.PHONY: all
all: dist
	@ :
	
.PHONY: s-%
s-%: 
	@echo $($*)

# no user configurable variables after this

OBJDIR_STAMP := $(OBJDIR)/.stamp

# create the object directory
$(OBJDIR_STAMP):
	mkdir -p $(OBJDIR)
	@touch $@

.PHONY: clean
clean:
	rm -rf $(OBJDIR)
	cd IMAP && $(MAKE) clean

.PHONY: clean-data
clean-data:
	rm -rf $(DATA_DIR)
	rm -rf $(CACHE_DIR)

# build all the libraries we need
DISTDIR=$(PWD)/upstream

#######################
# Python modules install

PYTHON ?= python
export PYTHON
PYTHON_PREFIX=$(OBJDIR)/py
PYTHONPATH=$(PYTHON_PREFIX)/lib/python2.5/site-packages
export PYTHONPATH
PKG_CONFIG_PATH := /usr/local/lib/pkgconfig
export PKG_CONFIG_PATH

# virtual target to build an egg in our prefix
$(OBJDIR)/.egg-%: $(OBJDIR_STAMP)
	mkdir -p $(PYTHONPATH)
	easy_install -H None -f $(DISTDIR) --prefix=$(PYTHON_PREFIX) \
		--script-dir=$(OBJDIR)/bin $(DISTDIR)/$* 
	@touch $@

$(OBJDIR)/.tgz-%: $(OBJDIR_STAMP)
	rm -rf $(OBJDIR)/build-$*
	mkdir -p $(OBJDIR)/build-$*
	tar -C $(OBJDIR)/build-$* -zxf $(DISTDIR)/$*.tar.gz
	for i in $(wildcard $(DISTDIR)/$**.patch); do \
		cd $(OBJDIR)/build-$*/$* && patch -p0 < $$i; done
	mkdir -p $(PYTHONPATH)
	cd $(OBJDIR)/build-$*/$* && $(PYTHON) setup.py install --prefix=$(PYTHON_PREFIX)
	@touch $@

########################
# SimpleJSON installer

JSON_EGG := simplejson-2.0.7-py2.5-win32.egg
JSON_STAMP := $(OBJDIR)/.egg-$(JSON_EGG)

.PHONY: pyjson
pyjson: $(JSON_STAMP)
	 @ :

##########################
# Python twitter installer

PYTWITTER_EGG := twitter-0.5.1-py2.5.egg
PYTWITTER_STAMP := $(OBJDIR)/.egg-$(PYTWITTER_EGG)

.PHONY: pytwitter
pytwitter: $(PYTWITTER_STAMP)
	@ :

###############################
# FUSE Python

PYFUSE_DIST=fuse-python-0.2
PYFUSE_STAMP=$(OBJDIR)/.tgz-$(PYFUSE_DIST)

.PHONY: pyfuse
pyfuse: $(PYFUSE_STAMP)
	@ :

###############################
# LXML Python

LXML_DIST=lxml-2.1.5
LXML_STAMP=$(OBJDIR)/.tgz-$(LXML_DIST)

.PHONY: lxml
lxml: $(LXML_STAMP)
	@ :

###############################
# Skype Python

SKYPE_DIST=Skype4Py-1.0.31.0
SKYPE_STAMP=$(OBJDIR)/.tgz-$(SKYPE_DIST)

.PHONY: pyskype
pyskype: $(SKYPE_STAMP)
	@ :

###############################
#
SETENV_SCRIPT := $(OBJDIR)/export.sh
$(SETENV_SCRIPT): $(OBJDIR_STAMP)
	echo "export PYTHONPATH=$(PYTHONPATH)" > $@
	chmod a+x $@

#############################
# Python dateutil library

PYDATEUTIL_DIST := python-dateutil-1.4.1
PYDATEUTIL_STAMP := $(OBJDIR)/.tgz-$(PYDATEUTIL_DIST)

.PHONY: pydateutil
pydateutil: $(PYDATEUTIL_STAMP)
	@ :

.PHONY: dist
dist: lxml pyjson pytwitter pydateutil pyfuse pyskype $(SETENV_SCRIPT)
	cd IMAP && $(MAKE) 
