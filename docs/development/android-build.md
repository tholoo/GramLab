# Android build preparation

Status: the current source preparation applies the complete ordered 30-patch queue to the pinned
Telegram Android revision. A reviewed local x86_64 normal30 APK has complete source provenance and
passes the recorded bridge-v5 document workflows in the original client. The repository does not
contain or publish that APK; its retained hash is evidence, not a download or a promise that a new
locally signed build will be byte-identical.

Read [licensing](licensing.md), [upstream maintenance](upstream.md), and
[offline safety](offline-safety.md) first. Dependency provisioning can access public registries;
client execution remains a separate, contained operation.

## Prepare a dedicated source tree

Use the unchanged acquired checkout under `clients/android/upstream/`, with the exact commits in
the [source lock](../../clients/android/upstream-lock.json). `prepare.py` verifies every pinned
revision and exports tracked files from Git objects, rather than copying a developer's working
tree or ignored configuration. It applies the [ordered patch queue](../../clients/android/patches/README.md)
and refuses existing destinations. The script makes no network request; if the approved pinned root
checkout or any of its ten submodules is absent or has the wrong revision, stop rather than acquiring
or updating source implicitly.

The following commands are source/build preparation steps. This documentation reconciliation
audited their repository paths but did not acquire source, provision dependencies, build an APK or
run Android. The first Gradle invocation can fetch missing dependencies and therefore belongs to a
separately approved provisioning phase, never to an offline bot/client run:

```sh
nix develop .#android
python clients/android/prepare.py --destination .cache/android-build/worktree
cd .cache/android-build/worktree
mkdir -p .gramlab
keytool -genkeypair -keystore .gramlab/debug.keystore \
  -storepass android -keypass android -alias gramlab-debug \
  -keyalg RSA -keysize 3072 -validity 3650 \
  -dname 'CN=GramLab Development' -noprompt
./gradlew --no-daemon --max-workers=2 --dependency-verification=strict \
  :TMessagesProj_GramLab:assembleDebug
```

Choose a fresh ignored destination for a new export. Subsequent builds of that tree use its
existing GramLab-only key. `prepare.py` verifies the locked root and submodule revisions before
creating output, exports only tracked Git objects, removes upstream signing/service templates,
replaces upstream API/hash/key declarations with inert values, applies each filename from
`clients/android/patches/series`, and copies the committed source lock and dependency checksum
record. It does not record original credential values in the patch queue. No real Telegram identity
or production credential is used.

The new application ID is `org.gramlab.android`, with a distinct unofficial label and original
vector icon. The shared Telegram renderer, Java resources and JLatexMath implementation are
preserved; the second patch adds narrow [native transport guards](android-native-guard.md).
Cloud/distribution Gradle plugins and unrelated application variants are
excluded from this selected build. The fourth patch first enables the application only with
synthetic configuration and audited startup/transport seams; the remaining ordered patches add the
documented composer, recovery, rich-message, media, custom-emoji, rich-button and ordinary-document
adapter surfaces. Independent containment remains mandatory; not all cloud runtime dependencies
have been removed.

The shared library and APK target x86_64. Native compilation uses a Ninja job pool with two
compile jobs and one link job by default; `-PgramlabNativeJobs=<count>` selects another compile
limit. This is separate from Gradle's worker limit. The
[CMake job-pool contract](https://cmake.org/cmake/help/v3.22/prop_gbl/JOB_POOLS.html) explains the
distinction; generated Ninja rules were inspected to verify the limits actually apply.

## Dependency provenance

Gradle 8.11.1 is downloaded through the upstream wrapper with its
[published SHA-256](https://services.gradle.org/distributions/gradle-8.11.1-bin.zip.sha256) enforced
in `gradle-wrapper.properties`. The verified value is
`f397b287023acdba1e9f6fc5ea72d22dd63669d59ed4a289a29b1a76eee151c6`.

The standard Google Maven endpoint returned HTTP 404 for AGP 8.10.1. Google's official
`redirector.gvt1.com/edgedl/android/maven2/` distribution endpoint served the same pinned artifact.
The patch uses that official endpoint, alongside Maven Central and the upstream build plugin's
Gradle Plugin Portal. No machine-specific proxy or third-party mirror is embedded in the build.

The AGP JAR's observed SHA-256,
`a0fe22ce029c548335a75913f7ad517c827c567b8abb84047102034255ae1173`, matches the SHA-256 and size in
Google's [published module metadata](https://redirector.gvt1.com/edgedl/android/maven2/com/android/tools/build/gradle/8.10.1/gradle-8.10.1.module).
[AGP's compatibility table](https://developer.android.com/build/releases/agp-8-10-0-release-notes)
confirms the selected Gradle/JDK/API requirements.

The [dependency checksum record](../../clients/android/dependency-verification.xml) contains 519
components and 918 artifact/metadata entries from the successful provisioning build. Preparation
copies it into `gradle/verification-metadata.xml`; ordinary builds use strict verification. These
are acquired SHA-256 checksums, not independently authenticated signatures or a Gradle version
lock. Each recorded artifact has a matching cached file. An older, unused copy of a deprecated
artifact has different bytes and is intentionally not added to the accepted checksums.

Only a deliberate dependency update should use `--write-verification-metadata sha256`: inspect
the changes and their origin before replacing the committed record. Generating new checksums
during an ordinary build would accept changed artifacts instead of detecting them. Package/asset
license auditing and source reconstruction of upstream native prebuilts remain open distribution gates.

## Rebuild without external networking

After provisioning, prepare a new ignored directory with `source/` exported by `prepare.py` and
`gradle/` containing copies of the project Gradle `caches/` and `wrapper/` directories. Generate a
dedicated key in `source/.gramlab/` as above. Do not copy personal Gradle configuration or daemon
registries. The build data directory is the only writable host directory exposed to the build.

From the repository root in `nix develop .#android`, the following runs the build through the
[process boundary](runtime-boundary.md). Adjust only the ignored data directory if needed:

```sh
PYTHONPATH=src python - <<'PY'
import dataclasses
import os
from pathlib import Path
from gramlab.runtime import RuntimeProfile, Sandbox

profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_ANDROID_RUNTIME_PROFILE"]))
environment = dict(profile.environment)
environment["GRADLE_USER_HOME"] = "/work/gradle"
environment["GRADLE_OPTS"] = (
    "-Dorg.gradle.project.android.aapt2FromMavenOverride="
    + environment["ANDROID_HOME"] + "/build-tools/36.0.0/aapt2"
)
profile = dataclasses.replace(profile, environment=tuple(environment.items()))
script = """
import os, subprocess
os.makedirs('/work/home', exist_ok=True)
os.chdir('/work/source')
with open('/work/build.log', 'w') as log:
    result = subprocess.run([
        'bash', './gradlew', '--no-daemon', '--offline',
        '--dependency-verification=strict', '--max-workers=2',
        ':TMessagesProj_GramLab:assembleDebug',
    ], stdout=log, stderr=subprocess.STDOUT)
raise SystemExit(result.returncode)
"""
result = Sandbox(profile).run(
    [profile.python, "-c", script],
    data=Path(".cache/android-build/offline"), timeout=2400,
)
print(result.stdout, result.stderr)
raise SystemExit(result.returncode)
PY
```

Inspect the ignored `build.log` and require a successful exit. `--offline` prevents dependency
fetches; the separate loopback-only network namespace enforces the external network boundary.
The build does not expose KVM or start an emulator. A missing cache entry must fail; provision it
separately and repeat the contained build after reviewing any dependency changes.

## Current evidence

- The retained normal30 source-provenance record names upstream revision
  `62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c` and contains all 30 ordered patch filenames and
  SHA-256 values, ending with `0030-ordinary-document-delivery.patch`. Host controls reject an
  incomplete series, changed first/final patch, upstream mismatch or changed APK bytes.
- The reviewed local normal30 APK SHA-256 is
  `a964bbaccaaf59719d966a72ecd85de4288d146887e3f7ff7d50be7281df726b`. The public bridge-v5
  runner passes a contained real bot, original document render, inline tap/callback, stable-file
  reuse and repeated original-client launches on those bytes. Dedicated native gates separately
  pass original loader/cache/destination behavior and the document→photo→document edit lifecycle.
  See [local ordinary documents](documents.md) for the precise scope and remaining limits.
- This hash identifies one retained, locally built artifact. It is not checked into the source
  repository, is not available at a repository URL and is not a bit-for-bit reproducibility target:
  signing keys, paths and build metadata can change APK bytes. Reproduction means exporting the
  locked tracked source, applying the exact ordered patch queue, using the pinned toolchain and
  verified dependencies, and recording the resulting source/APK provenance.
- Earlier one-, two- and three-patch preparation builds remain historical evidence for build,
  native-guard and semantic-adapter bring-up; their disabled manifests and old APK hashes do not
  describe the current 30-patch application. Patch 4 first activated synthetic startup, and later
  records cover each added surface at its own checkpoint.
- The current build still targets only the documented x86_64 evidence profile. Distribution remains
  blocked on the dependency/asset license audit and corresponding-source review; successful local
  build or runtime evidence does not authorize binary publication.

Build logs, local signing material, absolute paths, timings and live process handles belong in
ignored `.cache/` or `artifacts/`. Preserve a live build across handoffs and poll its actual handle;
an observation timeout is not evidence that compilation stopped.
