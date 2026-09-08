#!/system/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
set -eu
if [ "$#" -ne 3 ]; then
  echo 'Usage: run-on-guest.sh PROBE_APK NORMAL27_APK FRESH_PRIVATE_OUTPUT' >&2
  exit 2
fi
export CLASSPATH="$1:$2"
exec /system/bin/app_process /system/bin org.telegram.gramlab.RichButtonMatrixProbe "$3"
