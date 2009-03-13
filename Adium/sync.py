# Parse and sync Adium logs with a LifeDB

import os, sys
import glob
import simplejson
from xml.dom.minidom import parse
from datetime import datetime
import dateutil.parser
import time
import hashlib
import base64
import xml
import lxml.html

cache_dir = None
save_dir = None

def parseLog(chatlog):
    mtime = os.stat(chatlog).st_mtime
    try:
        tree = parse(chatlog)
    except xml.parsers.expat.ExpatError, err:
        print >> sys.stderr, "Warning: %s is not XML, skipping" % chatlog
        return
    chats = tree.getElementsByTagName('chat')
    for chat in chats:
        account = chat.getAttribute('account')
        service = chat.getAttribute('service')
        version = chat.getAttribute('version')
        transport = chat.getAttribute('transport')
        uri = chat.namespaceURI
        info = { 'account': account, 'service': service, 'uri': uri }
        if version != "": info['version'] = version
        if transport != "": info['transport'] = transport
        msgs = chat.getElementsByTagName('message')
        # need to accumulate the list of participants in the chat based on who
        # talks that isnt the sender
        participants = []
        for msg in msgs:
            sender = msg.getAttribute('sender')
            if sender != account and sender not in participants:
               participants.append(sender)
        for msg in msgs:
            sender = msg.getAttribute('sender')
            tm = msg.getAttribute('time')
            time_parsed = dateutil.parser.parse(tm)
            tt = time_parsed.timetuple()
            time_float = time.mktime(tt)
            # very dodgily ignoring unicode errors here, but copes with some malformed messages
            body = unicode.join(u'',map(lambda x: unicode(x.toxml(encoding='utf-8'), errors='ignore'), msg.childNodes))
            body = lxml.html.fromstring(body).text_content()
            m = { 'sender' : sender, 'time': time_float, 'text' : body }
            m['_type'] = 'com.adium'
            m['_timestamp'] = time_float
            # this message originated from the current user, so its from us
            # and to the participants
            m['_from'] = { 'type' : service, 'id': sender }
            if sender == account:
                m['_to'] = map(lambda x: { 'type': service, 'id' : x }, participants)
            else:
                m['_to'] = [{ 'type' :service, 'id': account }]
            m.update(info)
            h = hashlib.sha1()
            h.update(service)
            h.update(account)
            h.update(sender)
            h.update(tm)
            h.update(body)
            uid = h.hexdigest()
            output_dir = os.path.join(save_dir, str(tt[0]), str(tt[1]), str(tt[2]))
            output_filename = "%s.lifeentry" % uid
            if not os.path.isdir(output_dir):
                os.makedirs(output_dir)
            fout = open(os.path.join(output_dir, output_filename), 'w')
            fout.write(simplejson.dumps(m, indent=2))
            fout.close()

    # update the cache log with the mtime
    update_cache_file(chatlog, mtime)

def get_cache_filename(log_filename):
    h = hashlib.sha1()
    h.update(log_filename)
    return os.path.join(cache_dir, h.hexdigest())

def update_cache_file(log_filename, new_time):
    cache_filename = get_cache_filename(log_filename)
    if not os.path.isdir(cache_dir):
       os.makedirs(cache_dir)
    if os.path.isfile(cache_filename):
        os.utime(cache_filename, (new_time, new_time))
    else:
        fout = open(cache_filename, 'w')
        fout.close()

def needs_parsing(log_filename):
    cache_filename = get_cache_filename(log_filename)
    if not os.path.isfile(cache_filename):
        print >> sys.stderr, "NEW: not seen before: %s" % log_filename
        return True
    else:
        cache_st = os.stat(cache_filename)
        logfl_st = os.stat(log_filename)
        if cache_st.st_mtime < logfl_st.st_mtime:
            print >> sys.stderr, "MOD: cache has older mtime: %s" % log_filename
            return True
        else:
            #print >> sys.stderr, "OLD: %s" % log_filename
            return False
    
def main():
    global save_dir, cache_dir
    save_dir = os.getenv("LIFEDB_DIR")
    if not save_dir:
        print >> sys.stderr, "no LIFEDB_DIR in env"
        exit(1)
    cache_dir = os.getenv("LIFEDB_CACHE_DIR")
    if not cache_dir: 
        print >> sys.stderr, "no LIFEDB_CACHE_DIR in env"
        exit(1)
    logdir = "%s/Library/Application Support/Adium 2.0/Users/Default/Logs/" % os.getenv("HOME")
    if not os.path.isdir(logdir):
        print >> sys.stderr, "Unable to find Adium log dir in: %s" % logdir
        exit(1)

    for root, dirs, files in os.walk(logdir):
        for f in files:
            logfile = os.path.join(root, f)
            if needs_parsing(logfile):
                parseLog(logfile)
    
if __name__ == "__main__":
    main()
