# Copyright (C) 2003 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

from ConfigParser import ConfigParser
from offlineimap.localeval import LocalEval
import os

class CustomConfigParser(ConfigParser):
    def getdefault(self, section, option, default, *args, **kwargs):
        """Same as config.get, but returns the "default" option if there
        is no such option specified."""
        if self.has_option(section, option):
            return apply(self.get, [section, option] + list(args), kwargs)
        else:
            return default
    
    def getdefaultint(self, section, option, default, *args, **kwargs):
        if self.has_option(section, option):
            return apply(self.getint, [section, option] + list(args), kwargs)
        else:
            return default

    def getdefaultfloat(self, section, option, default, *args, **kwargs):
        if self.has_option(section, option):
            return apply(self.getfloat, [section, option] + list(args), kwargs)
        else:
            return default

    def getdefaultboolean(self, section, option, default, *args, **kwargs):
        if self.has_option(section, option):
            return apply(self.getboolean, [section, option] + list(args),
                         kwargs)
        else:
            return default

    def getmetadatadir(self):
        metadatadir = os.path.expanduser(self.getdefault("general", "metadata", "~/.offlineimap"))
        if not os.path.exists(metadatadir):
            os.mkdir(metadatadir, 0700)
        return metadatadir

    def getlocaleval(self):
        if self.has_option("general", "pythonfile"):
            path = os.path.expanduser(self.get("general", "pythonfile"))
        else:
            path = None
        return LocalEval(path)

    def getsectionlist(self, key):
        """Returns a list of sections that start with key + " ".  That is,
        if key is "Account", returns all section names that start with
        "Account ", but strips off the "Account ".  For instance, for
        "Account Test", returns "Test"."""

        key = key + ' '
        return [x[len(key):] for x in self.sections() \
                if x.startswith(key)]

def CustomConfigDefault():
    """Just a sample constant that won't occur anywhere else to use for the
    default."""
    pass

class ConfigHelperMixin:
    def _confighelper_runner(self, option, default, defaultfunc, mainfunc):
        if default != CustomConfigDefault:
            return apply(defaultfunc, [self.getsection(), option, default])
        else:
            return apply(mainfunc, [self.getsection(), option])

    def getconf(self, option, default = CustomConfigDefault):
        return self._confighelper_runner(option, default,
                                         self.getconfig().getdefault,
                                         self.getconfig().get)

    def getconfboolean(self, option, default = CustomConfigDefault):
        return self._confighelper_runner(option, default,
                                         self.getconfig().getdefaultboolean,
                                         self.getconfig().getboolean)

    def getconfint(self, option, default = CustomConfigDefault):
        return self._confighelper_runner(option, default,
                                         self.getconfig().getdefaultint,
                                         self.getconfig().getint)
    
    def getconffloat(self, option, default = CustomConfigDefault):
        return self._confighelper_runner(option, default,
                                         self.getconfig().getdefaultfloat,
                                         self.getconfig().getfloat)
    
