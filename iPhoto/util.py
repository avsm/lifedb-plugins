import os

def split_len(seq, length):
    return [seq[i:i+length] for i in range(0, len(seq), length)]

def split_to_guid(uid):
    uid = str.replace(uid, '-', '').lower()
    bits = split_len(uid, 2)[0:2]
    pth = os.path.join(*bits)
    guid = "iPhoto:" + uid
    return (guid, pth)
