import simplejson
import sys
from datetime import datetime

from AppKit import *
import AddressBook
import objc
import os,sys,tempfile
from AddressBook_util import *

# The names of fields in the export, and the corresponding property.
FIELD_NAMES=(
    ('last_name',   AddressBook.kABLastNameProperty),
    ('first_name',  AddressBook.kABFirstNameProperty),
    ('birthday',   AddressBook.kABBirthdayProperty),
    ('company',    AddressBook.kABOrganizationProperty),
    ('job',        AddressBook.kABJobTitleProperty),
    ('calendar',   AddressBook.kABCalendarURIsProperty),
    ('note',       AddressBook.kABNoteProperty),
    ('middle_name', AddressBook.kABMiddleNameProperty),
    ('title',      AddressBook.kABTitleProperty),
)

FIELD_NAMES_ARRAY=(
    ('address',    AddressBook.kABAddressProperty),
)

SERVICES=(
    ('aim', AddressBook.kABAIMInstantProperty, None),
    ('jabber', AddressBook.kABJabberInstantProperty, None),
    ('msn', AddressBook.kABMSNInstantProperty, None),
    ('yahoo!', AddressBook.kABYahooInstantProperty, None),
    ('icq', AddressBook.kABICQInstantProperty, None),
    ('email', AddressBook.kABEmailProperty, None),
    ('phone', AddressBook.kABPhoneProperty, normalize_phone),
)

SERVICES_URL_LABELS=(
    ('twitter', 'LDB:twitter'),
    ('skype', 'LDB:skype'),
    ('facebook', 'LDB:facebook'),
)

def encodeField(value):
    if value is None:
        return None
    
    if isinstance(value, AddressBook.NSDate):
        return float(value.timeIntervalSince1970())
    elif isinstance(value, AddressBook.NSCFDictionary):
        d = {}
        for k in value:
            d[k] = encodeField(value[k])
        return d
    elif isinstance(value, AddressBook.ABMultiValue):
        # A multi-valued property, merge them into a single string
        result = { }
        for i in range(len(value)):
            l = encodeField(value.labelAtIndex_(i))
            if not l or l == "":
               raise ValueError(l)
            if not l in result:
                result[l] = []
            result[l].append(encodeField(value.valueAtIndex_(i)))
        return result
    elif type(value) == objc.pyobjc_unicode:
        return unicode(value)
    else:
        print type(value)
        raise NotImplemented

def getField(p, fieldName):
    return encodeField(p.valueForProperty_(fieldName))

def writeRecord(p, uid, mtime, attdir, fobj):
    print "NEW: %s" % addressbook_name(p)
    m = { '_type' : 'com.clinklabs.contact', '_timestamp' : mtime, 'abrecord' : uid , '_uid' : uid }
    for (fieldname, fieldkey) in FIELD_NAMES:
        v = getField(p, fieldkey)
        if v:
            m[fieldname] = v
    for (fieldname, fieldkey) in FIELD_NAMES_ARRAY:
        v = getField(p, fieldkey)
        if v:   
            if not fieldname in m:
                m[fieldname] = []
            if type(v) == dict:
                for k in v:
                    m[fieldname].append(v[k])
            else:
                m[fieldname].append(v)
           
    services = {}
    for (fieldname, fieldkey, cb) in SERVICES:
        v = getField(p, fieldkey)
        if v:   
            if not fieldname in services:
                services[fieldname] = []
            if type(v) == dict:
                for k in v:
                    if cb:
                        v[k] = map(lambda x: cb(x.lower()), v[k])
                    services[fieldname].extend(v[k])
            else:
                if cb:
                    v[k] = cb(v[k].lower())
                services[fieldname].append(v[k])
    urls = getField(p, AddressBook.kABURLsProperty)
    for (fieldname, fieldkey) in SERVICES_URL_LABELS:
        if urls and fieldkey in urls:
            if not fieldname in services:
                services[fieldname] = []
            services[fieldname].extend(urls[fieldkey])
    m['_services'] = services

    imgdata = p.imageData()
    if imgdata:
        tiffData = NSImage.alloc().initWithData_(imgdata).TIFFRepresentation()
        bitmap = NSBitmapImageRep.alloc().initWithData_(tiffData)
        fileType = NSPNGFileType
        imageData = bitmap.representationUsingType_properties_(fileType, None)
        picfname = os.path.join(attdir, (uid+".png"))
        picf = open(picfname, 'wb')
        picf.write(str(imageData.bytes()))
        picf.close ()
        print "NEW: %s" % picfname
        m['image'] = (uid+".png")
        m['_att'] = [(uid+".png")]

    simplejson.dump(m, fobj, indent=2)

def main(argv = None):
    """ main entry point """

    save_dir = os.getenv("LIFEDB_DIR")
    if not save_dir:
       print >> sys.stderr, "no LIFEDB_DIR in env"
       exit(1)
    book = AddressBook.ABAddressBook.sharedAddressBook()
    for p in book.people():
        mtime_ts = getField(p, AddressBook.kABModificationDateProperty)
        mtime = datetime.fromtimestamp(mtime_ts)
        uid = getField(p, AddressBook.kABUIDProperty)
        tt = mtime.timetuple()
        dir = os.path.join(save_dir,str(tt[0]),str(tt[1]),str(tt[2]))
        attdir = os.path.realpath(os.path.join(dir, "../_att"))
        fname = "%s.lifeentry" % uid
        full_fname = os.path.join(dir,fname) 
        if not os.path.isdir(dir):
           os.makedirs(dir)
        if not os.path.isdir(attdir):
           os.makedirs(attdir)
        if os.path.isfile(full_fname):
           fobj = open(full_fname,'r')
           oldjson = simplejson.load(fobj)
           fobj.close ()
           if oldjson['_timestamp'] < mtime_ts:
               print "UPDATING"
               fd, tmpname = tempfile.mkstemp(suffix=".lifeentry")
               fout = os.fdopen(fd, 'w')
               writeRecord(p, uid, mtime_ts, attdir, fout)
               fout.close()
               os.rename(tmpname, full_fname)
        else:
           print full_fname
           fd, tmpname = tempfile.mkstemp(suffix=".lifeentry")
           fout = os.fdopen(fd, 'w')
           writeRecord(p, uid, mtime_ts, attdir, fout)
           fout.close()
           os.rename(tmpname, full_fname)
    
if __name__ == "__main__":
    main()
