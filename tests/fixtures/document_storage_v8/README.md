# Populated schema-8 document migration fixture

This is original synthetic GramLab data generated offline with the untouched Python package from
assignment base `df1e67e6c61ba2b63c8883732863aca2e714d6b6`. The imported
`src/gramlab/world.py` SHA-256 was
`a57a4b88f05ae25ab93b67f3132f25fd3415a6d45ec206d53efa2f7dc1d2d8f3`.
Generation happened before the schema-9 implementation. No current database was downgraded.

`world.sql` is SQLite's dump of the populated schema-8 database followed by its observed
`user_version=8`. `expected.json` retains complete version-4 public observations from the base,
including histories, events, updates, snapshots, changes, photo and custom-emoji identities and
grants, exact downloaded bytes, and callback creation/retry dependencies. `identities.json`
contains only synthetic capabilities for this disposable World.

The fixture generator pins the base and source hash and refuses an existing output directory. For
manual reproduction, export only `src/gramlab` from the base to a disposable directory, select its
`src` with `PYTHONPATH`, and invoke `generate.py` in the pinned offline environment. The generator
never runs in tests. Remove the source export and regenerated output after comparing it with this
retained evidence.

Retained output checksums:

| File | SHA-256 |
| --- | --- |
| `world.sql` | `24a0490e97edd8c3ed5105fc6572861d5bad0560e7741a742bdcf9524f9e10e4` |
| `expected.json` | `f6495167c6ea8dc75fb6335cf35cc8ddf2642b94361b64e6dfc2f6265bc87f48` |
| `identities.json` | `4864f4c0551a34a43dd4cd1dfdde28b8ec62b11faf8d0c8cd3f10a4b3d69de1e` |
