# GramLab

An offline Telegram bot laboratory: programmable simulation, faithful Android previews,
and reproducible interaction tests.

**Status: experimental foundation.** Pinned development shells, Android source provenance and a
tested Linux process isolation boundary and dedicated AOSP guest startup exist. A persistent
synthetic world now exchanges messages with a real local bot over HTTP. An
[experimental scenario client](docs/development/scenario-sdk.md) controls that world from a private
process. The [experimental consumer runner](docs/development/consumer-runner.md) runs selected
scenario/bot files and produces local HTML reports. The same scenario can request
[original Android chat captures](docs/development/scenario-captures.md) in headless mode.
A stable SDK, interactive mode and complete Telegram compatibility remain unfinished.
The Android APK [builds inside network containment](docs/development/android-build.md).
Its [native transport guard](docs/development/android-native-guard.md) has real JNI probe evidence.
The [Java snapshot adapter](docs/development/android-semantic-bridge.md) receives real bot replies
as client TL objects. [Synthetic application startup](docs/development/android-application.md) now
renders that conversation in the actual client. The [callback loop](docs/development/android-callbacks.md)
verifies a real tap, bot edit and restart recovery. [Local HTML reports](docs/development/reports.md)
retain semantic results and original Android screenshots from a recovery scenario.
See the [world/bot prototype and its limits](docs/development/world-bot-prototype.md).
See the
[runtime evidence and limits](docs/development/runtime-boundary.md).

The [inline-input example](docs/development/scenario-input.md) runs the same callback/edit scenario
with virtual input or an actual Android button tap, retaining original before/after captures.

The [composer example](docs/development/scenario-composer.md) presses Start Bot, sends formatted
Persian/emoji text through the original composer and verifies real replies in both modes.

The [rich-message example](docs/development/scenario-rich-messages.md) sends bilingual structured
blocks and edits them to RTL, retaining equivalent semantic results and original Android captures.
The supported subset includes headings, formatted text, tables and nested quotations; broader
rich-message features remain explicit gaps.

The [bot recovery example](docs/development/scenario-lifecycle.md) stops a real bot after callback
receipt and restarts it to handle the same pending update, preserving its private state.

## Intended experience

Run an actual local bot against a simulated Bot API with virtual users and chats. Use the
same scenarios for renderer-free behavioral tests, headless Android rendering, and visible
Android exploration. Render previews and documented conversation examples without real accounts.

The first client target is the actual Telegram Android source, minimally adapted for offline
operation. Fidelity means a specified client revision, Android/runtime profile, assets, and
supported surfaces—not equivalence to every Telegram client or its private server behavior.

## Start here

- Next implementation agent: [handoff](docs/development/handoff.md).
- Product scope: [requirements](docs/product/requirements.md).
- Architecture: [boundaries](docs/architecture/overview.md).
- Safety: [offline requirements](docs/development/offline-safety.md).
- Progress: [foundation spec](.scratch/android-offline-foundation/spec.md).
- Tooling: [contributor workflow](CONTRIBUTING.md).
- Development shells and direnv: [environment setup](docs/development/environment.md).
- Fidelity evidence: [compatibility matrix](docs/compatibility/matrix.md).

No Telegram credentials are required or accepted by the planned default workflow. Dependency
installation and explicit upstream acquisition are separate from isolated test execution.
No Android runtime setup is needed to read or extend this scaffold.

Original core/SDK work is intended to use MIT. Android-derived components retain applicable
upstream copyleft terms. See [licensing boundaries](docs/development/licensing.md).
GramLab is independent and is not affiliated with or endorsed by Telegram.
