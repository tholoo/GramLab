# Native rich-button disarm lifetime probe

This GPL-2.0-or-later diagnostic loads the reviewed Android APK's actual
`GramLabButtonObserver`, initializes only its private control-file state through reflection, and
invokes its real `reload()` method. The applicable license is
[the Android adapter GPL text](../../../clients/android/patches/COPYING). The root MIT license does
not relicense this adapter-bound fixture.

The cases exercise valid disarms with an old activation or old client lifetime, the exact current
operation and another current-lifetime operation, plus malformed JSON, extra fields, schema and
each required token. They inspect the actual arm, disarmed-operation, invalidated-operation and
consumed-operation fields after `reload()`. They do not implement a second copy of the reload
decision, initialize the application, draw UI, resolve geometry, or perform input.

Compile the fixture using only cached inputs in this checkout's pinned Android shell:

```sh
tools/dev android --offline --command bash \
  tests/fixtures/android_button_disarm/compile.sh \
  .cache/android-button-disarm-probe-RUN
```

The fresh output contains `probe.apk`, its classes/DEX, and `inputs.json` with exact source,
compiler, Android API, D8 and output hashes. The probe uses reflection, so the same probe APK can
run against the immutable normal27 APK and the staged normal28 APK. Compilation proves only that
the fixture is valid Android bytecode.

Set `GRAMLAB_ANDROID_RUNTIME_PROFILE`, `GRAMLAB_ANDROID_PROBE_APK` and
`GRAMLAB_ANDROID_BUTTON_DISARM_PROBE_APK`, then run through the shared Android lock and mandatory
outer network guard:

```sh
tools/worktree lock android-gate tools/dev android --command \
  unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/pytest -q \
  tests/test_android_button_disarm.py::test_actual_reload_scopes_valid_disarm_to_its_client_lifetime'
```

The normal27 APK must fail both stale-lifetime cases; normal28 must pass all ten. The test runs in
the existing contained AOSP guest and retains the app-process output plus individual case records.
It is control-state evidence, not rendering, clipboard or input acceptance.
