#!/bin/sh

if [ "$TMPFILELOC" != "" ]; then echo "foo" >> $TMPFILELOC; fi

if [ "$WANTSLEEP" != "" ]; then sleep $WANTSLEEP; fi
