#!/bin/sh
# Wrapper script to run offlineimap in daemon mode

if [ "${LIFEDB_DIR}" = "" ]; then
     echo LIFEDB_DIR not set
     exit 1
fi

if [ "${LIFEDB_USERNAME}" = "" ]; then
     echo LIFEDB_USERNAME not set
     exit 1
fi

if [ "${LIFEDB_PASSWORD}" = "" ]; then
     echo LIFEDB_PASSWORD not set
     exit 1
fi

if [ "${LIFEDB_CACHE_DIR}" = "" ]; then
     echo LIFEDB_CACHE_DIR not set
     exit 1
fi

if [ "${USE_SSL}" = "" ]; then
     echo USE_SSL not set
     exit 1
fi

if [ "${IMAP_SERVER}" = "" ]; then
     echo IMAP_SERVER not set
     exit 1
fi

# need newer python than base due to MemoryError issue
PYTHON=/opt/local/bin/python2.5

if [ ! -x "${PYTHON}" ]; then
    echo ${PYTHON}: not found
    exit 1
fi

CONFIG_IN="./config/offlineimap.conf-maildir.in"
CONFIG_OUT=${LIFEDB_CACHE_DIR}/offlineimap.conf
mkdir -p ${LIFEDB_CACHE_DIR}

sed -e "s,@OBJ@,${LIFEDB_CACHE_DIR},g" -e "s,@LIFEDB_DIR@,${LIFEDB_DIR},g" \
    -e "s,@IMAPSERVER@,${IMAP_SERVER},g" -e "s,@IMAPUSER@,${LIFEDB_USERNAME},g" \
    -e "s,@IMAPPASSWD@,${LIFEDB_PASSWORD},g" -e "s,@USE_SSL@,${USE_SSL},g" \
       < ${CONFIG_IN} > ${CONFIG_OUT}

PYTHONPATH=./offlineimap/build/lib:$PYTHONPATH 
export PYTHONPATH
${PYTHON} ./offlineimap/build/scripts-2.5/offlineimap -u Noninteractive.Basic -c ${CONFIG_OUT}

