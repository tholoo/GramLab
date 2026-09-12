# Reconcile the current reproducible setup documentation

Type: task
Status: done
Work state: resolved
Owner: current-setup-docs
Blocked by: none

The repository has a passing public bridge-v5 document workflow on normal30, but several setup
documents still describe the patch-4 scaffold or say no runnable loop exists. Reconcile only
already verified setup and patch provenance; do not claim the pending operational milestone.

Own this ticket and:

- `examples/README.md`;
- `clients/android/README.md`;
- `docs/development/android-build.md`; and
- `clients/android/patches/README.md`.

Do not change code, patches, tests, lockfiles, root/shared handoff or compatibility documents. Read
the public README example, consumer-runner documentation, normal30 build/provenance records, patch
`series` and current preparation script before editing.

Document the exact checked-in runnable public example and bridge-v5 simulation/headless-Android
selection without inventing a portable APK download. Replace obsolete “no runnable loop” claims,
describe current offline source preparation/build inputs honestly, enumerate every patch in `series`
including 0008 and 0026–0030, and distinguish source reproduction from retained local APK evidence.
Fresh upstream acquisition, network access, binary publication and license-boundary changes remain
unauthorized. Commands must be copied from passing repository workflows or explicitly labeled as
preparation steps not executed in this ticket.

Validate every local link, patch-series filename/order, command path and privacy boundary. Run the
repository configuration/Markdown-link check and `git diff --check`; no runtime, guest, build,
dependency or external command belongs to this documentation task.

## Comments

- 2026-09-12: Claimed by `current-setup-docs` on `task/current-setup-docs` at assigned base
  `288a60e4e247bda8d5fd561765d0fe8ac3520fe1`. Work remains limited to the five assigned
  documentation files; no runtime, build, dependency provisioning, network access or upstream
  acquisition will be performed.

## Answer

The four setup pages now describe the checked-in echo runner, explicit bridge-version-5 selection
in simulation and `headless-android`, and the requirement for a separately provisioned reviewed
local APK. They no longer claim that the consumer launcher or original-Android loop is absent, and
they do not offer an APK download or a machine-specific APK path. Source export, dependency
provisioning, contained offline rebuild and runtime execution are separated explicitly; acquisition,
runtime network and binary-publication boundaries remain unchanged.

The patch README now names every entry in `series` once and in exact application order, including
0008 and 0026–0030. All 30 checked-in patch SHA-256 values match the retained normal30 provenance,
whose upstream revision also matches `upstream-lock.json`. The build page distinguishes that
retained local APK/hash evidence from source reproduction and bit-for-bit binary reproducibility.

Verification on 2026-09-12:

- the repository configuration/local-link validator body passes under Python 3.13.15 for 278
  Markdown files;
- the patch series/README audit finds 30 ordered entries, all files present and no extra patch;
- all 30 patch names and hashes match the retained normal30 source-provenance record;
- command-path/privacy checks confirm the CLI selectors, echo manifests, preparation/build paths,
  ten locked submodules, no tracked APK and ignored source/build/runtime boundaries; and
- `git diff --check` passes.

No bot, scenario, Android guest, APK build, dependency command, external network access or upstream
acquisition ran. The ticket remains claimed until coordinator review and integration, per the
parallel workflow.

- 2026-09-12 coordinator integration: reviewed and merged worker commit
  `e22f99d87296165aae5eb88b61414ff82f0cd334`. The root README and document profile were then
  reconciled with the already passing bounded normal30 document evidence. No behavior, Android
  source/patch, runtime input or fidelity target changed. The ticket is resolved.
