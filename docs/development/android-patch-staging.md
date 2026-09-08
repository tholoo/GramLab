# Private Android patch staging

`tools/android-patch-stage` checks one Android patch in a fresh private directory before a
coordinator considers applying it to the pinned source tree. It never edits the supplied source.
It accepts independently prepared SHA-256 manifests so a copied version-specific preparation
script cannot silently replace the expected preimage or postimage.

Each manifest is a JSON object from source-relative path to lowercase SHA-256. The after manifest
lists every path changed or created by the patch. The before manifest lists every changed path
that must already exist; omission from before explicitly declares a new file.

```sh
tools/android-patch-stage \
  --source ANDROID_SOURCE \
  --patch clients/android/patches/NNNN-change.patch \
  --before-sha256 BEFORE.json \
  --after-sha256 AFTER.json \
  --output PRIVATE_STAGE
```

The output must not exist. The command retains exact input copies, the patch command's bounded
stdout/stderr, the affected before/after trees, and `stage.json`. A ready manifest records absolute
input paths, affected and new paths, and the expected hashes. Keep generated staging directories
ignored because those paths are machine-specific.

The tool accepts at most 128 textual file diffs, 4 MiB per patch or manifest, 8 MiB per affected
source file and 64 MiB of declared source data. It invokes the system `patch` command for at most
30 seconds with `--batch --fuzz=0 -p1`, and rejects any reported fuzz or offset. Paths must match
the after manifest exactly, and executable patch content before the first `diff --git` header is
rejected before invocation. Stdout and stderr are drained while the command runs; exceeding the
1 MiB bound stops that process and retains only the bounded prefixes. Symlinks, traversal, stale
preimages, unexpected postimages, binary patches, renames, deletes, mode-only changes and output
collisions fail. A created output retains `status: failed` diagnostics, while the source tree
remains unchanged.

This stage is preparation evidence. It does not apply anything to the live cached source, extend
the patch series, build an APK, verify source provenance outside the declared affected files, or
establish native behavior. The coordinator separately reviews the staged diff and owns live source
mutation, provenance chaining, builds and native acceptance.
