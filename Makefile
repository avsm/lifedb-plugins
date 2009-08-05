PYTHON ?= /usr/bin/python
OBJDIR ?= $(PWD)/obj
APPS ?= Contacts Twitter IMAP Adium Phone Skype
DATA_DIR ?= $(HOME)/Documents/LifeDB
CACHE_DIR ?= $(HOME)/Library/Caches/LifeDB
INSTALL_PLUGINS ?= IMAP Contacts

.DEFAULT: all

.PHONY: all
all: 
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

.PHONY: install
install:
	if [ ! -d "$(DEST)" ]; then exit 1; fi
	if [ ! -d "$(ETC)" ]; then exit 1; fi
	for i in $(INSTALL_PLUGINS); do mkdir $(DEST)/$$i; cp -r $$i/ $(DEST)/$$i/; done
	for i in $(INSTALL_PLUGINS); do mkdir -p $(ETC)/conf; cp $$i/*.conf  $(ETC)/conf/; done
