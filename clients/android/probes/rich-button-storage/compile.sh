#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
set -euo pipefail
if [[ $# != 3 ]]; then
  echo 'Usage: compile.sh ORIGINAL_CLASSES_JAR ORIGINAL_APK NEW_OUTPUT_DIRECTORY' >&2
  exit 2
fi
probe_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
classes_jar=$(realpath -- "$1")
original_apk=$(realpath -- "$2")
output=$(realpath -m -- "$3")
[[ -f "$classes_jar" && -f "$original_apk" && ! -e "$output" ]]
android_jar="${ANDROID_HOME:?Enter the pinned Android development shell}/platforms/android-36/android.jar"
d8_jar="$ANDROID_HOME/build-tools/36.0.0/lib/d8.jar"
[[ -f "$android_jar" && -f "$d8_jar" ]]
original_inputs=$(sha256sum -- "$classes_jar" "$original_apk")
mkdir -p -- "$output/classes" "$output/dex"
javac --release 8 -Xlint:all -Werror -classpath "$android_jar:$classes_jar" \
  -d "$output/classes" "$probe_root/RichButtonStorageProbe.java"
jar --create --file "$output/probe-classes.jar" -C "$output/classes" .
d8 --min-api 26 --lib "$android_jar" --classpath "$classes_jar" \
  --output "$output/dex" "$output/probe-classes.jar"
[[ "$original_inputs" == "$(sha256sum -- "$classes_jar" "$original_apk")" ]]
python3 - "$output" "$probe_root" "$classes_jar" "$original_apk" "$android_jar" "$d8_jar" "$(command -v javac)" <<'PYCODE'
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile
output, source, classes, apk, android, d8, javac = map(Path, sys.argv[1:])
with zipfile.ZipFile(output / 'probe.apk', 'w') as archive:
    entry = zipfile.ZipInfo('classes.dex', (2000, 1, 1, 0, 0, 0))
    archive.writestr(entry, (output / 'dex/classes.dex').read_bytes())
files = {'source': source / 'RichButtonStorageProbe.java', 'compiler': javac.resolve(),
         'd8': d8, 'android_api': android, 'original_classes': classes, 'original_apk': apk,
         'probe_dex': output / 'dex/classes.dex', 'probe_apk': output / 'probe.apk'}
metadata = {'schema': 1, 'javac_version': subprocess.check_output([str(javac), '-version'], text=True).strip(),
            'files': {name: {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                      for name, path in files.items()}}
(output / 'inputs.json').write_text(json.dumps(metadata, indent=2) + '\n')
print(json.dumps(metadata, indent=2))
PYCODE
