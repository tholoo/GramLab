# Stage a new Android patch without copying version-specific scripts

Type: task
Status: ready-for-agent
Work state: open
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
