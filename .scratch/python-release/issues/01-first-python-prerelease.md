# Publish GramLab 0.1.0a1

Type: task
Status: ready-for-agent
Work state: claimed
Blocked by: pending PyPI Trusted Publisher registration

Prepare the Python-only distribution, fast-forward the verified scenario-flow work into `main`,
push it, and publish the first alpha through a tag-triggered GitHub OIDC workflow. Do not publish an
APK, upstream Android checkout, test evidence, ignored runtime artifacts or credentials.

## Comments

The user explicitly authorized preparing `main` and publishing on 2026-09-13. PyPI's authoritative
JSON endpoint returned 404 for `gramlab` before release preparation. GitHub reports
`tholoo/GramLab` is public, its default branch is `main`, and the authenticated user has admin
permission. The release keeps the tested Python `>=3.13,<3.14` constraint and exact Pillow 12.3.0
pin; broadening either requires separate compatibility evidence.

The release candidate adds PEP 621 author, project URL, classifier and keyword metadata; an alpha
changelog; PyPI-safe absolute README links; and a tag-triggered Trusted Publishing workflow. The
GitHub `pypi` environment exists without long-lived secrets. Every referenced GitHub Action commit
was resolved through the GitHub API, and `actionlint` accepts the workflow.

`uv lock --check --offline` and `uv build --no-sources --offline` pass. The final local artifacts
are retained under `/tmp/gramlab-release-final.mNaXLc/`: the 155,581-byte wheel has SHA-256
`9e32acdb008e5f511674b13d3a3359cb2dfc0c84a2d78aae6a9c56b09191d7fb`, and the 139,188-byte
source archive has SHA-256
`af820fee1fbb3245c25509d2aa43e99fd79b7982fb3c91cdc5615e6f4d9820a5`. Both have exactly 45
entries, contain the public scenario flow and all required MIT/Boost notices, and exclude Android,
tests, Git state, caches and runtime artifacts. Both install in fresh environments, import the
public typed API, report version `0.1.0a1` and expose `gramlab --help`; Twine accepts both archives.
Configuration and local links validate across 292 Markdown files, and `git diff --check` passes.

The remaining blocker is the human-authenticated pending publisher registration at PyPI. The
ephemeral checked wizard `/tmp/gramlab-pypi-publisher-wizard.sh` opens the authoritative form and
supplies the exact non-secret identity fields. After registration, push annotated tag `v0.1.0a1`,
observe the release workflow, verify the public package, create the matching GitHub prerelease and
record its immutable URLs and hashes here.
