# IMAP server support
# Copyright (C) 2002 - 2007 John Goerzen
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

import imaplib
from offlineimap import imaplibutil, imaputil, threadutil
from offlineimap.ui import UIBase
from threading import *
import thread, hmac, os, time
import base64

try:
    # do we have a recent pykerberos?
    have_gss = False
    import kerberos
    if 'authGSSClientWrap' in dir(kerberos):
        have_gss = True
except ImportError:
    pass

class UsefulIMAPMixIn:
    def getstate(self):
        return self.state
    def getselectedfolder(self):
        if self.getstate() == 'SELECTED':
            return self.selectedfolder
        return None

    def select(self, mailbox='INBOX', readonly=None, force = 0):
        if (not force) and self.getselectedfolder() == mailbox \
           and self.is_readonly == readonly:
            # No change; return.
            return
        result = self.__class__.__bases__[1].select(self, mailbox, readonly)
        if result[0] != 'OK':
            raise ValueError, "Error from select: %s" % str(result)
        if self.getstate() == 'SELECTED':
            self.selectedfolder = mailbox
        else:
            self.selectedfolder = None

    def _mesg(self, s, secs=None):
        imaplibutil.new_mesg(self, s, secs)

class UsefulIMAP4(UsefulIMAPMixIn, imaplib.IMAP4):
    def open(self, host = '', port = imaplib.IMAP4_PORT):
        imaplibutil.new_open(self, host, port)

class UsefulIMAP4_SSL(UsefulIMAPMixIn, imaplibutil.WrappedIMAP4_SSL):
    def open(self, host = '', port = imaplib.IMAP4_SSL_PORT):
        imaplibutil.new_open_ssl(self, host, port)

class UsefulIMAP4_Tunnel(UsefulIMAPMixIn, imaplibutil.IMAP4_Tunnel): pass

class IMAPServer:
    GSS_STATE_STEP = 0
    GSS_STATE_WRAP = 1
    def __init__(self, config, reposname,
                 username = None, password = None, hostname = None,
                 port = None, ssl = 1, maxconnections = 1, tunnel = None,
                 reference = '""', sslclientcert = None, sslclientkey = None):
        self.reposname = reposname
        self.config = config
        self.username = username
        self.password = password
        self.passworderror = None
        self.goodpassword = None
        self.hostname = hostname
        self.tunnel = tunnel
        self.port = port
        self.usessl = ssl
        self.sslclientcert = sslclientcert
        self.sslclientkey = sslclientkey
        self.delim = None
        self.root = None
        if port == None:
            if ssl:
                self.port = 993
            else:
                self.port = 143
        self.maxconnections = maxconnections
        self.availableconnections = []
        self.assignedconnections = []
        self.lastowner = {}
        self.semaphore = BoundedSemaphore(self.maxconnections)
        self.connectionlock = Lock()
        self.reference = reference
        self.gss_step = self.GSS_STATE_STEP
        self.gss_vc = None
        self.gssapi = False

    def getpassword(self):
        if self.goodpassword != None:
            return self.goodpassword

        if self.password != None and self.passworderror == None:
            return self.password

        self.password = UIBase.getglobalui().getpass(self.reposname,
                                                     self.config,
                                                     self.passworderror)
        self.passworderror = None

        return self.password

    def getdelim(self):
        """Returns this server's folder delimiter.  Can only be called
        after one or more calls to acquireconnection."""
        return self.delim

    def getroot(self):
        """Returns this server's folder root.  Can only be called after one
        or more calls to acquireconnection."""
        return self.root


    def releaseconnection(self, connection):
        """Releases a connection, returning it to the pool."""
        self.connectionlock.acquire()
        self.assignedconnections.remove(connection)
        self.availableconnections.append(connection)
        self.connectionlock.release()
        self.semaphore.release()

    def md5handler(self, response):
        ui = UIBase.getglobalui()
        challenge = response.strip()
        ui.debug('imap', 'md5handler: got challenge %s' % challenge)

        passwd = self.getpassword()
        retval = self.username + ' ' + hmac.new(passwd, challenge).hexdigest()
        ui.debug('imap', 'md5handler: returning %s' % retval)
        return retval

    def plainauth(self, imapobj):
        UIBase.getglobalui().debug('imap',
                                   'Attempting plain authentication')
        imapobj.login(self.username, self.getpassword())

    def gssauth(self, response):
        data = base64.b64encode(response)
        try:
            if self.gss_step == self.GSS_STATE_STEP:
                if not self.gss_vc:
                    rc, self.gss_vc = kerberos.authGSSClientInit('imap@' + 
                                                                 self.hostname)
                    response = kerberos.authGSSClientResponse(self.gss_vc)
                rc = kerberos.authGSSClientStep(self.gss_vc, data)
                if rc != kerberos.AUTH_GSS_CONTINUE:
                   self.gss_step = self.GSS_STATE_WRAP
            elif self.gss_step == self.GSS_STATE_WRAP:
                rc = kerberos.authGSSClientUnwrap(self.gss_vc, data)
                response = kerberos.authGSSClientResponse(self.gss_vc)
                rc = kerberos.authGSSClientWrap(self.gss_vc, response,
                                                self.username)
            response = kerberos.authGSSClientResponse(self.gss_vc)
        except kerberos.GSSError, err:
            # Kerberos errored out on us, respond with None to cancel the
            # authentication
            UIBase.getglobalui().debug('imap',
                                       '%s: %s' % (err[0][0], err[1][0]))
            return None

        if not response:
            response = ''
        return base64.b64decode(response)

    def acquireconnection(self):
        """Fetches a connection from the pool, making sure to create a new one
        if needed, to obey the maximum connection limits, etc.
        Opens a connection to the server and returns an appropriate
        object."""

        self.semaphore.acquire()
        self.connectionlock.acquire()
        imapobj = None

        if len(self.availableconnections): # One is available.
            # Try to find one that previously belonged to this thread
            # as an optimization.  Start from the back since that's where
            # they're popped on.
            threadid = thread.get_ident()
            imapobj = None
            for i in range(len(self.availableconnections) - 1, -1, -1):
                tryobj = self.availableconnections[i]
                if self.lastowner[tryobj] == threadid:
                    imapobj = tryobj
                    del(self.availableconnections[i])
                    break
            if not imapobj:
                imapobj = self.availableconnections[0]
                del(self.availableconnections[0])
            self.assignedconnections.append(imapobj)
            self.lastowner[imapobj] = thread.get_ident()
            self.connectionlock.release()
            return imapobj
        
        self.connectionlock.release()   # Release until need to modify data

        success = 0
        while not success:
            # Generate a new connection.
            if self.tunnel:
                UIBase.getglobalui().connecting('tunnel', self.tunnel)
                imapobj = UsefulIMAP4_Tunnel(self.tunnel)
                success = 1
            elif self.usessl:
                UIBase.getglobalui().connecting(self.hostname, self.port)
                imapobj = UsefulIMAP4_SSL(self.hostname, self.port,
                                          self.sslclientkey, self.sslclientcert)
            else:
                UIBase.getglobalui().connecting(self.hostname, self.port)
                imapobj = UsefulIMAP4(self.hostname, self.port)

            imapobj.mustquote = imaplibutil.mustquote

            if not self.tunnel:
                try:
                    # Try GSSAPI and continue if it fails
                    if 'AUTH=GSSAPI' in imapobj.capabilities and have_gss:
                        UIBase.getglobalui().debug('imap',
                            'Attempting GSSAPI authentication')
                        try:
                            imapobj.authenticate('GSSAPI', self.gssauth)
                        except imapobj.error, val:
                            UIBase.getglobalui().debug('imap',
                                'GSSAPI Authentication failed')               
                        else:
                            self.gssapi = True
                            self.password = None

                    if not self.gssapi:
                        if 'AUTH=CRAM-MD5' in imapobj.capabilities:
                            UIBase.getglobalui().debug('imap',
                                                   'Attempting CRAM-MD5 authentication')
                            try:
                                imapobj.authenticate('CRAM-MD5', self.md5handler)
                            except imapobj.error, val:
                                self.plainauth(imapobj)
                        else:
                            self.plainauth(imapobj)
                    # Would bail by here if there was a failure.
                    success = 1
                    self.goodpassword = self.password
                except imapobj.error, val:
                    self.passworderror = str(val)
                    self.password = None

        if self.delim == None:
            listres = imapobj.list(self.reference, '""')[1]
            if listres == [None] or listres == None:
                # Some buggy IMAP servers do not respond well to LIST "" ""
                # Work around them.
                listres = imapobj.list(self.reference, '"*"')[1]
            self.delim, self.root = \
                        imaputil.imapsplit(listres[0])[1:]
            self.delim = imaputil.dequote(self.delim)
            self.root = imaputil.dequote(self.root)

        self.connectionlock.acquire()
        self.assignedconnections.append(imapobj)
        self.lastowner[imapobj] = thread.get_ident()
        self.connectionlock.release()
        return imapobj
    
    def connectionwait(self):
        """Waits until there is a connection available.  Note that between
        the time that a connection becomes available and the time it is
        requested, another thread may have grabbed it.  This function is
        mainly present as a way to avoid spawning thousands of threads
        to copy messages, then have them all wait for 3 available connections.
        It's OK if we have maxconnections + 1 or 2 threads, which is what
        this will help us do."""
        threadutil.semaphorewait(self.semaphore)

    def close(self):
        # Make sure I own all the semaphores.  Let the threads finish
        # their stuff.  This is a blocking method.
        self.connectionlock.acquire()
        threadutil.semaphorereset(self.semaphore, self.maxconnections)
        for imapobj in self.assignedconnections + self.availableconnections:
            imapobj.logout()
        self.assignedconnections = []
        self.availableconnections = []
        self.lastowner = {}
        self.connectionlock.release()

    def keepalive(self, timeout, event):
        """Sends a NOOP to each connection recorded.   It will wait a maximum
        of timeout seconds between doing this, and will continue to do so
        until the Event object as passed is true.  This method is expected
        to be invoked in a separate thread, which should be join()'d after
        the event is set."""
        ui = UIBase.getglobalui()
        ui.debug('imap', 'keepalive thread started')
        while 1:
            ui.debug('imap', 'keepalive: top of loop')
            time.sleep(timeout)
            ui.debug('imap', 'keepalive: after wait')
            if event.isSet():
                ui.debug('imap', 'keepalive: event is set; exiting')
                return
            ui.debug('imap', 'keepalive: acquiring connectionlock')
            self.connectionlock.acquire()
            numconnections = len(self.assignedconnections) + \
                             len(self.availableconnections)
            self.connectionlock.release()
            ui.debug('imap', 'keepalive: connectionlock released')
            threads = []
            imapobjs = []
        
            for i in range(numconnections):
                ui.debug('imap', 'keepalive: processing connection %d of %d' % (i, numconnections))
                imapobj = self.acquireconnection()
                ui.debug('imap', 'keepalive: connection %d acquired' % i)
                imapobjs.append(imapobj)
                thr = threadutil.ExitNotifyThread(target = imapobj.noop)
                thr.setDaemon(1)
                thr.start()
                threads.append(thr)
                ui.debug('imap', 'keepalive: thread started')

            ui.debug('imap', 'keepalive: joining threads')

            for thr in threads:
                # Make sure all the commands have completed.
                thr.join()

            ui.debug('imap', 'keepalive: releasing connections')

            for imapobj in imapobjs:
                self.releaseconnection(imapobj)

            ui.debug('imap', 'keepalive: bottom of loop')

class ConfigedIMAPServer(IMAPServer):
    """This class is designed for easier initialization given a ConfigParser
    object and an account name.  The passwordhash is used if
    passwords for certain accounts are known.  If the password for this
    account is listed, it will be obtained from there."""
    def __init__(self, repository, passwordhash = {}):
        """Initialize the object.  If the account is not a tunnel,
        the password is required."""
        self.repos = repository
        self.config = self.repos.getconfig()
        usetunnel = self.repos.getpreauthtunnel()
        if not usetunnel:
            host = self.repos.gethost()
            user = self.repos.getuser()
            port = self.repos.getport()
            ssl = self.repos.getssl()
            sslclientcert = self.repos.getsslclientcert()
            sslclientkey = self.repos.getsslclientkey()
        reference = self.repos.getreference()
        server = None
        password = None
        
        if repository.getname() in passwordhash:
            password = passwordhash[repository.getname()]

        # Connect to the remote server.
        if usetunnel:
            IMAPServer.__init__(self, self.config, self.repos.getname(),
                                tunnel = usetunnel,
                                reference = reference,
                                maxconnections = self.repos.getmaxconnections())
        else:
            if not password:
                password = self.repos.getpassword()
            IMAPServer.__init__(self, self.config, self.repos.getname(),
                                user, password, host, port, ssl,
                                self.repos.getmaxconnections(),
                                reference = reference,
                                sslclientcert = sslclientcert,
                                sslclientkey = sslclientkey)
