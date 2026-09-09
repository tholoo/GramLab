# Prepare source repository for public collaboration

Type: task
Status: ready-for-agent
Work state: resolved
Owner: coordinator
Blocked by: none

Audit the current tracked tree and reachable Git history for credentials, private consumer context,
machine-specific details and unexpected generated artifacts. Review the existing license boundaries
and package notices for source sharing; this task does not claim an operational product or authorize
an Android binary release. Keep detailed matches, host paths and audit artifacts ignored.

Correct confirmed current-tree issues, verify local distributions include their existing licenses,
and update local/GitHub main with the audited integrated work. Keep pending worker feature branches
separate until their existing acceptance gates pass. Do not change repository visibility or replace
shared history before the cleanup is concrete, reviewed and explicitly authorized.

Add an authentic English-only renderer screenshot near the README top, preferably using the original
glass effects, if available without a speculative implementation change. Preserve screenshot source,
profile and original bytes; do not fabricate renderer progress. Include a short verified Python
example using the real library API and link to runnable setup.

## Audit checkpoint

The initial audit covers671 tracked files and2,334 distinct reachable Git blobs across557 commits.
Independent credential signatures and Gitleaks find no confirmed real credentials. Gitleaks flags
one deliberate public screenshot-correlation fixture; generic assignment matches are synthetic
redaction fixtures or XML attributes. These scans are bounded evidence, not an absolute guarantee.

Current tracked files exclude runtime caches, local configuration, signing keys, APKs and acquired
upstream source. Historical private consumer references and a machine-specific source path remain
reachable despite their removal from today's tree. Prepare a surgical cleanup separately, preserving
the current source tree and local work, before requesting authorization for shared-history replacement.

The root license map and Python package metadata must distinguish original MIT code, BSL-1.0 TDLib
adaptations, and separately distributed GPL Android patches/fixtures. Preserve existing rights;
clarifying metadata is not relicensing. Local wheel/sdist validation must confirm the Boost notice
and root scope map travel with the adapted modules. Android dependency/license audit remains a
separate binary-distribution requirement.

## Current-source verification

The Python package now declares MIT AND BSL-1.0. A real offline uv build produces a wheel and
source distribution containing LICENSE, LICENSES/BSL-1.0.txt and NOTICE, with the expected
License-Expression and no acquired Android source, application binary or cache material.
The exact README Python block passes through the public runner with the real contained echo bot
and creates its HTML report. README text contains no Persian characters or em dashes.

GitHub currently has no releases, workflow runs, workflow artifacts, open issues, wiki or
discussions to expose alongside the two existing branches. Repository visibility stays private
pending the user's publication decision. Normal Git author name/email metadata will be visible
if its history is published; this is separate from accidental private context.

## README capture and runnable example

The original English-only glass screenshot is retained unchanged in docs/assets/gramlab-preview.png,
with a portable capture record and upstream attribution beside it. The successful run verifies
the actual original shader, zero accounts, blocked external network, unchanged World state through
settings changes and restoration. It illustrates rich text and buttons, not complete media support.
Two failed startup attempts remain recorded separately; successful capture does not prove their cause.
Disposable owned guest disks were retired after preserving evidence.

The README command now selects examples/echo/hello.toml and its exact displayed hello.py, reusing
the existing real echo bot. The tracked manifest passes actual contained execution. Scoped typing
and Ruff cover the final example. No Persian text or em dashes appear in the README.

## Answer

The user approved the reviewed cleanup. Both GitHub branches were replaced together with an
atomic push and exact expected-tip leases. The 548 rewritten commits preserve each branch's
current tree byte for byte. All 2,325 reachable candidate blobs were scanned; no confirmed real
credentials or targeted private context remain. Git object integrity passes. GitHub branch tips
match the reviewed candidate, and local main and the integration checkout follow the clean history.

Source-sharing preparation is complete. The repository remains private; changing visibility is
separate from the approved history replacement. Normal author metadata is preserved. Rewriting
branch history cannot guarantee removal from cached commit views or existing clones. The README
example, original screenshot and source license checks above remain valid because their bytes
were unchanged by the rewrite. This does not establish operational or Android binary readiness.

Existing local worker branches retain their original history and pending work. Before resuming or
integrating one, the coordinator must migrate its reviewed changes onto the cleaned ancestry and
update its local assignment. Do not merge or push a legacy branch directly. Keep old build and test
commit identifiers as historical evidence, with the rewrite map retained in ignored audit storage.
