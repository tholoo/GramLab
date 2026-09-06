# GramLab agent guidance

Before starting implementation, read [the handoff](docs/development/handoff.md) and the
active local ticket. This repository is a scaffold; establish what exists before describing
commands or features as working.

Before changing behavior or tests, follow [TESTING.md](TESTING.md). Before running a bot,
Android client, Mini App, or scenario, read [offline safety](docs/development/offline-safety.md).

Before changing architecture, consult [the boundaries](docs/architecture/overview.md) and relevant
ADRs. Consult the user before consequential design changes, widening scope, changing the fidelity
target, adding network access, publishing artifacts, or changing license boundaries.

Before acquiring or adapting upstream source/assets, read [licensing](docs/development/licensing.md)
and [upstream maintenance](docs/development/upstream.md). Keep client-derived code out of the MIT
core. Preserve upstream rendering rather than recreating it.

For task branches, verification and handoff, follow [CONTRIBUTING.md](CONTRIBUTING.md) and
[completion requirements](docs/development/completion.md). Preserve unrelated changes and keep
GramLab independent of consumer applications.

## Agent skills

### Issue tracker

Track issues and specs as local Markdown under `.scratch/`.
See `docs/agents/issue-tracker.md`.

### Triage labels

Use the five default triage roles as issue status values.
See `docs/agents/triage-labels.md`.

### Domain docs

Use a single root glossary and root architecture decision records.
See `docs/agents/domain.md`.
