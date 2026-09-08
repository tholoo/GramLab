#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
set -euo pipefail
if [[ $# != 4 ]]; then
  echo 'Usage: compile-instrumentation.sh ORIGINAL_CLASSES_JAR ORIGINAL_APK DEBUG_KEYSTORE NEW_OUTPUT_DIRECTORY' >&2
  exit 2
fi
probe_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
classes_jar=$(realpath -- "$1")
original_apk=$(realpath -- "$2")
debug_keystore=$(realpath -- "$3")
output=$(realpath -m -- "$4")
[[ -f "$classes_jar" && -f "$original_apk" && -f "$debug_keystore" && ! -e "$output" ]]
tool_root="${ANDROID_HOME:?Enter the pinned Android development shell}/build-tools/36.0.0"
android_jar="$ANDROID_HOME/platforms/android-36/android.jar"
mkdir -- "$output"
bash "$probe_root/compile.sh" "$classes_jar" "$original_apk" "$output/bytecode" > "$output/bytecode.log"
ndk_root="$ANDROID_HOME/ndk/27.2.12479018/toolchains/llvm/prebuilt/linux-x86_64"
for target in 'x86_64:x86_64-linux-android26' 'x86:i686-linux-android26' \
              'arm64-v8a:aarch64-linux-android26' 'armeabi-v7a:armv7a-linux-androideabi26'; do
  abi=${target%%:*}
  compiler="$ndk_root/bin/${target#*:}-clang"
  mkdir -p -- "$output/lib/$abi"
  "$compiler" -std=c11 -Wall -Wextra -Werror -fPIC -shared -Wl,-z,max-page-size=16384 \
    "$probe_root/RenameNoReplaceProbe.c" -o "$output/lib/$abi/libdocument_rename_probe.so"
  "$ndk_root/bin/llvm-readelf" --file-header --dyn-syms "$output/lib/$abi/libdocument_rename_probe.so" \
    > "$output/lib/$abi/elf.txt"
done
"$tool_root/aapt2" link -I "$android_jar" --manifest "$probe_root/AndroidManifest.xml" \
  --min-sdk-version 26 --target-sdk-version 36 -o "$output/unsigned.apk"
python3 - "$output" <<'PYCODE'
from pathlib import Path
import sys
import zipfile
root = Path(sys.argv[1])
with zipfile.ZipFile(root / 'unsigned.apk', 'a') as archive:
    entry = zipfile.ZipInfo('classes.dex', (2000, 1, 1, 0, 0, 0))
    archive.writestr(entry, (root / 'bytecode/dex/classes.dex').read_bytes())
    for library in sorted((root / 'lib').glob('*/*.so')):
        entry = zipfile.ZipInfo(library.relative_to(root).as_posix(), (2000, 1, 1, 0, 0, 0))
        archive.writestr(entry, library.read_bytes())
PYCODE
"$tool_root/zipalign" -p 4 "$output/unsigned.apk" "$output/aligned.apk"
# This is the existing dedicated, publicly configured local debug identity, never a release key.
"$tool_root/apksigner" sign --ks "$debug_keystore" --ks-key-alias gramlab-debug \
  --ks-pass pass:android --key-pass pass:android --out "$output/probe.apk" "$output/aligned.apk"
"$tool_root/apksigner" verify --print-certs "$original_apk" > "$output/original-certificate.txt"
"$tool_root/apksigner" verify --print-certs "$output/probe.apk" > "$output/probe-certificate.txt"
python3 - "$output" "$probe_root" "$tool_root" "$ndk_root" <<'PYCODE'
import hashlib
import json
from pathlib import Path
import re
import sys
output, source, tools, ndk = map(Path, sys.argv[1:])
def certificate(path):
    matches = re.findall(r'^Signer #1 certificate SHA-256 digest: ([0-9a-f]{64})$', path.read_text(), re.M)
    if len(matches) != 1:
        raise ValueError('Exactly one verified debug signer is required')
    return matches[0]
cert = certificate(output / 'original-certificate.txt')
if certificate(output / 'probe-certificate.txt') != cert:
    raise ValueError('Instrumentation signer differs from the original target APK')
metadata = json.loads((output / 'bytecode/inputs.json').read_text())
metadata['signer_certificate_sha256'] = cert
metadata['execution'] = 'target_instrumentation'
metadata['rename_probe'] = {'ndk': '27.2.12479018', 'api': 26, 'runtime_verified': False,
    'arguments': ['-std=c11', '-Wall', '-Wextra', '-Werror', '-fPIC', '-shared', '-Wl,-z,max-page-size=16384'],
    'architectures': ['arm64-v8a', 'armeabi-v7a', 'x86', 'x86_64']}
for abi, target in {'x86_64': 'x86_64-linux-android26', 'x86': 'i686-linux-android26',
                    'arm64-v8a': 'aarch64-linux-android26', 'armeabi-v7a': 'armv7a-linux-androideabi26'}.items():
    evidence = (output / 'lib' / abi / 'elf.txt').read_text()
    if not re.search(r'UND syscall@LIBC', evidence) or re.search(r'UND renameat2', evidence):
        raise ValueError('Expected API26 syscall ABI without API30 renameat2 dependency')
    for name, path in {'library': output / 'lib' / abi / 'libdocument_rename_probe.so',
                       'elf': output / 'lib' / abi / 'elf.txt',
                       'compiler': (ndk / 'bin' / (target + '-clang')).resolve()}.items():
        metadata['files']['rename_' + abi + '_' + name] = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
for name, path in {
    'probe_apk': output / 'probe.apk',
    'rename_c': source / 'RenameNoReplaceProbe.c',
    'ndk_stdio_header': ndk / 'sysroot/usr/include/stdio.h',
    'ndk_syscall_header': ndk / 'sysroot/usr/include/sys/syscall.h',
    'ndk_syscall_definitions': ndk / 'sysroot/usr/include/bits/glibc-syscalls.h',
    'ndk_readelf': (ndk / 'bin/llvm-readelf').resolve(),
    'instrumentation_manifest': source / 'AndroidManifest.xml',
    'instrumentation_compile_script': source / 'compile-instrumentation.sh',
    'aapt2': tools / 'aapt2',
    'zipalign': tools / 'zipalign',
    'apksigner': tools / 'lib/apksigner.jar',
}.items():
    metadata['files'][name] = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
(output / 'inputs.json').write_text(json.dumps(metadata, indent=2) + '\n')
print(json.dumps(metadata, indent=2))
PYCODE
