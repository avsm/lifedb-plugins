import plistlib
import os, sys, shutil
import simplejson
import EXIF
from datetime import datetime
import time
import AddressBook
import md5
import dateutil.parser

def relpath(path, start):
    """Return a relative version of a path"""

    if not path:
        raise ValueError("no path specified")

    start_list = os.path.abspath(start).split(os.path.sep)
    path_list = os.path.abspath(path).split(os.path.sep)

    # Work out how much of the filepath is shared by start and path.
    i = len(os.path.commonprefix([start_list, path_list]))

    rel_list = [os.path.pardir] * (len(start_list)-i) + path_list[i:]
    if not rel_list:
      rel_list=[""]
    return os.path.join(*rel_list)

def create_roll_dir(lifedb_dir, roll_id):
    return os.path.join(lifedb_dir, str(roll_id))

def attachments_dir(lifedb_dir):
    return os.path.realpath(os.path.join(lifedb_dir, "../_att"))

def main():
    symlink_photos = (os.getenv("SYMLINK_PHOTOS") and True) or False
    book = AddressBook.ABAddressBook.sharedAddressBook()
    addrs = book.me().valueForProperty_(AddressBook.kABEmailProperty)
    myemail = addrs.valueAtIndex_(addrs.indexForIdentifier_(addrs.primaryIdentifier()))
    fname = book.me().valueForProperty_(AddressBook.kABFirstNameProperty)
    lname = book.me().valueForProperty_(AddressBook.kABLastNameProperty)
    name = "%s %s" % (fname, lname)
    from_info = { 'type': 'email', 'id' : myemail }
    base = os.getenv("PHOTO_FILES_DIR")
    if not base or (not os.path.isdir(base)):
      print >> sys.stderr, "PHOTO_FILES_DIR not set or dir doesnt exist"
      exit(1)
    lifedb_dir = os.getenv("LIFEDB_DIR")
    if not lifedb_dir:
      print >> sys.stderr, "LIFEDB_DIR not set"
      exit(1)
    for root, dirs, files in os.walk(base):
      for f in files:
        skip = False
        fname = os.path.join(root, f)
        root_name,ext = os.path.splitext(fname)
        fin = open(fname, 'rb')
        try:
          exif_tags = EXIF.process_file(fin)
        except:
          print >> sys.stderr, "error reading: %s" % fname
          skip = True
        finally:
          fin.close()
        if skip or (exif_tags == {}):
          continue
        if exif_tags.has_key('EXIF DateTimeOriginal'):
          raw = str(exif_tags['EXIF DateTimeOriginal'])
          tm = dateutil.parser.parse(raw)
          tt = tm.timetuple()
        else:
          tt = datetime.fromtimestamp(os.path.getmtime(fname)).timetuple()
        tstamp = time.mktime(tt)
        guid = md5.new(file(fname).read()).hexdigest()
        uid = guid + ext
        m = { '_type':'com.clinklabs.photofiles', '_timestamp':tstamp, '_att': [uid], '_uid': guid, '_from': from_info, '_to':[] }
        rpath = relpath(root,base)
        m['caption'] = os.path.join(rpath, os.path.basename(fname))
        output_dir = os.path.join(lifedb_dir, rpath)
        ofname = os.path.join(output_dir, os.path.basename(fname) + ".lifeentry")
        if not os.path.isdir(output_dir):
          os.makedirs(output_dir)
        att_dir = attachments_dir(output_dir)
        if not os.path.isdir(att_dir):
          os.makedirs(att_dir)
 
        oimgname = os.path.join(att_dir, uid)
        if symlink_photos:
          try:
            os.unlink(oimgname)
          except:
            pass
          os.symlink(fname, oimgname)
        else:
          shutil.copyfile(fname, oimgname)

        fout = open(ofname, 'w')
        try:
          simplejson.dump(m, fout, indent=2)
          print "NEW: %s" % ofname
        except:
          print >> sys.stderr, "error writing %s" % ofname
        finally:
          fout.close()

if __name__ == "__main__":
    main()
