# Android build preparation

Status: a complete x86_64 preparation APK has rebuilt from exported sources and cached dependencies
with strict verification inside independent network containment. Signature/manifest inspection
passed. The preparation application is disabled; synthetic client startup is not implemented.

Read [licensing](licensing.md), [upstream maintenance](upstream.md), and
[offline safety](offline-safety.md) first. Dependency provisioning can access public registries;
client execution remains a separate, contained operation.

## Prepare a dedicated source tree

Use the unchanged acquired checkout under `clients/android/upstream/`, with the exact commits in
the [source lock](../../clients/android/upstream-lock.json). `prepare.py` verifies every pinned
revision and exports tracked files from Git objects, rather than copying a developer's working
tree or ignored configuration. It applies the [ordered patch queue](../../clients/android/patches/README.md)
and refuses existing destinations.

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
existing GramLab-only key. The preparation removes upstream signing/service templates and replaces
the upstream API/hash/key declarations with inert values; it does not record their original
values in the patch queue. No real Telegram identity or production credential is used.

The new application ID is `org.gramlab.android`, with a distinct unofficial label and original
vector icon. The shared Telegram renderer, Java resources, JLatexMath implementation and native
source are preserved. Cloud/distribution Gradle plugins and unrelated application variants are
excluded from this selected build. This does not remove all cloud runtime dependencies or make
the client ready to start: application activation is disabled until the offline patches are proven.

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

- Gradle 8.11.1 downloaded, passed checksum verification and reported the expected version.
- The upstream Kotlin build plugin, JLatexMath and Telegram Java renderer compiled.
- A fresh pinned export applied the patch queue successfully. All 6,666 checked files under the
  original UI Java and main resource directories matched the acquired source byte-for-byte.
- Upstream credential templates, ignored build data and non-inert credential declarations were
  absent from that export. An attempted repeat refused to overwrite the existing tree.
- The generated packaged manifest identifies `org.gramlab.android` and disables the application
  and backup. No client was installed or launched.
- Native configuration initially selected ARM as well. That build was deliberately stopped;
  the revised shared-library configuration selects x86_64, with verified compiler job pools.
- The complete preparation APK contains only x86_64 native libraries, including
  `libtmessages.49.so`. Its signature verifies with the dedicated `GramLab Development` signer.
  The contained build's APK SHA-256 is
  `9c4f26abef38d55d7a345a511e7259d8c88d63acba0feeda15740561fb1a8936` (96,140,183 bytes).
  This identifies the observed artifact, not a bit-for-bit reproducibility guarantee; signing keys,
  paths and build metadata can change APK bytes.
- The first contained attempt compiled Java/resources but exposed SDK Ninja's `/bin/sh`
  requirement. The Android profile now resolves that path to pinned Bash; the boundary regression
  failed before the change and passed afterward. Native compilation and APK packaging completed
  inside the same independent boundary using only cached dependencies.
- `apksigner` verified the resulting APK's v1/v2 signatures; `aapt2` inspected its binary manifest
  and confirmed the GramLab package with application and backup disabled. No client was installed.
- Deliberately replacing the accepted AGP JAR digest with an incorrect checksum caused strict
  offline Gradle configuration to fail on that exact artifact. The committed metadata was restored
  byte-for-byte afterward, and strict offline configuration passed again. All thirteen
  process/guest tests pass with 90.91% statement coverage.

Build logs, local signing material, absolute paths, timings and live process handles belong in
ignored `.cache/` or `artifacts/`. Preserve a live build across handoffs and poll its actual handle;
an observation timeout is not evidence that compilation stopped.
