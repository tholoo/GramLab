# Native ordinary-document codec probe

This GPL-2.0-or-later diagnostic loads the reviewed Android APK's actual `GramLabDocument`,
`TLRPC`, `NativeByteBuffer`, `ImageLocation`, and `FileLoader` classes. The applicable license is
[the Android adapter GPL text](../../../clients/android/patches/COPYING). The root MIT license does
not relicense this adapter-bound fixture.

The independently authored cases exercise strict descriptor parsing, numeric ordering, the complete
ordinary `TL_document` carrier, original serialization and attachment keys, the negative ordinary-ID
namespace, and the positive custom-emoji namespace. The fixture calls the real codec only through
reflection and does not contain a substitute TLRPC implementation. It loads the original x86_64
native library extracted from the reviewed client APK solely to exercise `NativeByteBuffer`.
Failure records name the exact reflection stage and retain bounded cause and relevant-stack details.
A client that lacks the codec emits the same structured one-case bootstrap summary to stdout and
`summary.json` before native loading; successful clients retain the original 34-case result shape.

Compile the fixture using only cached inputs in this checkout's pinned Android shell:

```sh
tools/dev android --offline --command bash \
  tests/fixtures/android_document_codec/compile.sh \
  .cache/android-document-codec-probe-RUN
```

Set `GRAMLAB_ANDROID_RUNTIME_PROFILE`, `GRAMLAB_ANDROID_PROBE_APK`, and
`GRAMLAB_ANDROID_DOCUMENT_CODEC_PROBE_APK`, then run through the shared Android lock and mandatory
outer network guard:

```sh
tools/worktree lock android-gate tools/dev android --command \
  unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/pytest -q \
  tests/test_android_document_codec.py::test_actual_document_codec_uses_original_native_carriers'
```

The pre-0029 APK must fail because `GramLabDocument` is absent. The post-0029 APK must pass all
cases. This proves only descriptor projection and native serialization; it does not prove bridge-v5
negotiation, dependency installation, file loading, rendering, download, or cache persistence.
