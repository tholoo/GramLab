# Reject integration checks importing another worktree

Type: bug
Status: ready-for-agent
Work state: fixed and focused verification passed; combined gate pending
Blocked by: none

A worker ran bare `uv sync` after changing directories while inheriting the coordinator's
`UV_PROJECT_ENVIRONMENT`. This redirected the primary editable install to the worker source.
Consequently, source hashes from the primary checkout did not establish what host Python loaded.
The direct import-origin assertion failed, and a rich-link integration selection produced six
failures and 100 passes while the worker checkout lacked the new feature. Preserve these results
as environment diagnosis, not integrated acceptance.

Coordinator repaired the primary install through its own pinned shell using locked offline
package reinstallation. Pytest now checks its imported GramLab path against the checkout that
owns `tests/conftest.py` before collection. A deliberately wrong `PYTHONPATH` exits 4 with the
specific checkout diagnostic; the correct environment passes the 144 combined feature tests.
Contributor and parallel-work guidance explain explicit environment targeting. The guard changes
development verification only; it does not alter simulator runtime or native fidelity.

The recent 27-case native continuation and isolated list restart control began after the install
was redirected. Their observed outcomes and original PNG/XML/logs remain retained, but they do
not establish combined integration acceptance. Earlier core and focused quoted-code rendering
runs predate the environment change. Rerun the applicable combined native inventory on the next
integrated normal APK with verified imports rather than treating unchanged on-disk source as
sufficient proof. Local timestamps, paths and manifests stay in ignored evidence.
