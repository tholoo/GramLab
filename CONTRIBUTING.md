# Contributing

Read [AGENTS.md](AGENTS.md) before implementation. The current repository contains only a
scaffold. [The first ticket](.scratch/android-offline-foundation/issues/01-validate-android-seam.md)
is the entry point for the next agent.

## Development environment

Use Python 3.13 and uv. `pyproject.toml` defines the development tools; `uv.lock` records their
resolution. These initial tool versions match the inspected consumer application environment, not a claim
that they are the newest versions. No consumer application runtime dependency is included.

Dependency provisioning can access package registries. Normal scenario execution must follow
[offline safety](docs/development/offline-safety.md). Do not mistake `uv --offline` alone for
network isolation of a bot, client, or test subprocess.

The [development flake and direnv setup](docs/development/environment.md) provide pinned Python
and Android preparation shells. Run `nix develop` for core work or `nix develop .#android` for
the approved Android toolchain on x86_64 Linux. `nix fmt` and `nix flake check` validate Nix and
direnv changes. Store host inventory, proxy addresses and other machine-specific notes in ignored
`.cache/local-notes/` or run artifacts; keep committed setup and documentation portable.

```sh
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
```

The project is deliberately non-packaged until a real Python implementation exists. There is no
CLI entry point or importable SDK yet. Add packaging and public commands alongside working code.

Once source and behavioral tests exist, use focused pytest runs during development, and the
following full checks at handoff:

```sh
uv run --locked mypy src/gramlab
uv run --locked pytest --cov=src/gramlab --cov-report=term-missing --cov-fail-under=80
```

The 80% floor is an initial backstop; review the behavioral assertions and blind spots regardless.
Use pytest-xdist only for appropriately isolated tests. Mark Android-dependent tests separately;
report missing Android infrastructure as unavailable coverage, not success.

## Task workflow

Work on a focused task branch. After the initial repository baseline exists, use a sibling Git
worktree when parallel tasks need isolation. Keep local Markdown issues version-controlled and
runtime artifacts ignored. Do not apply consumer application's `mp`, beta, Dokploy or remote-ref cleanup
workflow here: GramLab is an independent repository. A configured remote does not authorize publication.

Before implementation, claim the active ticket and resolve dependencies. Read existing state
before changing files. At handoff, preserve work, report its Git state and verification precisely,
and update affected docs and tickets. Remote publication requires user approval.

## Automation

The manually dispatched CI workflow validates scaffold configuration and Markdown links. If
Python source exists, it also requires actual tests and runs the Python gate. It does not claim
Android fidelity or external-egress isolation. Extend it with isolated runtime jobs as those
capabilities are implemented; manual execution remains the initial product workflow.
