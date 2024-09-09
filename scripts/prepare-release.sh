#!/bin/bash

NEXT_VERSION=$1
ZIP_FILENAME=$2

if [ -z ${NEXT_VERSION} || -z ${ZIP_FILENAME} ]; then
    echo "Usage: $0 <next version> <zip filename>"
    exit 1
fi

# Update version in manifest file
sed -i '' -e "s/\"version\":\t\".*\"/\"version\":\t\"${NEXT_VERSION}\"/" *.manifest

echo "[semantic-release] [prepare-release] ✔ Manifest version updated to ${NEXT_VERSION}"

# Create zip file
zip -rq ${ZIP_FILENAME} \
    commands \
    docs \
    lib \
    *.manifest \
    *.py \
    LICENSE \
    README.md

echo "[semantic-release] [prepare-release] ✔ ${ZIP_FILENAME} created"
