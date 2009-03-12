# IMAP utility module
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

import re, string, types
from offlineimap.ui import UIBase
quotere = re.compile('^("(?:[^"]|\\\\")*")')

def debug(*args):
    msg = []
    for arg in args:
        msg.append(str(arg))
    UIBase.getglobalui().debug('imap', " ".join(msg))

def dequote(string):
    """Takes a string which may or may not be quoted and returns it, unquoted.
    This function does NOT consider parenthised lists to be quoted.
    """

    debug("dequote() called with input:", string)
    if not (string[0] == '"' and string[-1] == '"'):
        return string
    string = string[1:-1]               # Strip off quotes.
    string = string.replace('\\"', '"')
    string = string.replace('\\\\', '\\')
    debug("dequote() returning:", string)
    return string

def flagsplit(string):
    if string[0] != '(' or string[-1] != ')':
        raise ValueError, "Passed string '%s' is not a flag list" % string
    return imapsplit(string[1:-1])

def options2hash(list):
    debug("options2hash called with input:", list)
    retval = {}
    counter = 0
    while (counter < len(list)):
        retval[list[counter]] = list[counter + 1]
        counter += 2
    debug("options2hash returning:", retval)
    return retval

def flags2hash(string):
    return options2hash(flagsplit(string))

def imapsplit(imapstring):
    """Takes a string from an IMAP conversation and returns a list containing
    its components.  One example string is:

    (\\HasNoChildren) "." "INBOX.Sent"

    The result from parsing this will be:

    ['(\\HasNoChildren)', '"."', '"INBOX.Sent"']"""

    debug("imapsplit() called with input:", imapstring)
    if type(imapstring) != types.StringType:
        debug("imapsplit() got a non-string input; working around.")
        # Sometimes, imaplib will throw us a tuple if the input
        # contains a literal.  See Python bug
        # #619732 at https://sourceforge.net/tracker/index.php?func=detail&aid=619732&group_id=5470&atid=105470
        # One example is:
        # result[0] = '() "\\\\" Admin'
        # result[1] = ('() "\\\\" {19}', 'Folder\\2')
        #
        # This function will effectively get result[0] or result[1], so
        # if we get the result[1] version, we need to parse apart the tuple
        # and figure out what to do with it.  Each even-numbered
        # part of it should end with the {} number, and each odd-numbered
        # part should be directly a part of the result.  We'll
        # artificially quote it to help out.
        retval = []
        for i in range(len(imapstring)):
            if i % 2:                   # Odd: quote then append.
                arg = imapstring[i]
                # Quote code lifted from imaplib
                arg = arg.replace('\\', '\\\\')
                arg = arg.replace('"', '\\"')
                arg = '"%s"' % arg
                debug("imapsplit() non-string [%d]: Appending %s" %\
                      (i, arg))
                retval.append(arg)
            else:
                # Even -- we have a string that ends with a literal
                # size specifier.  We need to strip off that, then run
                # what remains through the regular imapsplit parser.
                # Recursion to the rescue.
                arg = imapstring[i]
                arg = re.sub('\{\d+\}$', '', arg)
                debug("imapsplit() non-string [%d]: Feeding %s to recursion" %\
                      (i, arg))
                retval.extend(imapsplit(arg))
        debug("imapsplit() non-string: returning %s" % str(retval))
        return retval
        
    workstr = imapstring.strip()
    retval = []
    while len(workstr):
        if workstr[0] == '(':
            rparenc = 1 # count of right parenthesis to match
            rpareni = 1 # position to examine
 	    while rparenc: # Find the end of the group.
 	    	if workstr[rpareni] == ')':  # end of a group
 			rparenc -= 1
 		elif workstr[rpareni] == '(':  # start of a group
 			rparenc += 1
 		rpareni += 1  # Move to next character.
            parenlist = workstr[0:rpareni]
            workstr = workstr[rpareni:].lstrip()
            retval.append(parenlist)
        elif workstr[0] == '"':
            quotelist = quotere.search(workstr).group(1)
            workstr = workstr[len(quotelist):].lstrip()
            retval.append(quotelist)
        else:
            splits = string.split(workstr, maxsplit = 1)
            splitslen = len(splits)
            # The unquoted word is splits[0]; the remainder is splits[1]
            if splitslen == 2:
                # There's an unquoted word, and more string follows.
                retval.append(splits[0])
                workstr = splits[1]    # split will have already lstripped it
                continue
            elif splitslen == 1:
                # We got a last unquoted word, but nothing else
                retval.append(splits[0])
                # Nothing remains.  workstr would be ''
                break
            elif splitslen == 0:
                # There was not even an unquoted word.
                break
    debug("imapsplit() returning:", retval)
    return retval
            
def flagsimap2maildir(flagstring):
    flagmap = {'\\seen': 'S',
               '\\answered': 'R',
               '\\flagged': 'F',
               '\\deleted': 'T',
               '\\draft': 'D'}
    retval = []
    imapflaglist = [x.lower() for x in flagstring[1:-1].split()]
    for imapflag in imapflaglist:
        if flagmap.has_key(imapflag):
            retval.append(flagmap[imapflag])
    retval.sort()
    return retval

def flagsmaildir2imap(list):
    flagmap = {'S': '\\Seen',
               'R': '\\Answered',
               'F': '\\Flagged',
               'T': '\\Deleted',
               'D': '\\Draft'}
    retval = []
    for mdflag in list:
        if flagmap.has_key(mdflag):
            retval.append(flagmap[mdflag])
    retval.sort()
    return '(' + ' '.join(retval) + ')'

def listjoin(list):
    start = None
    end = None
    retval = []

    def getlist(start, end):
        if start == end:
            return(str(start))
        else:
            return(str(start) + ":" + str(end))
        

    for item in list:
        if start == None:
            # First item.
            start = item
            end = item
        elif item == end + 1:
            # An addition to the list.
            end = item
        else:
            # Here on: starting a new list.
            retval.append(getlist(start, end))
            start = item
            end = item

    if start != None:
        retval.append(getlist(start, end))

    return ",".join(retval)



            
        
