# Publishing the Python package

GramLab publishes only the independently written Python distribution. The Telegram Android patch
queue, acquired source, APKs, tests and runtime artifacts are not package contents and have separate
licensing and distribution requirements.

## Release contract

1. Resolve a release ticket and update the version and changelog on a clean branch based on `main`.
2. Run the applicable repository checks and build with `uv build --no-sources --clear`.
3. Inspect and smoke-test both artifacts in isolated environments. Confirm the wheel contains
   `LICENSE`, `LICENSES/BSL-1.0.txt` and `NOTICE`, and contains no Android-derived files.
4. Fast-forward and push `main` only after the exact release commit is verified.
5. Configure the GitHub `pypi` environment and a matching PyPI Trusted Publisher.
6. Create and push an annotated `v<version>` tag. The release workflow builds once, transfers the
   artifacts to a separate OIDC-enabled publication job, attests them and publishes to PyPI.
7. Verify the PyPI metadata and install the published version into a new isolated environment.
8. Create a GitHub prerelease with the same tag and record the URLs and hashes in the ticket.

PyPI files are immutable. Never rebuild an existing version or move a published tag. A failed
partial upload may only be retried with the exact same artifact bytes.

## Trusted Publisher identity

The first release uses a pending publisher configured at PyPI with these exact public values:

- PyPI project: `gramlab`
- GitHub owner: `tholoo`
- Repository: `GramLab`
- Workflow: `release.yml`
- Environment: `pypi`

No long-lived PyPI token is stored in GitHub or the repository.
