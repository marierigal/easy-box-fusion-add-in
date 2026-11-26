#!/usr/bin/env bash
set -euo pipefail
version=${1:?Expected next version}
output=${2:?Expected ZIP filename}
output="$(pwd)/$output"
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT

python3 - "$version" <<'PYTHON'
import json
from pathlib import Path
import re
import sys

path = Path("EasyBox.manifest")
text = path.read_text()
updated, count = re.subn(r'("version"\s*:\s*)"[^"]*"', lambda m: m[1] + json.dumps(sys.argv[1]), text)
if count != 1 or json.loads(updated)["version"] != sys.argv[1]:
    raise ValueError("Expected one manifest version")
path.write_text(updated)
PYTHON

mkdir "$stage/EasyBox"
cp -R commands docs lib EasyBox.manifest ./*.py LICENSE README.md "$stage/EasyBox/"
(cd "$stage" && zip -rq "$stage/release.zip" EasyBox)
mv "$stage/release.zip" "$output"
