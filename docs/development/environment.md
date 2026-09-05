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

Core shell outputs are defined for x86_64 Linux, aarch64 Linux and aarch64 macOS. The pinned
nixpkgs revision does not support x86_64 macOS. Evaluation on a platform is not evidence that
GramLab's runtime is supported there; the initial Android profile targets x86_64 Linux only.

On Linux, the shell also provides util-linux, iproute2 and a Nix-generated
`GRAMLAB_RUNTIME_PROFILE` for the [experimental process boundary](runtime-boundary.md).
This selects an immutable dependency closure and pinned bubblewrap executable; it does not
start a sandbox on shell entry. Follow that page's separate behavioral verification command.

## direnv

Install direnv and enable its shell hook, then run `direnv allow` in this repository. `.envrc`
loads the default flake shell. nix-direnv caching is used when available; it is not required by
the file. Shell entry creates cache directories but does not run `uv sync`, start ADB/an emulator,
modify host services, or write Android configuration files into the upstream checkout.

For the Android shell, create an ignored `.envrc.local` containing:

```sh
export GRAMLAB_DEV_SHELL=android
```

Then run `direnv reload`. Remove that override to return to the default shell. `.envrc` watches
the lockfiles, Python configuration and Android profile. An invalid shell name fails explicitly.
Local environment customization belongs in `.envrc.local`; do not commit credentials or proxies.
When nix-direnv is available, fallback to a stale development shell is disabled so evaluation
failures remain visible.

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

For a deliberate toolchain upgrade, update the immutable nixpkgs revision in `flake.nix`, run
`nix flake lock`, and review both the resulting lock and `clients/android/toolchain.json`. The
Android expression checks the image revision, extension and published checksum so a nixpkgs
update cannot silently select a different image. Revalidate archive provenance, native loader
patches, the development shell and Android fidelity/isolation before recording a supported upgrade.
