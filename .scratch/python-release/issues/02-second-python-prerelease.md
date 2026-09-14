# Publish GramLab 0.1.0a2

Type: task
Status: ready-for-agent
Work state: claimed
Blocked by: none

Publish the Python-only second alpha from the verified `main` history. Include the persistent and
interactive playground, synthetic group support, stronger native rich-input recovery, independent
per-bot runtime profiles and the faster semantic/native playground handoff. Do not publish an APK,
upstream Android checkout, tests, runtime artifacts or credentials.

## Comments

The user explicitly authorized merging GramLab `main` and publishing a new release on 2026-09-14.
Version `0.1.0a2` advances the existing experimental 0.1.0 alpha line without claiming stable API
compatibility. Release verification must follow `docs/development/releasing.md`, retain exact
artifact hashes, verify both archives in fresh isolated environments, and confirm the published
PyPI and GitHub prerelease records before resolving this ticket.

The release candidate passes Ruff lint and formatting, strict source typing, lockfile validation,
and distribution-boundary inspection. The wheel and source archive each contain 47 entries, the
public scenario flow and every required MIT/Boost notice, while excluding Android source, tests,
Git state, caches and runtime artifacts. Fresh isolated environments install both archives, import
the public API, report version `0.1.0a2` and execute `gramlab --help`.

The pre-publication artifacts are retained under `/tmp/gramlab-0.1.0a2.U4c6ie/`. The wheel has
SHA-256 `95ed078546bd3e15d1b44c616ef717d2bf6bb1f3aa9faeff4e52f9220b08d69a`; the source
archive has SHA-256 `38386ed312d7afaab48a766ed4c0ea66bab9235608326127327f932885260667`.
