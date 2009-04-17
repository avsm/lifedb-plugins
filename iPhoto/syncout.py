import os,sys,simplejson,tempfile,shutil,subprocess

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

def create_osascript(tmpdir, entries):
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
  return err

def main():
  files = sys.argv[1:]
  entries = map(process_file, files)
  tmpdir = tempfile.mkdtemp(prefix="iphotosync")
  err = create_osascript(tmpdir, entries)
  shutil.rmtree(tmpdir)
  if err:
    exit(1)

if __name__ == "__main__":
  main ()
