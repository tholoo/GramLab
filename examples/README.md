# Examples

The checked-in [echo example](echo/run.toml) runs an ordinary local HTTP Bot API consumer and a
Python scenario in separate contained processes. The scenario verifies two conversations,
including mixed Persian/English and emoji, and writes semantic captures to a local report. From
the repository, after provisioning the [development environment](../docs/development/environment.md):

```sh
nix develop
uv sync --locked --offline
mkdir -p artifacts
uv run --locked --offline gramlab run examples/echo/run.toml \
  --bridge-version 5 --output artifacts/echo-demo
```

The offline sync succeeds only when the locked dependencies have already been provisioned. The
runner does not install dependencies. Open `artifacts/echo-demo/report.html`, and choose a new
output directory for every run. The shorter [hello manifest](echo/hello.toml) runs the exact
single-conversation scenario shown in the root README.

The same echo bot/scenario has a [headless Android manifest](echo/android.toml). It renders and
captures the conversations through the original Telegram Android client rather than a recreated
layout. This requires the separately provisioned Android environment and a compatible reviewed
APK built from the [pinned source and patch queue](../docs/development/android-build.md):

```sh
nix develop .#android
uv sync --locked --offline
mkdir -p artifacts
uv run --locked --offline gramlab run examples/echo/android.toml \
  --bridge-version 5 --android-apk "$GRAMLAB_ANDROID_APK" \
  --output artifacts/echo-android
```

`--bridge-version 5` is a trusted runner selection, not a consumer-manifest field. It is accepted
in both simulation and headless Android mode; version 5 adds the ordinary-document bridge while
retaining version-4 custom-emoji data. The repository does not distribute an APK or define a
portable value for `GRAMLAB_ANDROID_APK`; set it only to a locally reviewed build. Runtime does not
download or build Android inputs. `interactive-android` remains unsupported. See the
[consumer-runner contract](../docs/development/consumer-runner.md) and
[capture setup](../docs/development/scenario-captures.md) for the complete boundaries.

Additional runnable examples cover [inline callbacks](inline), [bot recovery](recovery),
[bounded composer input](composer), [rich messages](rich), [rich buttons](rich_inline) and
[rich lists](rich_lists). Their `run.toml` and `android.toml` manifests select the corresponding
mode; support remains limited by the [compatibility matrix](../docs/compatibility/matrix.md).

The [representative workflow](representative) is the bridge-v6 composed milestone example. It adds
automatic and explicit rich entities, ordinary/rich callbacks across bot recovery, photos,
documents, true albums and static/animated custom emoji in one offline run. Its README gives the
exact simulation and original-Android commands; the repository still does not distribute an APK.

[report.py](report.py) is different: it writes a self-contained HTML report from a small, clearly
labeled synthetic documentation fixture. Follow the [report instructions](../docs/development/reports.md)
to run it. It does not start a bot or Android client.
