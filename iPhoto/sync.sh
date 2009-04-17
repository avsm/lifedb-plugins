#!/bin/sh
set -x
export PYTHONPATH=../obj/py/lib/python2.5/site-packages:$PYTHONPATH
if [ "${LIFEDB_SYNC_DIR}" = "out" ]; then
  /usr/bin/python2.5 syncout.py $*
else
  /usr/bin/python2.5 syncin.py
fi
