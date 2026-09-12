# Reconcile the current reproducible setup documentation

Type: task
Status: ready-for-agent
Work state: open
Owner: unassigned
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
