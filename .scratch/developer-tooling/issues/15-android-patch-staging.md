# Stage a new Android patch without copying version-specific scripts

Type: task
Status: ready-for-agent
Work state: implemented on `task/android-patch-staging`; coordinator review pending
Blocked by: coordinator integration

Own this ticket, `tools/android-patch-stage`, focused `tests/test_android_patch_stage.py` and
`docs/development/android-patch-staging.md`. Coordinator owns live source mutation, builds,
full provenance chains, shared contributor/CI files and native acceptance.

Replace repetitive private patch-preparation scripts with a small standard-library CLI that
accepts an existing source tree, one patch, a fresh output directory and independently supplied
before/after SHA-256 manifests keyed by relative file path. Verify all declared source preimages,
copy only affected files into private before/after trees, apply the patch only to the private
tree with zero fuzz and no offsets, and verify exact expected postimages. Retain the original
patch, manifests and bounded command output. The live source tree must remain unchanged.

Reject traversal, symlinks, binary/rename/delete patches, undeclared file changes, malformed or
duplicate manifest fields, stale source, output collisions and fuzzy/offset application. Support
ordinary textual edits and explicitly declared new files. Bound files, patch/manifest sizes and
subprocess runtime. Failed staging must retain diagnostic evidence without claiming readiness.
Do not build a general cleanup, recovery or live-source mutation framework. Keep machine paths
only in generated ignored manifests. Focused tests should use real patch execution and temporary
files, including failure cases that prove live source bytes are unchanged. No guest/build/full
gate, archive mutation or external traffic. Return a clean frozen branch and focused checks.

## Worker evidence

`tools/android-patch-stage` accepts explicit source, patch, before/after SHA-256 manifest and fresh
output paths. It retains exact inputs, copies only declared existing paths into private before and
after trees, creates private parents for declared new files, invokes the system patch tool with
zero fuzz, and verifies the complete expected postimage set. The generated `stage.json` contains
machine paths and stays in the caller's ignored output.

Thirteen real temporary-filesystem cases execute the actual patch subprocess and cover an existing
edit plus a new file, stale preimages, wrong postimages, undeclared changes, nonapplying/offset
input, binary/rename/delete markers, symlinked source paths, duplicate manifest fields, output
collisions, manifest traversal, a traversing patch header, an unframed create/delete prefix and
runtime enforcement of the command-output bound. Every failure control compares the
live source or the relevant outside target unchanged and retains a failed stage when output was
created. Follow-up JUnit is retained at `artifacts/android-patch-staging-followup.xml`; scoped Ruff,
formatting, strict mypy and bytecode compilation pass. No live Android source, APK, build, guest,
network or shared configuration was changed.
