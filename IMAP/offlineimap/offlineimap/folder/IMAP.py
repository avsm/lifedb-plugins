# IMAP folder support
# Copyright (C) 2002-2007 John Goerzen
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

from Base import BaseFolder
import imaplib
from offlineimap import imaputil, imaplibutil
from offlineimap.ui import UIBase
from offlineimap.version import versionstr
import rfc822, time, string, random, binascii, re
from StringIO import StringIO
from copy import copy


class IMAPFolder(BaseFolder):
    def __init__(self, imapserver, name, visiblename, accountname, repository):
        self.config = imapserver.config
        self.expunge = repository.getexpunge()
        self.name = imaputil.dequote(name)
        self.root = None # imapserver.root
        self.sep = imapserver.delim
        self.imapserver = imapserver
        self.messagelist = None
        self.visiblename = visiblename
        self.accountname = accountname
        self.repository = repository
        self.randomgenerator = random.Random()
        BaseFolder.__init__(self)

    def selectro(self, imapobj):
        """Select this folder when we do not need write access.
        Prefer SELECT to EXAMINE if we can, since some servers
        (Courier) do not stabilize UID validity until the folder is
        selected."""
        try:
            imapobj.select(self.getfullname())
        except imapobj.readonly:
            imapobj.select(self.getfullname(), readonly = 1)

    def getaccountname(self):
        return self.accountname

    def suggeststhreads(self):
        return 1

    def waitforthread(self):
        self.imapserver.connectionwait()

    def getcopyinstancelimit(self):
        return 'MSGCOPY_' + self.repository.getname()

    def getvisiblename(self):
        return self.visiblename

    def getuidvalidity(self):
        imapobj = self.imapserver.acquireconnection()
        try:
            # Primes untagged_responses
            self.selectro(imapobj)
            return long(imapobj.untagged_responses['UIDVALIDITY'][0])
        finally:
            self.imapserver.releaseconnection(imapobj)
    
    def quickchanged(self, statusfolder):
        # An IMAP folder has definitely changed if the number of
        # messages or the UID of the last message have changed.  Otherwise
        # only flag changes could have occurred.
        imapobj = self.imapserver.acquireconnection()
        try:
            # Primes untagged_responses
            imapobj.select(self.getfullname(), readonly = 1, force = 1)
            try:
                # Some mail servers do not return an EXISTS response if
                # the folder is empty.
                maxmsgid = long(imapobj.untagged_responses['EXISTS'][0])
            except KeyError:
                return True

            # Different number of messages than last time?
            if maxmsgid != len(statusfolder.getmessagelist()):
                return True

            if maxmsgid < 1:
                # No messages; return
                return False

            # Now, get the UID for the last message.
            response = imapobj.fetch('%d' % maxmsgid, '(UID)')[1]
        finally:
            self.imapserver.releaseconnection(imapobj)

        # Discard the message number.
        messagestr = string.split(response[0], maxsplit = 1)[1]
        options = imaputil.flags2hash(messagestr)
        if not options.has_key('UID'):
            return True
        uid = long(options['UID'])
        saveduids = statusfolder.getmessagelist().keys()
        saveduids.sort()
        if uid != saveduids[-1]:
            return True

        return False

    def cachemessagelist(self):
        imapobj = self.imapserver.acquireconnection()
        self.messagelist = {}

        try:
            # Primes untagged_responses
            imapobj.select(self.getfullname(), readonly = 1, force = 1)
            try:
                # Some mail servers do not return an EXISTS response if
                # the folder is empty.
                maxmsgid = long(imapobj.untagged_responses['EXISTS'][0])
            except KeyError:
                return
            if maxmsgid < 1:
                # No messages; return
                return

            # Now, get the flags and UIDs for these.
            # We could conceivably get rid of maxmsgid and just say
            # '1:*' here.
            response = imapobj.fetch('1:%d' % maxmsgid, '(FLAGS UID INTERNALDATE)')[1]
        finally:
            self.imapserver.releaseconnection(imapobj)
        for messagestr in response:
            # Discard the message number.
            messagestr = string.split(messagestr, maxsplit = 1)[1]
            options = imaputil.flags2hash(messagestr)
            if not options.has_key('UID'):
                UIBase.getglobalui().warn('No UID in message with options %s' %\
                                          str(options),
                                          minor = 1)
            else:
                uid = long(options['UID'])
                flags = imaputil.flagsimap2maildir(options['FLAGS'])
                rtime = imaplibutil.Internaldate2epoch(messagestr)
                self.messagelist[uid] = {'uid': uid, 'flags': flags, 'time': rtime}

    def getmessagelist(self):
        return self.messagelist

    def getmessage(self, uid):
        ui = UIBase.getglobalui()
        imapobj = self.imapserver.acquireconnection()
        try:
            imapobj.select(self.getfullname(), readonly = 1)
            initialresult = imapobj.uid('fetch', '%d' % uid, '(BODY.PEEK[])')
            ui.debug('imap', 'Returned object from fetching %d: %s' % \
                     (uid, str(initialresult)))
            return initialresult[1][0][1].replace("\r\n", "\n")
                
        finally:
            self.imapserver.releaseconnection(imapobj)

    def getmessagetime(self, uid):
        return self.messagelist[uid]['time']
    
    def getmessageflags(self, uid):
        return self.messagelist[uid]['flags']

    def savemessage_getnewheader(self, content):
        raise NotImplemented
        headername = 'X-OfflineIMAP-%s-' % str(binascii.crc32(content)).replace('-', 'x')
        headername += binascii.hexlify(self.repository.getname()) + '-'
        headername += binascii.hexlify(self.getname())
        headervalue= '%d-' % long(time.time())
        headervalue += str(self.randomgenerator.random()).replace('.', '')
        headervalue += '-v' + versionstr
        return (headername, headervalue)

    def savemessage_addheader(self, content, headername, headervalue):
        raise NotImplemented
        ui = UIBase.getglobalui()
        ui.debug('imap',
                 'savemessage_addheader: called to add %s: %s' % (headername,
                                                                  headervalue))
        insertionpoint = content.find("\r\n")
        ui.debug('imap', 'savemessage_addheader: insertionpoint = %d' % insertionpoint)
        leader = content[0:insertionpoint]
        ui.debug('imap', 'savemessage_addheader: leader = %s' % repr(leader))
        if insertionpoint == 0 or insertionpoint == -1:
            newline = ''
            insertionpoint = 0
        else:
            newline = "\r\n"
        newline += "%s: %s" % (headername, headervalue)
        ui.debug('imap', 'savemessage_addheader: newline = ' + repr(newline))
        trailer = content[insertionpoint:]
        ui.debug('imap', 'savemessage_addheader: trailer = ' + repr(trailer))
        return leader + newline + trailer

    def savemessage_searchforheader(self, imapobj, headername, headervalue):
        raise NotImplemented
        if imapobj.untagged_responses.has_key('APPENDUID'):
            return long(imapobj.untagged_responses['APPENDUID'][-1].split(' ')[1])

        ui = UIBase.getglobalui()
        ui.debug('imap', 'savemessage_searchforheader called for %s: %s' % \
                 (headername, headervalue))
        # Now find the UID it got.
        headervalue = imapobj._quote(headervalue)
        try:
            matchinguids = imapobj.uid('search', 'HEADER', headername, headervalue)[1][0]
        except imapobj.error, err:
            # IMAP server doesn't implement search or had a problem.
            ui.debug('imap', "savemessage_searchforheader: got IMAP error '%s' while attempting to UID SEARCH for message with header %s" % (err, headername))
            return 0
        ui.debug('imap', 'savemessage_searchforheader got initial matchinguids: ' + repr(matchinguids))

        if matchinguids == '':
            ui.debug('imap', "savemessage_searchforheader: UID SEARCH for message with header %s yielded no results" % headername)
            return 0

        matchinguids = matchinguids.split(' ')
        ui.debug('imap', 'savemessage_searchforheader: matchinguids now ' + \
                 repr(matchinguids))
        if len(matchinguids) != 1 or matchinguids[0] == None:
            raise ValueError, "While attempting to find UID for message with header %s, got wrong-sized matchinguids of %s" % (headername, str(matchinguids))
        matchinguids.sort()
        return long(matchinguids[0])

    def savemessage(self, uid, content, flags, rtime):
        raise NotImplemented
        imapobj = self.imapserver.acquireconnection()
        ui = UIBase.getglobalui()
        ui.debug('imap', 'savemessage: called')
        try:
            try:
                imapobj.select(self.getfullname()) # Needed for search
            except imapobj.readonly:
                ui.msgtoreadonly(self, uid, content, flags)
                # Return indicating message taken, but no UID assigned.
                # Fudge it.
                return 0
            
            # This backend always assigns a new uid, so the uid arg is ignored.
            # In order to get the new uid, we need to save off the message ID.

            message = rfc822.Message(StringIO(content))
            datetuple_msg = rfc822.parsedate(message.getheader('Date'))
            # Will be None if missing or not in a valid format.

            # If time isn't known
            if rtime == None and datetuple_msg == None:
                datetuple = time.localtime()
            elif rtime == None:
                datetuple = datetuple_msg
            else:
                datetuple = time.localtime(rtime)

            try:
                if datetuple[0] < 1981:
                    raise ValueError

                # Check for invalid date
                datetuple_check = time.localtime(time.mktime(datetuple))
                if datetuple[:2] != datetuple_check[:2]:
                    raise ValueError

                # This could raise a value error if it's not a valid format.
                date = imaplib.Time2Internaldate(datetuple) 
            except (ValueError, OverflowError):
                # Argh, sometimes it's a valid format but year is 0102
                # or something.  Argh.  It seems that Time2Internaldate
                # will rause a ValueError if the year is 0102 but not 1902,
                # but some IMAP servers nonetheless choke on 1902.
                date = imaplib.Time2Internaldate(time.localtime())

            ui.debug('imap', 'savemessage: using date ' + str(date))
            content = re.sub("(?<!\r)\n", "\r\n", content)
            ui.debug('imap', 'savemessage: initial content is: ' + repr(content))

            (headername, headervalue) = self.savemessage_getnewheader(content)
            ui.debug('imap', 'savemessage: new headers are: %s: %s' % \
                     (headername, headervalue))
            content = self.savemessage_addheader(content, headername,
                                                 headervalue)
            ui.debug('imap', 'savemessage: new content is: ' + repr(content))
            ui.debug('imap', 'savemessage: new content length is ' + \
                     str(len(content)))

            assert(imapobj.append(self.getfullname(),
                                       imaputil.flagsmaildir2imap(flags),
                                       date, content)[0] == 'OK')

            # Checkpoint.  Let it write out the messages, etc.
            assert(imapobj.check()[0] == 'OK')

            # Keep trying until we get the UID.
            ui.debug('imap', 'savemessage: first attempt to get new UID')
            uid = self.savemessage_searchforheader(imapobj, headername,
                                                   headervalue)
            # See docs for savemessage in Base.py for explanation of this and other return values
            if uid <= 0:
                ui.debug('imap', 'savemessage: first attempt to get new UID failed.  Going to run a NOOP and try again.')
                assert(imapobj.noop()[0] == 'OK')
                uid = self.savemessage_searchforheader(imapobj, headername,
                                                       headervalue)
        finally:
            self.imapserver.releaseconnection(imapobj)

        if uid: # avoid UID FETCH 0 crash happening later on
            self.messagelist[uid] = {'uid': uid, 'flags': flags}

        ui.debug('imap', 'savemessage: returning %d' % uid)
        return uid

    def savemessageflags(self, uid, flags):
        raise NotImplemented
        imapobj = self.imapserver.acquireconnection()
        try:
            try:
                imapobj.select(self.getfullname())
            except imapobj.readonly:
                UIBase.getglobalui().flagstoreadonly(self, [uid], flags)
                return
            result = imapobj.uid('store', '%d' % uid, 'FLAGS',
                                 imaputil.flagsmaildir2imap(flags))
            assert result[0] == 'OK', 'Error with store: ' + '. '.join(r[1])
        finally:
            self.imapserver.releaseconnection(imapobj)
        result = result[1][0]
        if not result:
            self.messagelist[uid]['flags'] = flags
        else:
            flags = imaputil.flags2hash(imaputil.imapsplit(result)[1])['FLAGS']
            self.messagelist[uid]['flags'] = imaputil.flagsimap2maildir(flags)

    def addmessageflags(self, uid, flags):
        self.addmessagesflags([uid], flags)

    def addmessagesflags_noconvert(self, uidlist, flags):
        self.processmessagesflags('+', uidlist, flags)

    def addmessagesflags(self, uidlist, flags):
        """This is here for the sake of UIDMaps.py -- deletemessages must
        add flags and get a converted UID, and if we don't have noconvert,
        then UIDMaps will try to convert it twice."""
        self.addmessagesflags_noconvert(uidlist, flags)

    def deletemessageflags(self, uid, flags):
        self.deletemessagesflags([uid], flags)

    def deletemessagesflags(self, uidlist, flags):
        self.processmessagesflags('-', uidlist, flags)

    def processmessagesflags(self, operation, uidlist, flags):
        if len(uidlist) > 101:
            # Hack for those IMAP ervers with a limited line length
            self.processmessagesflags(operation, uidlist[:100], flags)
            self.processmessagesflags(operation, uidlist[100:], flags)
            return
        
        imapobj = self.imapserver.acquireconnection()
        try:
            try:
                imapobj.select(self.getfullname())
            except imapobj.readonly:
                UIBase.getglobalui().flagstoreadonly(self, uidlist, flags)
                return
            r = imapobj.uid('store',
                            imaputil.listjoin(uidlist),
                            operation + 'FLAGS',
                            imaputil.flagsmaildir2imap(flags))
            assert r[0] == 'OK', 'Error with store: ' + '. '.join(r[1])
            r = r[1]
        finally:
            self.imapserver.releaseconnection(imapobj)
        # Some IMAP servers do not always return a result.  Therefore,
        # only update the ones that it talks about, and manually fix
        # the others.
        needupdate = copy(uidlist)
        for result in r:
            if result == None:
                # Compensate for servers that don't return anything from
                # STORE.
                continue
            attributehash = imaputil.flags2hash(imaputil.imapsplit(result)[1])
            if not ('UID' in attributehash and 'FLAGS' in attributehash):
                # Compensate for servers that don't return a UID attribute.
                continue
            lflags = attributehash['FLAGS']
            uid = long(attributehash['UID'])
            self.messagelist[uid]['flags'] = imaputil.flagsimap2maildir(lflags)
            try:
                needupdate.remove(uid)
            except ValueError:          # Let it slide if it's not in the list
                pass
        for uid in needupdate:
            if operation == '+':
                for flag in flags:
                    if not flag in self.messagelist[uid]['flags']:
                        self.messagelist[uid]['flags'].append(flag)
                    self.messagelist[uid]['flags'].sort()
            elif operation == '-':
                for flag in flags:
                    if flag in self.messagelist[uid]['flags']:
                        self.messagelist[uid]['flags'].remove(flag)

    def deletemessage(self, uid):
        raise NotImplemented
        self.deletemessages_noconvert([uid])

    def deletemessages(self, uidlist):
        raise NotImplemented
        self.deletemessages_noconvert(uidlist)

    def deletemessages_noconvert(self, uidlist):
        raise NotImplemented
        # Weed out ones not in self.messagelist
        uidlist = [uid for uid in uidlist if uid in self.messagelist]
        if not len(uidlist):
            return        

        self.addmessagesflags_noconvert(uidlist, ['T'])
        imapobj = self.imapserver.acquireconnection()
        try:
            try:
                imapobj.select(self.getfullname())
            except imapobj.readonly:
                UIBase.getglobalui().deletereadonly(self, uidlist)
                return
            if self.expunge:
                assert(imapobj.expunge()[0] == 'OK')
        finally:
            self.imapserver.releaseconnection(imapobj)
        for uid in uidlist:
            del self.messagelist[uid]
        
        
