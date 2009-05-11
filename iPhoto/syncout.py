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

import os,sys,simplejson,tempfile,shutil,subprocess,sqlite3,glob
import util

osa_template="""
set AlbumName to "From %s"
set importDirectory to "%s"

tell application "iPhoto"
        if not (exists (album AlbumName)) then
                new album name AlbumName
        end if
        
        set theAlbum to album AlbumName
        import from importDirectory to theAlbum without force copy
        
        repeat while (importing)
                delay 0.5
        end repeat
        
        -- # DO STUFF TO PHOTOS LIKE ADD TITLE, DESCRIPTION AND KEYWORDS
        
end tell
"""


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

def process_file(file):
  fin = open(file, 'rb')
  j = simplejson.load(fin)
  fin.close()
  atts = j.get('_att', None)
  if not atts:
    print >> sys.stderr, "No attachments for %s" % file
  atts = map(lambda x: find_att(file, x), atts)
  frm = j['_from']['id']
  tags = j.get('_tags',[])
  print atts,frm,tags
  return (atts,frm,tags)

def create_osascript(c, uidmapdir, tmpdir, entries):
  print >> sys.stderr, "tempdir: %s" % tmpdir
  # group all the froms into a temporary directory of their own
  frms = {}
  for (atts,frm,tags) in entries:
    frmtmp = os.path.join(tmpdir, frm)
    for att in atts:
      attdir, attfname = os.path.split(att)
      dst = os.path.join(frmtmp, attfname)
      if not os.path.isdir(frmtmp):
        os.makedirs(frmtmp)
      if not frms.get(frm, None):
        frms[frm] = frmtmp
      os.symlink(att, dst)
      print >> sys.stderr, "symlink: %s -> %s" % (att,dst)
  err=False
  for frm,frmdir in frms.items():
    osa = osa_template % (frm, frmdir)
    p = subprocess.Popen("/usr/bin/osascript", shell=True, stdin=subprocess.PIPE, close_fds=True)
    p.stdin.write(osa)
    p.stdin.close()
    pid, sts = os.waitpid(p.pid, 0)
    ecode = os.WEXITSTATUS(sts)
    if ecode != 0:
       err = True
    # now retrieve the UIDs we just injected into iPhoto back
    innames = map(os.path.basename, glob.glob(frmdir + "/*"))
    for fname in innames:
      # fname is of form guid.jpg
      sql = "select uid from SqFileInfo inner join SqFileImage on (SqFileInfo.primaryKey = SqFileImage.primaryKey) inner join SqPhotoInfo on (SqFileImage.photoKey = SqPhotoInfo.primaryKey)  where relativePath like \"Originals/%%/%s\"" % fname;
      c.execute(sql)
      newuid=None
      for row in c:
        if newuid:
          print >> sys.stderr, "unexpected multiple results in UID query: %s %s" % (newuid, row)
          exit(1)
        newuid = row[0]
      if newuid:
        # fname is of form guid.jpg, so split out the extension and convert the guid to lifedb
        origuid = util.split_to_guid(os.path.splitext(fname)[0])[0]
        # newuid is of form "uuid" so convert it into the lifedb uid format
        newlifeuid = util.split_to_guid(newuid)[0]
        fout = open(os.path.join(uidmapdir, newlifeuid), 'w')
        fout.write(origuid)
        fout.close()
        print >> sys.stderr, "UIDMap: %s -> %s" % (newuid, origuid)
  return err

def main():
  files = sys.argv[1:]
  home = os.getenv("HOME")
  if not home:
    print >> sys.stderr, "HOME not set in environment"
    exit(1)
  uidmapdir = os.getenv("LIFEDB_UID_MAP")
  if not uidmapdir:
    print >> sys.stderr, "LIFEDB_UID_MAP not set in environment"
    exit(1)
  # connect to iPhoto Sqlite DB
  base = os.path.join(home, "Pictures/iPhoto Library")
  idb = os.path.join(base, 'iPhotoMain.db')
  conn = sqlite3.connect(idb)
  c = conn.cursor()
  
  entries = map(process_file, files)
  tmpdir = tempfile.mkdtemp(prefix="iphotosync")
  err = create_osascript(c, uidmapdir, tmpdir, entries)

  shutil.rmtree(tmpdir)
  if err:
    exit(1)

if __name__ == "__main__":
  main ()
