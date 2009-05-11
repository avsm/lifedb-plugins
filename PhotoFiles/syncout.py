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

import os,sys,simplejson,tempfile,shutil

def find_att(entry, uid):
  dir,file = os.path.split(entry)
  found=None
  while len(dir) > 1 and (not found):
     dir,x = os.path.split(dir)
     attdir = os.path.join(dir,"_att")
     attfile = os.path.join(attdir, uid)
     if os.path.isfile(attfile):
       found=attfile
  return found

def process_file(base, file):
  print >> sys.stderr, "Processing %s" % file
  fin = open(file, 'rb')
  j = simplejson.load(fin)
  fin.close()
  atts = j.get('_att', None)
  if not atts:
    print >> sys.stderr, "No attachments for %s" % file
  atts = map(lambda x: find_att(file, x), atts)
  frm = j['_from']['id']
  subdir = j.get('file_path',None)
  if not subdir:
    subdir = frm + "/misc/" + j['_uid']
  else:
    subdir = frm + "/" + subdir
  # XXX ensure there is no ../ in the file_path
  for att in atts:
    ofname = os.path.join(base, subdir)
    ofdir = os.path.dirname(ofname)
    if not os.path.isdir(ofdir):
      os.makedirs(ofdir)
    print >> sys.stderr, "copying: %s -> %s" % (att, ofname)
    shutil.copyfile(att, ofname)
    print "NEW: %s" % ofname

def main():
  base = os.getenv("PHOTO_FILES_DIR")
  if not base or (not os.path.isdir(base)):
    print >> sys.stderr, "PHOTO_FILES_DIR not set or dir doesnt exist"
    exit(1)
  files = sys.argv[1:]
  entries = map(lambda x: process_file(base, x), files)
  
if __name__ == "__main__":
  main ()
