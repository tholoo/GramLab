#!/system/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
# Coordinator invokes this inside the already contained dedicated guest as app UID.
set -eu
if [ "$#" -ne 5 ]; then
  echo 'Usage: run-on-guest.sh PROBE_APK ORIGINAL_APK NATIVE_LIBRARY FRESH_PRIVATE_OUTPUT baseline|suite' >&2
  exit 2
fi
export CLASSPATH="$1:$2"
exec /system/bin/app_process /system/bin org.telegram.gramlab.RichButtonStorageProbe "$3" "$4" "$5"
