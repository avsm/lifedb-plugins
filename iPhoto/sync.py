import plistlib
import os, sys, shutil
import simplejson
import sqlite3
import EXIF
import sqlite3
from datetime import datetime
from CoreFoundation import kCFAbsoluteTimeIntervalSince1970
from AppKit import *
import AddressBook

def relpath(path, start):
    """Return a relative version of a path"""

    if not path:
        raise ValueError("no path specified")

    start_list = os.path.abspath(start).split(os.path.sep)
    path_list = os.path.abspath(path).split(os.path.sep)

    # Work out how much of the filepath is shared by start and path.
    i = len(os.path.commonprefix([start_list, path_list]))

    rel_list = [os.path.pardir] * (len(start_list)-i) + path_list[i:]
    return os.path.join(*rel_list)

def create_roll_dir(lifedb_dir, roll_id):
    return os.path.join(lifedb_dir, str(roll_id))

def attachments_dir(lifedb_dir):
    return os.path.realpath(os.path.join(lifedb_dir, "../_att"))

def ti_to_tt(ti):
    tstamp = ti + kCFAbsoluteTimeIntervalSince1970
    tt = datetime.fromtimestamp(tstamp).timetuple()
    return (tstamp,tt)

def main():
    symlink_photos = (os.getenv("SYMLINK_PHOTOS") and True) or False
    book = AddressBook.ABAddressBook.sharedAddressBook()
    addrs = book.me().valueForProperty_(AddressBook.kABEmailProperty)
    myemail = addrs.valueAtIndex_(addrs.indexForIdentifier_(addrs.primaryIdentifier()))
    fname = book.me().valueForProperty_(AddressBook.kABFirstNameProperty)
    lname = book.me().valueForProperty_(AddressBook.kABLastNameProperty)
    name = "%s %s" % (fname, lname)
    from_info = { 'type': 'email', 'id' : myemail }
    home = os.getenv("HOME")
    base = os.path.join(home, "Pictures/iPhoto Library")
    idb = os.path.join(base, 'iPhotoMain.db')
    fdb = os.path.join(base, 'face.db')
    conn = sqlite3.connect('')
    c = conn.cursor()
    c.execute("attach database '%s' as i" % idb)
    c.execute("attach database '%s' as f" % fdb)
    sql = "select f.face_name.name,f.face_name.email,relativePath from i.SqFileInfo inner join i.SqFileImage on (i.SqFileImage.primaryKey = i.SqFileInfo.primaryKey) inner join i.SqPhotoInfo on (i.SqFileImage.photoKey = i.SqPhotoInfo.primaryKey) inner join f.detected_face on (f.detected_face.image_key = i.SqFileImage.photoKey) inner join f.face_name on (f.detected_face.face_key = f.face_name.face_key) where f.face_name.name != '' and relativePath=?"
    lifedb_dir = os.getenv("LIFEDB_DIR")
    fname = "%s/Pictures/iPhoto Library/AlbumData.xml" % os.getenv("HOME")
    pl = plistlib.readPlist(fname)

    version="%s.%s" % (pl['Major Version'], pl['Minor Version'])
    app_version = pl['Application Version']
    if not (app_version.startswith('8.0')):
        print >> sys.stderr, "This script only works with iPhoto 8.0, found version %s" % app_version
        exit(1)
    images = pl['Master Image List']
    keywords = pl['List of Keywords']
    rolls = pl['List of Rolls']

    for roll in rolls:
        roll_id = roll['RollID']
        roll_dir = create_roll_dir(lifedb_dir, roll_id)
        for img_id in roll['KeyList']:
            img = images[img_id]
            if 'OriginalPath' in img:
                img_path = img['OriginalPath']
            else:
                img_path = img['ImagePath']
            rel_path = (relpath(img_path, base),)
            root,ext = os.path.splitext(img_path)
            uid = img['GUID'] + ext
            guid = 'iPhoto:' + img['GUID']
            tstamp,tt = ti_to_tt(img['DateAsTimerInterval'])
            m = {'_type':'com.apple.iphoto', '_timestamp':tstamp, '_att': [uid], '_uid': guid }
            if 'Rating' in img:
                m['rating'] = img['Rating']
            if 'Comment' in img and img['Comment'] != '':
                m['comment'] = img['Comment']
            if 'Keywords' in img:
                kw = map(lambda x: keywords[x], img['Keywords'])
                m['_tags'] = kw
            if 'Caption' in img:
                m['caption'] = img['Caption']
            c.execute(sql, rel_path)
            m['_from'] = from_info
            m['_to'] = []
            for row in c:
               fname=row[0]
               email=row[1]
               if email:
                  m['_to'].append({'type':'email', 'id':email})
            output_dir = os.path.join(lifedb_dir, str(tt[0]), str(tt[1]), str(tt[2]))
            att_dir = attachments_dir(output_dir)
#            fin = open(img_path, 'rb')
#            try:
#               tags = EXIF.process_file(fin)
#            except:
#               pass
#            fin.close()
            if not os.path.isdir(output_dir):
                os.makedirs(output_dir)
            if not os.path.isdir(att_dir):
                os.makedirs(att_dir)
            oimgname = os.path.join(att_dir, uid)
            if symlink_photos:
                try:
                    os.unlink(oimgname)
                except:
                    pass
                os.symlink(img_path, oimgname)
            else:
                shutil.copyfile(img_path, oimgname)
            ofname = os.path.join(output_dir, guid+".lifeentry")
            fout = open(ofname, 'w')
            simplejson.dump(m, fout, indent=2)
#            print simplejson.dumps(m, indent=2)
            fout.close()
            print ofname

if __name__ == "__main__":
    main()
