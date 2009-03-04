#!/bin/sh

if [ "$1" != "" ]; then
   LIFEDB_DIR=$1
fi

if [ "$LIFEDB_DIR" == "" ]; then
   echo Usage: $0 lifedbdir
   exit 1
fi

set -eu

SUFFIX=/Phone
PYTHON=/usr/bin/python
BASE="/Users/$USER/Library/Application Support/MobileSync/Backup/"
IPHONE_LIST=`ls -1 "${BASE}"`
TMPDIR=`mktemp -d -t sms.XXXXXXXXXX`
trap "rm -rf $TMPDIR; exit" INT TERM EXIT

for i in "${IPHONE_LIST}"; do
    fdir="${BASE}/${i}"
    if [ ! -d "${fdir}" ]; then
        echo skipping non-directory "${fdir}"
    fi
    tmpout="${TMPDIR}/${i}"
    ${PYTHON} ./manifest.py -x Library -o ${tmpout} "${fdir}"
    ${PYTHON} ./parse_db.py -m sms -o ${LIFEDB_DIR}${SUFFIX} -u ${i} ${tmpout}/Library/SMS/sms.db
    ${PYTHON} ./parse_db.py -m call -o ${LIFEDB_DIR}${SUFFIX} -u ${i} ${tmpout}/Library/CallHistory/call_history.db
done
