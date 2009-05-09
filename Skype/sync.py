import Skype4Py
import simplejson
import datetime, time, sys, os
import util

def main():
    save_dir = os.getenv("LIFEDB_DIR")
    if not save_dir:
        print >> sys.stderr, "no LIFEDB_DIR in env"
        exit(1)

    skype = Skype4Py.Skype()
    skype.Attach()

    myHandle = skype.CurrentUserHandle

    calls = skype.Calls()
    for call in calls:
        tt = call.Datetime.timetuple()
        tstamp = time.mktime(tt)
        if call.Type == Skype4Py.cltIncomingPSTN or call.Type == Skype4Py.cltOutgoingPSTN:
            ctype = "PhoneCall"
        else:
            ctype = "Skype"
        m = { '_type' : 'com.skype', '_timestamp' : tstamp,
            'duration' : call.Duration, 'type' : call.Type,
            'status' : call.Status,
            '_from' : { 'type' : ctype, 'id' : call.PartnerHandle }, 
            '_to' : [ { 'type' : 'Skype', 'id' : myHandle } ]
          }
        if call.Participants:
            m['participants'] = map(lambda x: x.Handle, call.Participants)
       
        uid = "%s.%s.%s" % (call.Id, tstamp, myHandle)
        guid, subdir = util.split_to_guid(uid)
        dir = os.path.join(save_dir, subdir)
        fname = "%s.lifeentry" % guid
        m['_uid'] = guid
        full_fname = os.path.join(dir, fname)
        if not os.path.isfile(full_fname):
            if not os.path.isdir(dir):
                os.makedirs(dir)
            fout = open(full_fname, 'w')
            simplejson.dump(m, fout, indent=2)
            fout.close()
            print "Written: %s" % full_fname

if __name__ == "__main__":
   main()
