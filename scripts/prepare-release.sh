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
import sys

path = Path("EasyBox.manifest")
manifest = json.loads(path.read_text())
manifest["version"] = sys.argv[1]
path.write_text(json.dumps(manifest, ensure_ascii=False, indent="\t") + "\n")
PYTHON

mkdir "$stage/EasyBox"
cp -R commands docs lib EasyBox.manifest ./*.py LICENSE README.md "$stage/EasyBox/"
(cd "$stage" && zip -rq "$stage/release.zip" EasyBox)
mv "$stage/release.zip" "$output"
