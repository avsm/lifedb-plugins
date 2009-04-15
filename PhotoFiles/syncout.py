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
