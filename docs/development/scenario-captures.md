# Scenario captures in simulation and headless Android

The [consumer runner](consumer-runner.md) now supports chat captures from the same Python
scenario in `simulation-only` and `headless-android` modes. Simulation retains semantic evidence;
headless Android additionally checks the actual client UI and retains original PNGs. Rendering
uses the existing approved Telegram Android APK, not a recreated chat layout.

## Run both modes

The [echo scenario](../../examples/echo/scenario.py) checks and captures two conversations.
[run.toml](../../examples/echo/run.toml) and [android.toml](../../examples/echo/android.toml)
declare the same scenario/bot files, seed and synthetic time. Android allows 300 seconds for
guest startup and rendering.

Run simulation using the [ordinary instructions](consumer-runner.md#run-the-example). For Android,
first provision the [environment](environment.md) and [build the approved APK](android-build.md).
Set `GRAMLAB_ANDROID_APK` locally to that APK, for example in ignored `.envrc.local`; do not add
its local path to the consumer manifest.

```sh
nix develop .#android
uv sync --locked --offline
mkdir -p artifacts
uv run --locked --offline gramlab run examples/echo/android.toml \
  --android-apk "$GRAMLAB_ANDROID_APK" --output artifacts/echo-android
```

The shell supplies `GRAMLAB_ANDROID_RUNTIME_PROFILE`; `--android-profile` can select another
trusted provisioned profile. The core profile still bounds scenario/bot dependencies. The Android
profile supplies the supervisor and private emulator closure. Profiles and APKs are trusted
provisioning inputs, never acquired from a consumer manifest. APK input is limited to 256 MiB;
its SHA-256 and the Android profile fingerprint are recorded. Runtime never downloads or builds
an APK, image or dependency.

The pinned AOSP 36 default x86_64 image uses KVM, `swangle` software graphics, 320×640 at 160 dpi,
default fonts and unchanged app animation settings. Reports record observed API/ABI, build
fingerprint, graphics backend, package version and boot duration. Every run has a fresh dedicated
AVD with private files; it does not attach to a personal device.

## Capture contract

Inside the private scenario process:

```python
capture = lab.capture_chat(
    chat_id=chat["id"],
    label="reply",
    contains=["Echo: سلام hello"],
)
```

`contains` requires 1–32 nonempty strings, each at most 4,096 characters. Every string must occur
in an authoritative message. Android also requires it in a decoded UIAutomator node's text before
retaining the screenshot. Prefer complete message text to distinguish a particular reply. This
is an accessible-text condition, not an independent pixel-equivalence or layout assertion.

The result contains `chat_id`, `label`, complete `history` at request time and `rendered`.
Simulation returns `rendered=False`; successful Android captures return `True` plus `android`
diagnostics. All captures appear in `result.json`; successful original PNGs are embedded in
`report.html`. PNG and UIAutomator XML files are retained in `captures/<label>.png` and `.xml`.
Serialized diagnostics receive general redaction; use the dedicated XML file for structural parsing.

Labels start with a lowercase letter and contain at most 64 lowercase letters, digits,
underscores or hyphens. They must remain unchanged under credential redaction and be unique;
at most eight captures are accepted. Unknown chats, absent expected text, invalid labels and
exhausted limits are rejected before changing capture evidence. Existing captures are never
overwritten. Callers cannot supply an ADB command, guest path or host output path.

The persistent supervisor starts the guest before consumer processes. Each capture opens the
selected user's chat. Changing persona clears only this run's dedicated client data and supplies
a new persona capability. Capturing the same persona cold-restarts the client without clearing
its cache. Captures are serialized. Do not create the guest from a short-lived HTTP handler:
that caused it to die between requests and is covered by the repeated-capture integration test.

The capture socket timeout defaults to 180 seconds and can be adjusted; the manifest's whole-run
deadline still bounds startup/execution. Backend failure produces an explicit scenario error and
a failed run, retaining bounded redacted command/logcat diagnostics where available. Completed
captures survive a later scenario failure. A lost response may leave a completed capture or
changed client state, so uncertainty is conservative and no capture is automatically retried.

## Evidence boundaries

Before client use, the runner checks external IPv4/IPv6 denial and emulator filesystem/PID
separation. Captures require zero Android accounts and reject credential-shaped UI attribute
values before writing PNGs. XML metadata such as `password="false"` is not a displayed password.
No real account, DC connection, new upstream adaptation or renderer replacement is involved.
The broader [offline requirements](offline-safety.md) remain applicable.

History is read before UI observation; concurrent world changes can produce a newer frame.
Sequence actions when a stable checkpoint matters. Long histories are not automatically scrolled
or stitched: requested text must be visible together. Screens retain normal status-bar time and
app animations. They are observations, not deterministic golden images or proof of arbitrary
secret detection in pixels.

`interactive-android` remains explicitly unsupported. Live viewing, SDK-controlled native taps,
more lifecycle/fault commands and multi-guest scheduling remain active work. Separate
[callback/recovery tests](android-callbacks.md) establish their own actual UI interactions;
captures alone do not expose those actions through the SDK.

## Verification

[Capture tests](../../tests/test_runner_capture.py) exercise the actual command and public Python
runner API, including pass/failure preservation, rejection and evidence limits.
[Android consumer tests](../../tests/test_runner_android.py) run the same two-persona scenario in
both modes, compare complete world metadata/histories, inspect actual UI/account/isolation
observations, and require two original screenshots in the report. Further cases retain a capture
after scenario failure and report a startup deadline. Review the actual screenshots alongside
these assertions; a green simulation does not establish rendering fidelity.
