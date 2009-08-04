#!/bin/sh

if [ "${LIFEDB_DIR}" = "" ]; then
     echo LIFEDB_DIR not set
     exit 1
fi

./dist/sync.app/Contents/MacOS/sync
