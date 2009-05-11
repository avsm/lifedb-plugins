# Copyright (C) 2009 Anil Madhavapeddy <anil@recoil.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

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
import md5
import tempfile,filecmp
import util

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
    uidmapdir = os.getenv("LIFEDB_UID_MAP") or exit(3)
    lifedb_dir = os.getenv("LIFEDB_DIR") or exit(4)
    home = os.getenv("HOME") or exit(5)
    book = AddressBook.ABAddressBook.sharedAddressBook()
    addrs = book.me().valueForProperty_(AddressBook.kABEmailProperty)
    myemail = addrs.valueAtIndex_(addrs.indexForIdentifier_(addrs.primaryIdentifier()))
    fname = book.me().valueForProperty_(AddressBook.kABFirstNameProperty)
    lname = book.me().valueForProperty_(AddressBook.kABLastNameProperty)
    name = "%s %s" % (fname, lname)
    from_info = { 'type': 'email', 'id' : myemail }
    base = os.path.join(home, "Pictures/iPhoto Library")
    idb = os.path.join(base, 'iPhotoMain.db')
    fdb = os.path.join(base, 'face.db')
    conn = sqlite3.connect('')
    c = conn.cursor()
    c.execute("attach database '%s' as i" % idb)
    c.execute("attach database '%s' as f" % fdb)
    sql = "select f.face_name.name,f.face_name.email,relativePath from i.SqFileInfo inner join i.SqFileImage on (i.SqFileImage.primaryKey = i.SqFileInfo.primaryKey) inner join i.SqPhotoInfo on (i.SqFileImage.photoKey = i.SqPhotoInfo.primaryKey) inner join f.detected_face on (f.detected_face.image_key = i.SqFileImage.photoKey) inner join f.face_name on (f.detected_face.face_key = f.face_name.face_key) where f.face_name.name != '' and relativePath=?"
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
            guid, output_subdir = util.split_to_guid(img['GUID'])
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
            m['file_path'] = relpath(img_path, base)
            c.execute(sql, rel_path)
            m['_from'] = from_info
            m['_to'] = []
            for row in c:
               fname=row[0]
               email=row[1]
               if email:
                  m['_to'].append({'type':'email', 'id':email})
            output_dir = os.path.join(lifedb_dir, output_subdir)
            ofname = os.path.join(output_dir, m['_uid']+".lifeentry")

            # check if the UID exists in the UID_MAP_DIR
            uidmapfile = os.path.join(uidmapdir, guid)
            if os.path.isfile(uidmapfile):
                fin = open(uidmapfile, 'r')
                origuid = fin.read()
                fin.close()
                uid = origuid
                print >> sys.stderr, "remapping UID: %s -> %s" % (m['_uid'], uid)
                m['_uid'] = uid
                output_dir = os.path.dirname(os.path.realpath(ofname))
                ofname = os.path.join(output_dir, m['_uid']+".lifeentry")
            att_dir = attachments_dir(output_dir)
            oimgname = os.path.join(att_dir, uid)

            if not os.path.isdir(output_dir):
                os.makedirs(output_dir)
            if not os.path.isdir(att_dir):
                os.makedirs(att_dir)

#            fin = open(img_path, 'rb')
#            try:
#               tags = EXIF.process_file(fin)
#            except:
#               pass
#            fin.close()

            if symlink_photos:
                try:
                    os.unlink(oimgname)
                except:
                    pass
                os.symlink(img_path, oimgname)
            else:
                shutil.copyfile(img_path, oimgname)

            fd, tmpname = tempfile.mkstemp(suffix=".lifeentry")
            fout = os.fdopen(fd, 'w')
            simplejson.dump(m, fout, indent=2)
            fout.close()
            if (not os.path.isfile(ofname)) or (not filecmp.cmp(tmpname, ofname)):
              print "NEW: %s" % ofname
              os.rename(tmpname, ofname)
            else:
              print "SKIP: %s" % ofname
              os.unlink(tmpname)

if __name__ == "__main__":
    main()
