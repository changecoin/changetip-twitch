#!/bin/bash
for f in `find ./ -name '*py' | grep -v test `; do
    pyflakes $f
    if [ "$?" != "0" ] ; then
        echo "$f does not pass lint check"
        exit 1
    fi
done
exit 0
