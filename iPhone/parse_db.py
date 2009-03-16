# parse the SQLITE3 database in the iPhone into JSON for the LifeDB

import sqlite3
import sys, os
import simplejson
from datetime import datetime
import getopt

# CREATE TABLE message (ROWID INTEGER PRIMARY KEY AUTOINCREMENT, 
# address TEXT, date INTEGER, text TEXT, flags INTEGER, replace INTEGER, 
# svc_center TEXT, group_id INTEGER, association_id INTEGER, height INTEGER, 
# UIFlags INTEGER, version INTEGER);

from AppKit import *
import AddressBook

def my_number():
    book = AddressBook.ABAddressBook.sharedAddressBook()
    phones = book.me().valueForProperty_(AddressBook.kABPhoneProperty)
    mob_res = []
    other_res = []
    if phones:
        for i in range(len(phones)):
            num = phones.valueAtIndex_(i)
            lab = phones.labelAtIndex_(i)
            if lab == AddressBook.kABPhoneMobileLabel:
                mob_res.append(num)
            else:
                other_res.append(num)

    if len(mob_res) > 0:
        return mob_res[0]
    elif len(other_res) > 0:
        return other_res[0]
    raise ValueError, "couldnt determine your phone number from address book"

def usage(ret=2):
    print "Usage: %s [-u <IPhone UUID>] -m [call|sms] <SMS sqlite.db>" % sys.argv[0]
    sys.exit(ret)
    
def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hu:m:o:")
    except getopt.GetoptError, err:
        print str(err)
        usage(2)
    uid_prefix = "Default_iPhone"
    save_dir=None
    mode=None
    for o,a in opts:
        if o == '-h':
            usage(0)
        elif o == '-u':
            uid_prefix=a
        elif o == '-o':
            save_dir=a 
        elif o == '-m':
            if a == 'sms':
                mode = 'SMS'
            elif a== 'call':
                mode = 'Call'
            else:
                usage()
    if len(args) != 1 or not mode or not save_dir:
        usage()
    conn = sqlite3.connect(args[0])
    c = conn.cursor()
    if mode == 'SMS':
        res = parseSMS(c, uid_prefix)
    elif mode == 'Call':
        res = parseCall(c, uid_prefix)
    for uid in res:
        tt = datetime.fromtimestamp(res[uid]['_timestamp']).timetuple()
        output_dir = os.path.join(save_dir, str(tt[0]), str(tt[1]), str(tt[2]))
        full_path = os.path.join(output_dir, "%s.lifeentry" % uid)
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)
        if not os.path.isfile(full_path):
            print "+ %s" % full_path
            fout = open(full_path, 'w')
            simplejson.dump(res[uid], fout, indent=2)
            fout.close()

def normalize_phone(p):
    import re
    if len(p) < 1:
        return p
    pn = re.sub('[^0-9|\+]','',p)
    if len(pn) < 1:
        return pn
    if pn[0:1] == "00" and len(pn) > 2:
        pn = "+%s" % pn[2:]
    elif pn[0]  == '0':
        pn = "+44%s" % pn[1:]
    return pn

def parseSMS(c, uid_prefix):
    mynum = my_number()
    c.execute('''
        SELECT group_member.address,text,flags,replace,version,date
        FROM message INNER JOIN group_member ON group_member.group_id = message.group_id;
    ''')
    sms={}
    for row in c:
        e = {}
        if row[1]:
          e['number'] = normalize_phone(row[0])
          e['text'] = row[1]
          e['flags'] = row[2]
          e['replace'] = row[3]
          e['version'] = row[4]
          e['_timestamp'] = float(row[5])
          e['_type'] = 'com.apple.iphone.sms'
          if e['flags'] == 2:
            e['_from'] = { 'type': 'phone', 'id' : e['number'] }
            e['_to'] = [ { 'type': 'phone', 'id' : mynum } ]
          elif e['flags'] == 3:
            e['_from'] = { 'type': 'phone', 'id' : mynum }
            e['_to'] = [ { 'type': 'phone', 'id' : e['number'] } ]
          uid = "%s.SMS.%s" % (uid_prefix,row[0])
          sms[uid] = e
    return sms

def parseCall(c, uid_prefix):
    mynum = my_number()
    c.execute('''
        SELECT * from call
    ''')
    call={}
    for row in c:
        # XXX needs to include the phone UUID as well
        e = {}
        e['number'] = normalize_phone(row[1])
        e['_timestamp'] = float(row[2])
        e['duration'] = int(row[3])
        e['flags'] = int(row[4])
        e['weirdid'] = row[5]
        e['_type'] = 'com.apple.iphone.call'
        if e['flags'] == 4:
            e['_from'] = { 'type': 'phone', 'id' : e['number'] }
            e['_to'] = [ { 'type': 'phone', 'id' : mynum } ]
        elif e['flags'] == 5:
            e['_from'] = { 'type': 'phone', 'id' : mynum }
            e['_to'] = [ { 'type': 'phone', 'id' : e['number'] } ]
        uid = "%s.Call.%s" % (uid_prefix, row[0])
        call[uid] = e
    return call
    
if __name__ == "__main__":
    main()
