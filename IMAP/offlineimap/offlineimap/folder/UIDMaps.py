# Base folder support
# Copyright (C) 2002 John Goerzen
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

from threading import *
from offlineimap import threadutil
from offlineimap.threadutil import InstanceLimitedThread
from offlineimap.ui import UIBase
from IMAP import IMAPFolder
import os.path, re

class MappingFolderMixIn:
    def _initmapping(self):
        self.maplock = Lock()
        (self.diskr2l, self.diskl2r) = self._loadmaps()
        self._mb = self.__class__.__bases__[1]

    def _getmapfilename(self):
        return os.path.join(self.repository.getmapdir(),
                            self.getfolderbasename())
        
    def _loadmaps(self):
        self.maplock.acquire()
        try:
            mapfilename = self._getmapfilename()
            if not os.path.exists(mapfilename):
                return ({}, {})
            file = open(mapfilename, 'rt')
            r2l = {}
            l2r = {}
            while 1:
                line = file.readline()
                if not len(line):
                    break
                line = line.strip()
                (str1, str2) = line.split(':')
                loc = long(str1)
                rem = long(str2)
                r2l[rem] = loc
                l2r[loc] = rem
            return (r2l, l2r)
        finally:
            self.maplock.release()

    def _savemaps(self, dolock = 1):
        mapfilename = self._getmapfilename()
        if dolock: self.maplock.acquire()
        try:
            file = open(mapfilename + ".tmp", 'wt')
            for (key, value) in self.diskl2r.iteritems():
                file.write("%d:%d\n" % (key, value))
            file.close()
            os.rename(mapfilename + '.tmp', mapfilename)
        finally:
            if dolock: self.maplock.release()

    def _uidlist(self, mapping, items):
        return [mapping[x] for x in items]

    def cachemessagelist(self):
        self._mb.cachemessagelist(self)
        reallist = self._mb.getmessagelist(self)

        self.maplock.acquire()
        try:
            # OK.  Now we've got a nice list.  First, delete things from the
            # summary that have been deleted from the folder.

            for luid in self.diskl2r.keys():
                if not reallist.has_key(luid):
                    ruid = self.diskl2r[luid]
                    del self.diskr2l[ruid]
                    del self.diskl2r[luid]

            # Now, assign negative UIDs to local items.
            self._savemaps(dolock = 0)
            nextneg = -1

            self.r2l = self.diskr2l.copy()
            self.l2r = self.diskl2r.copy()

            for luid in reallist.keys():
                if not self.l2r.has_key(luid):
                    ruid = nextneg
                    nextneg -= 1
                    self.l2r[luid] = ruid
                    self.r2l[ruid] = luid
        finally:
            self.maplock.release()

    def getmessagelist(self):
        """Gets the current message list.
        You must call cachemessagelist() before calling this function!"""

        retval = {}
        localhash = self._mb.getmessagelist(self)
        self.maplock.acquire()
        try:
            for key, value in localhash.items():
                try:
                    key = self.l2r[key]
                except KeyError:
                    # Sometimes, the IMAP backend may put in a new message,
                    # then this function acquires the lock before the system
                    # has the chance to note it in the mapping.  In that case,
                    # just ignore it.
                    continue
                value = value.copy()
                value['uid'] = self.l2r[value['uid']]
                retval[key] = value
            return retval
        finally:
            self.maplock.release()

    def getmessage(self, uid):
        """Returns the content of the specified message."""
        return self._mb.getmessage(self, self.r2l[uid])

    def savemessage(self, uid, content, flags, rtime):
        """Writes a new message, with the specified uid.
        If the uid is < 0, the backend should assign a new uid and return it.

        If the backend cannot assign a new uid, it returns the uid passed in
        WITHOUT saving the message.

        If the backend CAN assign a new uid, but cannot find out what this UID
        is (as is the case with many IMAP servers), it returns 0 but DOES save
        the message.
        
        IMAP backend should be the only one that can assign a new uid.

        If the uid is > 0, the backend should set the uid to this, if it can.
        If it cannot set the uid to that, it will save it anyway.
        It will return the uid assigned in any case.
        """
        if uid < 0:
            # We cannot assign a new uid.
            return uid
        if uid in self.r2l:
            self.savemessageflags(uid, flags)
            return uid
        newluid = self._mb.savemessage(self, -1, content, flags, rtime)
        if newluid < 1:
            raise ValueError, "Backend could not find uid for message"
        self.maplock.acquire()
        try:
            self.diskl2r[newluid] = uid
            self.diskr2l[uid] = newluid
            self.l2r[newluid] = uid
            self.r2l[uid] = newluid
            self._savemaps(dolock = 0)
        finally:
            self.maplock.release()

    def getmessageflags(self, uid):
        return self._mb.getmessageflags(self, self.r2l[uid])

    def getmessagetime(self, uid):
        return None

    def savemessageflags(self, uid, flags):
        self._mb.savemessageflags(self, self.r2l[uid], flags)

    def addmessageflags(self, uid, flags):
        self._mb.addmessageflags(self, self.r2l[uid], flags)

    def addmessagesflags(self, uidlist, flags):
        self._mb.addmessagesflags(self, self._uidlist(self.r2l, uidlist),
                                  flags)

    def _mapped_delete(self, uidlist):
        self.maplock.acquire()
        try:
            needssave = 0
            for ruid in uidlist:
                luid = self.r2l[ruid]
                del self.r2l[ruid]
                del self.l2r[luid]
                if ruid > 0:
                    del self.diskr2l[ruid]
                    del self.diskl2r[luid]
                    needssave = 1
            if needssave:
                self._savemaps(dolock = 0)
        finally:
            self.maplock.release()

    def deletemessageflags(self, uid, flags):
        self._mb.deletemessageflags(self, self.r2l[uid], flags)

    def deletemessagesflags(self, uidlist, flags):
        self._mb.deletemessagesflags(self, self._uidlist(self.r2l, uidlist),
                                     flags)

    def deletemessage(self, uid):
        self._mb.deletemessage(self, self.r2l[uid])
        self._mapped_delete([uid])

    def deletemessages(self, uidlist):
        self._mb.deletemessages(self, self._uidlist(self.r2l, uidlist))
        self._mapped_delete(uidlist)

    #def syncmessagesto_neguid_msg(self, uid, dest, applyto, register = 1):
    # does not need changes because it calls functions that make the changes   
    # same goes for all other sync messages types.
    

# Define a class for local part of IMAP.
class MappedIMAPFolder(MappingFolderMixIn, IMAPFolder):
    def __init__(self, *args, **kwargs):
	apply(IMAPFolder.__init__, (self,) + args, kwargs)
        self._initmapping()
