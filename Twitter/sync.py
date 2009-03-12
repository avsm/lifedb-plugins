import sys
import twitter
import dateutil.parser
import time
import os
import os.path
import simplejson

save_extension = "lifeentry"

# XXX to make this really robust against failure, need to save
# the chunk of tweets to a temp directory and move them into the
# save directory in oldest-first order so that the seen flag is
# set correctly on resume

def urlid(name):
   return "http://twitter.com/%s" % name

def save_stats(save_dir, st, mode="from"):
   seen = False
   for s in st:
      time_parsed = dateutil.parser.parse(s['created_at'])
      tt = time_parsed.timetuple()
      dir = os.path.join(save_dir,str(tt[0]),str(tt[1]),str(tt[2]))
      fname = "%s.%s" % (s['id'], save_extension)
      full_fname = os.path.join(dir, fname)
      if not os.path.isfile(full_fname):
          if not os.path.isdir(dir):
              os.makedirs(dir)
          time_float = time.mktime(tt)
          s['_timestamp'] = time_float
          s['_type'] = 'com.twitter'
          if mode == "from":
              s['_from'] = { 'type': 'twitter', 'id': urlid(s['user']['screen_name']) }
              if 'in_reply_to_screen_name' in s and s['in_reply_to_screen_name']:
                  s['_to'] = [ { 'type' : 'Twitter', 'id': urlid(s['in_reply_to_screen_name']) } ]
          else:
              s['_from'] = { 'type' : 'twitter', 'id': urlid(s['from_user']) }
              s['_to'] = [ { 'type' : 'twitter', 'id': urlid(s['to_user']) } ]
          fout = open(full_fname, 'w')
          simplejson.dump(s, fout, indent=2)
          fout.close()   
          print "Written: (%s) %s" % (s['_from']['id'] , full_fname)
      else:
          seen = True
   return seen

def retryOnError(label, c):
   tries = 0
   while True:
      print "attempt #%d: %s" % (tries, label)
      try:
          return (c ())
      except twitter.api.TwitterError, e:
          print "   error: %s" % str(e)
          tries = tries + 1
          if tries > 6:
              raise e
          time.sleep(60 * 20)  # sleep for 20 minutes
         
def main():
    user = os.getenv('LIFEDB_USERNAME')
    password = os.getenv('LIFEDB_PASSWORD')
    save_dir = os.getenv('LIFEDB_DIR') + "/Twitter"
    t = twitter.Twitter(user, password)
    tsearch = twitter.Twitter(user, password, domain="search.twitter.com")
    friends = [user]
    pg = 1
    while True:
        fs = retryOnError("search", lambda: tsearch.search(rpp=90, page=pg, to=user))
        if len(fs) == 0:
            break;
        if save_stats(save_dir, fs['results'], mode="to"):
            break;
        pg = pg + 1
  
    get_all_friends_tweets = False
    if os.getenv('FULL_SYNC') == "1":
        get_all_friends_tweets = True
    if get_all_friends_tweets:
        pg = 1
        while True:
          fs = retryOnError("get_friends", lambda: t.statuses.friends(page=pg))
          for f in retryOnError("get_friends_page_%d" % pg, lambda: t.statuses.friends(page=pg)):
              friends.append(f['screen_name'])
          if len(fs) == 0:
              break
          pg = pg + 1
    for friend in friends:
        pg = 1
        while True:
            st = retryOnError("timeline_%s_%d" % (friend,pg), lambda: t.statuses.user_timeline(id=friend, page=pg, count=200))
            if len(st) == 0:
                break
            if save_stats(save_dir, st, mode="from"):
                break
            pg = pg + 1        
        
if __name__ == "__main__":
    main()
