# GramLab

An offline Telegram bot laboratory: programmable simulation, faithful Android previews,
and reproducible interaction tests.

**Status: scaffold only.** There is no simulator, CLI, SDK implementation, Android fork,
verified compatibility, or runnable product test suite yet. Configuration checks are not
evidence of Telegram compatibility.

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
- Fidelity evidence: [compatibility matrix](docs/compatibility/matrix.md).

No Telegram credentials are required or accepted by the planned default workflow. Dependency
installation and explicit upstream acquisition are separate from isolated test execution.
No Android runtime setup is needed to read or extend this scaffold.

Original core/SDK work is intended to use MIT. Android-derived components retain applicable
upstream copyleft terms. See [licensing boundaries](docs/development/licensing.md).
GramLab is independent and is not affiliated with or endorsed by Telegram.
