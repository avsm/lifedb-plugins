#!/bin/sh 

if [ "$1" != "" ]; then
   LIFEDB_DIR=$1
fi

if [ "$LIFEDB_DIR" == "" ]; then
   echo Usage: $0 lifedbdir
   exit 1
fi

set -eu

MANIFEST=./dist/manifest.app/Contents/MacOS/manifest 
PARSE_DB=./dist/parse_db.app/Contents/MacOS/parse_db 
BASE="/Users/$USER/Library/Application Support/MobileSync/Backup/"
IPHONE_LIST=`ls -1 "${BASE}"`
TMPDIR=`mktemp -d -t sms.XXXXXXXXXX`
VERBOSE=-v

trap "rm -rf $TMPDIR; exit" INT TERM EXIT

for i in "${IPHONE_LIST}"; do
    fdir="${BASE}/${i}"
    if [ ! -d "${fdir}" ]; then
        echo skipping non-directory "${fdir}"
    fi
    tmpout="${TMPDIR}/${i}"
    echo $
    ${MANIFEST} ${VERBOSE} -x Library -o ${tmpout} "${fdir}"
    echo cd ${tmpout}
    ${PARSE_DB} -m call -o ${LIFEDB_DIR} -u ${i} ${tmpout}/Library/CallHistory/call_history.db
    ${PARSE_DB} -m sms -o ${LIFEDB_DIR} -u ${i} ${tmpout}/Library/SMS/sms.db
done
