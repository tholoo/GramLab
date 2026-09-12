# Publish GramLab 0.1.0a1

Type: task
Status: ready-for-agent
Work state: resolved
Blocked by: none

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

The only account-side blocker was the human-authenticated pending publisher registration at PyPI.
The ephemeral checked wizard `/tmp/gramlab-pypi-publisher-wizard.sh` supplied the exact non-secret
identity fields without collecting a token or password.

The user registered the exact pending publisher on 2026-09-13. Annotated tag `v0.1.0a1` points to
release commit `2d0ec88e806fba189ef420f0745c74b464255e85`. GitHub Actions
[run 34718534527](https://github.com/tholoo/GramLab/actions/runs/34718534527) completed both the
separated build and OIDC publish jobs successfully, including distribution inspection, isolated
wheel/sdist smoke tests and attestation generation.

[PyPI 0.1.0a1](https://pypi.org/project/gramlab/0.1.0a1/) serves both non-yanked artifacts with
the exact locally audited sizes and hashes above. A new index-resolved environment installed
`gramlab==0.1.0a1`, imported `Scenario` and `Conversation`, reported the expected distribution
version and executed `gramlab --help`. The matching public
[GitHub prerelease](https://github.com/tholoo/GramLab/releases/tag/v0.1.0a1) is published. No APK,
Android source, credential, test tree, cache or runtime artifact was distributed. The first Python
prerelease is resolved; future files for this version must never be rebuilt or replaced.
