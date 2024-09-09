#!/bin/bash

ZIP_FILENAME=$1

if [ -z ${ZIP_FILENAME} ]; then
    echo "Usage: $0 <zip filename>"
    exit 1
fi

# Create zip file
zip -r ${ZIP_FILENAME} \
    commands \
    docs \
    lib \
    *.manifest \
    *.py \
    LICENSE \
    README.md

echo ${ZIP_FILENAME} created
