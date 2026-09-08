# Native rich-button matrix regression

This GPL-2.0-or-later probe invokes normal27's private coordinate helper reflectively while using
Android's actual `Canvas`, `Matrix`, and `RectF`. It allocates two `ChatMessageCell` identities
without constructors through Android's `sun.misc.Unsafe`; no view, application, account, transport,
renderer, or input lifecycle starts. It therefore proves the helper's matrix arithmetic and context
identity rules, not visible rendering, focus, hit testing, or touch behavior.

Compile from the pinned Android shell against matching reviewed normal27 inputs:

```sh
tools/dev android --offline --command bash \
  clients/android/probes/rich-button-matrix/compile.sh \
  /absolute/path/to/normal27-classes.jar \
  /absolute/path/to/normal27.apk \
  .cache/rich-button-matrix-RUN
```

The script performs only `javac`, `jar`, and D8 work with cached inputs. `inputs.json` records exact
source, compiler, Android API, D8, classes, APK, DEX and probe-APK hashes. A missing normal27 helper
or unavailable constructor-free allocation is a prerequisite failure, not a behavioral result.

The coordinator may stage the generated probe and matching APK read-only beneath the installed app
UID in an already contained guest, then invoke:

```sh
run-as org.gramlab.android sh \
  /data/user/0/org.gramlab.android/files/rich-button-matrix/run-on-guest.sh \
  /data/user/0/org.gramlab.android/files/rich-button-matrix/probe.apk \
  /data/user/0/org.gramlab.android/files/rich-button-matrix/normal27.apk \
  /data/user/0/org.gramlab.android/files/rich-button-matrix-RUN
```

All three inputs in this example must first be staged where the installed app UID can read them.

The fresh bounded output contains seven case records, an outer-basis evidence record and summary.
The cases compare identity, translated and nonuniformly scaled outer bases; verify the independently
specified cell-local rectangle and retain an expected-only reference screen-origin addition; exercise missing,
mismatched, nested and mismatched-end contexts; and reject singular entry matrices, empty bounds,
and an affine finite-input overflow at the first corner. The latter first records all raw
Android-mapped corner
coordinates and fails as `fixture_did_not_produce_nonfinite` or
`fixture_nonfinite_not_in_first_corner` when the Skia premise does not hold, and requires every
later corner coordinate to remain finite; a failed premise is not
reported as a production-helper regression. The helper does not exercise production screen-offset
code; `expected_screen_bounds` is labeled `reference_only`. Successful results do not replace the public screenshot,
redraw stability and actual tap acceptance gate.
