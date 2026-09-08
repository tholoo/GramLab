# Immutable archived APK storage

Completed Android runs can contain many byte-identical APK copies. `tools/artifact-store` retains
every `.apk` path while moving its bytes into a caller-selected content store and replacing the
archived path with a hardlink to a verified read-only object. It uses only the Python standard
library and does not select archives automatically.

Use it only on a completed, quiescent archive. Stop every process that can write beneath the
archive root and confirm the root contains retained run output rather than a build directory,
active run staging area, guest disk or emulator data directory. The archive and store must be
separate directories on the same filesystem. The plan and receipt must be outside both.

Create and review a plan before changing the archive:

```sh
tools/artifact-store plan \
  --archive-root ARCHIVE_ROOT \
  --store CONTENT_STORE \
  --output PLAN.json
```

The create-only plan records the canonical roots and every regular `.apk` path, SHA-256, size,
device/inode identity, ownership, permissions, link count and nanosecond timestamps. Planning
rejects symlinks and an empty or oversized inventory. Keep plans in ignored local storage because
they contain host paths and local inventory.

After checking the root, store and full plan, apply it explicitly:

```sh
tools/artifact-store apply \
  --archive-root ARCHIVE_ROOT \
  --store CONTENT_STORE \
  --plan PLAN.json \
  --receipt RECEIPT.jsonl \
  --completed-quiescent
```

Apply validates the complete current inventory, every source identity and hash, and every existing
store object before it changes an APK. It copies each distinct value to `<sha256>.apk`, flushes and
verifies the copy, publishes it without overwriting an existing object, makes it mode `0444`, then
atomically replaces each source with a hardlink. Each source is checked again immediately before
replacement. Only files with the same verified digest and size can share an inode.

The JSON-lines receipt is flushed after its start, object, prepared, linked and completion records.
Prepared records contain the original path metadata. If apply is interrupted, every original path
is either the old readable file or the complete verified object. Run the same apply command with
the same plan and receipt to finish: it recognizes an authorized staged link and a replacement
completed just before interruption, and records a verified object published before its prior
journal append as recovered. Parent directories are reopened without following symlinks and the
final replacement uses the anchored directory descriptor. Changed inputs, unexpected receipt
contents, temporary-file collisions and content-object collisions fail instead of being
overwritten. Plans and the complete receipt are each limited to 16 MiB; the tool refuses an
inventory whose durable records would exceed that bound before changing the archive.

Hardlinks share permissions and content. Archived APK paths become read-only because changing a
linked path in place would also change the content object and every peer. To obtain a writable,
independent file, copy the bytes to a new filesystem entry rather than changing the archived path:

```sh
cp --reflink=auto --no-preserve=mode ARCHIVED.apk WORKING.apk
chmod u+w WORKING.apk
```

For exact restoration, read the path's `original.mode`, `original.atime_ns` and
`original.mtime_ns` from its receipt `prepared` record, then apply those values to the independent
copy with `chmod` and `os.utime(..., ns=(atime_ns, mtime_ns))`. Ownership is also recorded; normal
users should materialize files they own rather than attempting privileged ownership changes.

Do not edit, truncate, chmod or delete a content object or one of its archived hardlinks. Retention
and deletion policy remains manual and outside this tool. Preserve the plan and receipt for as long
as the archive uses shared objects.
