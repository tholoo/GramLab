# Representative offline bot workflow

This example runs one ordinary HTTP bot against GramLab with no Telegram account and no network
access. The same scenario covers bilingual text, detected and explicit rich entities, ordinary and
rich callbacks, callback edits across a controlled bot restart, photos, documents, true albums and
static/animated custom emoji. Mini Apps are intentionally deferred.

After provisioning the repository, run the semantic workflow inside the offline guard:

```sh
tools/dev default --offline --command \
  unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/gramlab run examples/representative/run.toml \
    --bridge-version 6 --output artifacts/representative-simulation'
```

Run the original Android renderer with the reviewed local APK and shared guest lock:

```sh
tools/worktree lock android-gate tools/dev android --offline --command \
  unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/gramlab run examples/representative/android.toml \
    --bridge-version 6 --output artifacts/representative-android'
```

The Android helper selects the configured reviewed APK/profile. Each output directory contains a
self-contained `result.json`, HTML report and captures; Android adds original PNG screenshots and
UI dumps. Bot and scenario components receive separate filesystems and only loopback endpoints.
The embedded media are small original GramLab fixtures covered by this repository's MIT license.
