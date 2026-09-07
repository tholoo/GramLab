# Contributing

Read [AGENTS.md](AGENTS.md) before implementation. The current repository contains an experimental
process boundary and Android preparation. [The handoff](docs/development/handoff.md) identifies
the active ticket and remaining gates.

## Development environment

Use Python 3.13 and uv. `pyproject.toml` defines the development tools; `uv.lock` records their
resolution. Tool upgrades should update the lockfile and pass the required checks together.

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
uv run --locked ruff check . tools/test-timings
uv run --locked ruff format --check . tools/test-timings
```

The experimental Python implementation is packaged with the pinned uv build backend. There is no
stable simulator SDK yet. The [consumer runner](docs/development/consumer-runner.md) exposes
`gramlab run` for simulation and headless captures, and the [experimental scenario client](docs/development/scenario-sdk.md)
provides typed world control inside private components.

Use focused pytest runs during development, and the following full checks at handoff. Run the
behavioral suite in the [documented outer network guard](docs/development/runtime-boundary.md):

```sh
uv run --locked mypy src/gramlab tests/probes/android_guest.py tests/probes/android_native_guard.py \
  tests/probes/android_client_bridge.py tests/probes/android_application.py \
  tests/probes/android_callbacks.py tests/probes/android_formatting.py \
  tests/probes/android_recovery.py tests/probes/recovery_round_trip.py \
  tests/probes/android_composer.py tests/probes/android_live_gap.py tests/probes/android_composer_text.py tests/probes/jdwp.py tests/composer_report.py \
  tests/probes/bot_round_trip.py tests/probes/callback_round_trip.py \
  tests/probes/long_poll_bot.py tests/probes/formatted_round_trip.py \
  tests/probes/component_bot.py tests/probes/emulator_process.py \
  tests/fixtures/echo_bot.py tests/fixtures/callback_bot.py tests/fixtures/formatted_bot.py \
  tests/fixtures/recovery_bot.py \
  clients/android/prepare.py tests/recovery_report.py examples/report.py \
  tests/probes/scenario_round_trip.py tests/fixtures/scenario_actor.py examples/echo \
  tests/probes/trace_runner.py
uv run --locked mypy tests/probes/rich_round_trip.py tests/probes/android_rich_messages.py \
  tests/fixtures/rich_bot.py tests/test_rich_round_trip.py tests/test_android_rich_messages.py
uv run --locked mypy tests/probes/android_rich_lists.py tests/test_android_rich_lists.py \
  tests/probes/android_list_rendering.py tests/test_android_list_rendering.py
uv run --locked mypy examples/inline
uv run --locked mypy examples/recovery
uv run --locked mypy examples/composer
uv run --locked mypy examples/rich tests/test_runner_rich_example.py
uv run --locked mypy tests/probes/android_effects.py tests/test_android_effects.py
uv run --locked mypy examples/rich_inline tests/test_runner_rich_buttons.py
uv run --locked mypy examples/rich_lists tests/test_runner_rich_lists.py
uv run --locked mypy tests/test_rich_cleaning_round_trip.py tests/test_android_rich_cleaning.py \
  tests/probes/android_rich_cleaning.py
uv run --locked mypy tests/probes/android_rich_button_codec.py tests/test_android_rich_button_codec.py
uv run --locked mypy tests/test_runner_rich_action_captures.py
uv run --locked mypy tests/test_rich_action_round_trip.py tests/test_android_rich_actions.py \
  tests/probes/android_rich_actions.py
uv run --locked mypy tests/probes/android_rich_messages.py tests/probes/android_rich_action_input.py \
  tests/probes/rich_action_input_round_trip.py tests/fixtures/rich_action_input_bot.py \
  tests/rich_action_input_experiment.py
uv run --locked mypy tests/probes/android_rich_action_effect.py tests/rich_action_effect_experiment.py \
  tests/probes/rich_action_effect_round_trip.py tests/fixtures/rich_action_effect_bot.py
MYPYPATH=tests uv run --locked mypy --explicit-package-bases \
  tests/probes/android_guest.py tests/test_guest_startup_diagnostics.py
uv run --locked mypy tools/test-timings tests/test_test_timings.py
uv run --locked mypy --strict tests/assets/rich-media/generate.py tests/assets/rich-media/verify.py
uv run --locked mypy tests/test_quoted_code_entities.py tests/test_quoted_code_round_trip.py \
  tests/test_android_quoted_code.py tests/probes/quoted_code_round_trip.py \
  tests/probes/android_quoted_code.py tests/probes/android_quoted_code_codec.py \
  tests/probes/rich_round_trip.py tests/fixtures/quoted_code_bot.py
uv run --locked pytest -m 'not android' -n 4 --cov=src/gramlab --cov-report=term-missing --cov-fail-under=80
```

The 80% floor is an initial backstop; review the behavioral assertions and blind spots regardless.
Use pytest-xdist only for appropriately isolated tests. Mark Android-dependent tests separately;
report missing Android infrastructure as unavailable coverage, not success.

The current isolated core inventory has passing parallel evidence; the four-worker recipe above
is the established development workflow. Run it inside the outer network guard linked above.
Keep Android verification separate and serial under the `android-gate` lock described in
[parallel development](docs/development/parallel-work.md#shared-resource-locks). Excluding Android
here avoids reporting unavailable guest tests as core skips. Review isolation when adding tests.
Use [retained timings](docs/development/test-timings.md) to compare runs before repeating a gate;
parallel wall time and summed case time measure different things.

## Task workflow

Work on a focused task branch. After the initial repository baseline exists, use a sibling Git
worktree when parallel tasks need isolation. Keep local Markdown issues version-controlled and
runtime artifacts ignored. Use this repository's documented verification and release workflow.
A configured remote does not authorize publication.

Before implementation, claim the active ticket and resolve dependencies. Read existing state
before changing files. At handoff, preserve work, report its Git state and verification precisely,
and update affected docs and tickets. Remote publication requires user approval.

## Automation

The manually dispatched CI validates configuration, Markdown links and Python static checks.
Its Nix job runs the real Linux isolation tests and requires 80% coverage. It does not claim
Android fidelity or guest egress isolation. Extend it as those capabilities are implemented;
manual execution remains the initial product workflow.

For concurrent implementation, use the [parallel development workflow](docs/development/parallel-work.md)
and `tools/worktree`. Keep file ownership explicit and serialize expensive Android gates through
its shared local resource lock. Developer helper checks run with `pytest tests/test_developer_tooling.py`, `bash -n tools/worktree`
and `shellcheck tools/worktree` in the Nix shell. For repeated command-line work, `tools/dev`
retains the selected development environment in an ignored Nix profile. Validate it with
`bash -n tools/dev`, `shellcheck tools/dev`, and a real `tools/dev default --command python3 --version`
invocation; the resulting profile must remain registered as a Nix garbage collection root.

Retain pytest JUnit output with a distinct `--junitxml=artifacts/RUN.xml` path when investigating
latency. The [timing command](docs/development/test-timings.md) compares retained reports without
rerunning tests and keeps added cases separate from matched duration changes. Its focused CLI
checks run with `pytest tests/test_test_timings.py`; it does not change runtime isolation or the
meaning of suite coverage.
