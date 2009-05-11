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

import os

def split_len(seq, length):
    return [seq[i:i+length] for i in range(0, len(seq), length)]

def split_to_guid(uid):
    uid = unicode.replace(unicode(uid), '-', '').lower()
    bits = split_len(uid, 2)[0:2]
    pth = os.path.join(*bits)
    guid = "Adium:" + uid
    return (guid, pth)
