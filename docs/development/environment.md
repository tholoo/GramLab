# Development environment

The project flake pins nixpkgs, Python and uv; `uv.lock` pins Python dependencies. The Android
profile additionally pins SDK tools, NDK, CMake, emulator and system image metadata. Host paths,
proxy configuration, local inventory and run logs belong in ignored local files.

## Python development

With Nix installed and flakes enabled:

```sh
nix develop
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
```

The default shell includes Python 3.13, uv, Git, curl, jq, ripgrep, nixfmt and ShellCheck. It uses
`.venv/` and `.cache/uv/` beneath the repository root, and disables uv's automatic Python downloads.
It does not automatically activate or replace an existing virtual environment. Use `uv run` for
project Python commands; `uv sync --locked` explicitly provisions the selected interpreter's
locked dependencies. No unrelated project or personal Python installation is required.

For repeated command-line work, [tools/dev](../../tools/dev) retains the selected shell in a
standard Nix profile under ignored `.cache/nix/profiles/`:

```sh
tools/dev default --command uv run --locked --offline ruff check .
tools/dev android --command python3 --version
tools/dev media --command ffmpeg -version
```

The profile keeps the development closure rooted between invocations, avoiding reprovisioning
when otherwise unrooted store paths are collected. The helper runs from the project root and
forwards remaining options directly to `nix develop`; `--offline` can require already provisioned
inputs. Each worktree keeps its own profiles. It does not change host garbage collection settings,
provision Python dependencies, or replace the separate runtime network boundary. Profile links
and their local store paths remain ignored. Ordinary `nix develop` remains available.

If offline provisioning in a new worktree lacks a wheel already downloaded by another checkout,
seed the new worktree's ignored `.cache/uv/` from that provisioned package cache while both caches
are idle. Preserve relative cache links and keep the destination separate; never reuse another
checkout's `.venv`. Run `uv sync --locked --offline` in the assigned worktree afterward and verify
that importing GramLab resolves to that checkout. This avoids repeated downloads while preserving
the pinned dependencies and independent editable installation. Cache seeding is provisioning;
the runtime network guard remains mandatory. Keep actual source/destination paths in local notes.

Core shell outputs are defined for x86_64 Linux, aarch64 Linux and aarch64 macOS. The pinned
nixpkgs revision does not support x86_64 macOS. Evaluation on a platform is not evidence that
GramLab's runtime is supported there; the initial Android profile targets x86_64 Linux only.

On Linux, the shell also provides util-linux, iproute2 and a Nix-generated
`GRAMLAB_RUNTIME_PROFILE` for the [experimental process boundary](runtime-boundary.md).
This selects an immutable dependency closure and pinned bubblewrap executable; it does not
start a sandbox on shell entry. The Android shell also exports `GRAMLAB_ANDROID_RUNTIME_PROFILE`
with its immutable SDK/JDK closure and private in-sandbox homes. Follow that page's separate
behavioral verification commands.

## direnv

Install direnv and enable its shell hook, then run `direnv allow` in this repository. `.envrc`
loads the default flake shell. nix-direnv caching is used when available; it is not required by
the file. Shell entry creates cache directories but does not run `uv sync`, start ADB/an emulator,
modify host services, or write Android configuration files into the upstream checkout.

For the Android shell, create an ignored `.envrc.local` containing:

```sh
export GRAMLAB_DEV_SHELL=android
```

Use `GRAMLAB_DEV_SHELL=media` instead for the media fixture tools. Then run `direnv reload`.
Remove that override to return to the default shell. `.envrc` watches the lockfiles, Python
configuration and Nix profiles. An invalid shell name fails explicitly.
Local environment customization belongs in `.envrc.local`; do not commit credentials or proxies.
When nix-direnv is available, fallback to a stale development shell is disabled so evaluation
failures remain visible.

## Media fixtures

The optional `media` shell adds FFmpeg 6.1.6 from the existing nixpkgs pin, with libvpx 1.16.0
and libwebp 1.6.0. It exports `GRAMLAB_MEDIA_TOOLCHAIN`, a generated JSON profile containing
pinned package versions and executable locations. Fixture manifests retain portable versions
and the nixpkgs revision; executable store paths stay in the generated profile.

```sh
tools/dev media --command ffmpeg -version
tools/dev media --offline --command unshare --user --map-root-user --net \
  python tests/assets/custom-emoji/verify.py
```

Provision the shell before the isolated verification command. The verifier regenerates the
[original emoji fixtures](../../tests/assets/custom-emoji/README.md), compares bytes and decodes
their geometry, colors, transparency and timing. An explicit encoder or decoder override must
match the active profile before the scripts claim pinned provenance. Without that profile,
generation records unpinned observations. Entering this shell does not encode assets or launch
a bot/client. Its toolchain profile is separate from the default and Android runtime profiles.
The namespace command above requires Linux; evaluating the shell on another declared platform
does not establish identical encoded bytes or runtime support there.

## Android preparation

```sh
nix develop .#android
```

This is a larger, explicit provisioning step. It adds JDK 17, the pinned Android SDK/NDK,
emulator and AOSP system image, CMake, and native preparation tools. SDK components live in the
immutable Nix store; mutable Gradle and Android configuration goes under `.cache/gradle/` and
`.cache/android/`. Gradle's Android resource tool override points at Nix's patched `aapt2`.
Use the pinned upstream Gradle wrapper; no unrelated global Gradle version is substituted.

The flake accepts the Android SDK license for this approved toolchain, and permits only the
Android SDK package family through nixpkgs' unfree-package check. See
[licensing](licensing.md) and the [toolchain profile](../../clients/android/toolchain.json).
This does not change the licenses of the SDK, client code or distributed artifacts.

The development shell is **not runtime network isolation**. Android and bot execution require the
separate [offline boundary](offline-safety.md). SDK acquisition can access official download
services, with an operator-provided proxy if needed; normal scenarios must not inherit that access.
No AVD, account or client is started merely by entering the shell.

The profile uses Google's official distribution CDN, preserving upstream archive hashes from the
pinned nixpkgs repository metadata. Do not use `sdkmanager` to mutate the Nix SDK or select floating
`latest` packages. Change the profile and lock intentionally when upgrading.

## Checks and upgrades

```sh
nix fmt
nix flake check
nix flake check --all-systems --no-build
```

`nix fmt` formats owned Nix files and excludes upstream source and run/cache directories. Flake
checks verify Nix formatting, `.envrc` Bash/ShellCheck validity, and the manual CI workflow with
Actionlint. The final command evaluates
all declared platform outputs without claiming they were built on every platform. These checks
do not replace Python behavioral tests, Android interaction evidence or egress enforcement.

If a check's tool inputs are missing, inspect its provisioning plan before forcing an offline
build. For example, substitute the host system in:

```sh
nix build --dry-run .#checks.x86_64-linux.workflow
```

Provision through the configured binary cache, then run the check. Nix's `--offline` disables
substitution and may instead attempt a large source build when inputs are missing; it does not
replace the separate runtime network guard. A measured workflow check needed only 2.3 MiB of
cached tools, while the offline attempt planned hundreds of derivations. Keep cache/proxy
configuration local. The retained development-shell profiles do not include every check's tools.

For a deliberate toolchain upgrade, update the immutable nixpkgs revision in `flake.nix`, run
`nix flake lock`, and review both the resulting lock and `clients/android/toolchain.json`. The
Android expression checks the image revision, extension and published checksum so a nixpkgs
update cannot silently select a different image. Revalidate archive provenance, native loader
patches, the development shell and Android fidelity/isolation before recording a supported upgrade.

For test-time investigation, [tools/test-timings](../../tools/test-timings) compares retained
pytest JUnit reports. Its [documented output](test-timings.md) separates matched case changes,
added/removed cases, suite duration and summed case durations. Preserve test selection and profile
information when interpreting results; the helper does not turn uncontrolled runs into benchmarks.
