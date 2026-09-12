# Complete the representative operational workflow

Type: task
Status: ready-for-agent
Work state: resolved
Owner: coordinator
Blocked by: none; implementation tickets 113–114 and 119 resolved

Focused evidence across older APKs does not prove the requested operational milestone. After the
approved fidelity implementations and tickets110–116,119–120 are integrated, build one public real-bot workflow in
simulation and headless Android that composes the approved surfaces rather than substituting a
narrow explicit subset.

The final workflow must include Persian/English ordinary text; normal rich automatic detection plus
explicit URL/mention/custom emoji; row/inline rich and ordinary buttons; callback-driven edits;
PNG and JPEG upload/reuse; default and forced ordinary documents; true photo and document albums;
static and transparent animated custom emoji including an incoming entity and rich-button label;
restart/recovery; and complete World/Bot API/bridge/interaction equality. Mini Apps remain deferred.

Own final example/test paths only after dependencies freeze: `examples/representative/**` and
`tests/test_representative_workflow.py`. Coordinator owns shared setup, compatibility, handoff and
reporting docs. Preserve one self-contained report with original screenshots, exact run/APK/source
identity, zero accounts, loopback-only observations, component filesystem isolation and no private
consumer or machine details. A pre-album or explicit-detection run may be retained as a labeled
preflight but cannot resolve this ticket.

Before acceptance, rerun the complete current non-Android inventory once and collect the exact
Android case manifest. Run every current-APK Android case serially under `android-gate`, fail on
unexpected skips, and reconcile the final compatibility matrix and reproducible setup from those
results. Do not reuse the stale historical 53-case count.

## Comments

### Approval-independent current-source preflight

At commit `b3217bd`, cache-disabled collection found exactly1,247 non-Android and68 Android cases
with no overlap. The ordered manifests are retained at
`artifacts/current-source-{non-android,android}-collection-01.json`; their SHA-256 values are
`9d9d83ccb990b22f17a8798fc1fbf834a044dfc956ee59b5506807d934e85603` and
`f49d81b3fa3f76e6820c749e36b5ac9924e6e8bb5e56e3d0445445593720b2d8` respectively.

The complete host inventory then passed **1,247/1,247** in111.47 seconds with88.12% coverage and no
failures, errors or skips at `artifacts/current-source-core-20.xml` (SHA-256
`d307bbb7830a875dae4e63883264e431ab1e76f126e5763f0f34efc5cbf005e3`). It ran inside a fresh user
and network namespace with loopback as its only interface. The contributor and manual-CI recipes
had omitted the integrated document-v5, custom-emoji-v5 and residual-rich strict typing scopes;
adding those three commands makes the complete current static recipe70 commands. Static19 passes
all70 at
`artifacts/coordinator-static-19.log` (SHA-256
`347f729d75085a864b1f42539d7f30640dd39824cb4cc3f40fa2a759235cd0d2`). A separate direct
invocation of the manual-CI validator passes configuration and local-link checks across278 Markdown
files; its one-line terminal result is not misrepresented as part of the static log.

No Android case ran during this preflight. The complete68-case normal30 gate is intentionally not
started before the pending album contract because album delivery requires a new normal31 APK and a
new final inventory. This collection is a precise baseline, not final native acceptance.

## Answer

Commit `5cbe830` adds the public bridge-v6 representative bot/scenario and its acceptance test. It
composes bilingual ordinary text, automatic and explicit rich entities, ordinary and rich
callbacks, edits, exact callback replay across bot restart, PNG/JPEG upload and reuse, default and
forced documents, true photo/document albums, and static/animated custom emoji.

The retained normal31 runner result at
`artifacts/representative-android-03/test_representative_workflow_u0/headless-android/result.json`
passes in 148.200 seconds with 17 final messages and five inspected original captures. Scenario,
World, Bot API, bridge-v6 and native input observations compare equal; original bytes, media-group
topology and custom-emoji descriptors are hash-pinned. The guest records zero accounts,
loopback-only networking and the required component filesystem separation. The self-contained
report beside it has SHA-256
`51b4f40008fcc0e081722b63680534141e6eb8f20158f58b90f8fcabd3a38851` and contains no private
consumer or machine details.

The enclosing JUnit failed only after the successful runner because its assertion helper restored
one redacted accessibility field at only one valid nesting location. The corrected helper replayed
the complete retained result successfully. Per the user's instruction, the successful emulator
workflow was not repeated. The prior full host gate passed 1,508/1,508; the representative
simulation, 17 affected rich-interaction tests and scoped static checks pass. Current collection is
1,553 non-Android and 74 Android cases. The normal31 diagnostic plus exact failed-case reruns are
recorded as case-level union evidence, not mislabeled as a clean aggregate rerun.

Mini Apps, external conformance, production emoji entitlement, HTML parse modes, grouped-media
edits and interactive mode remain outside this resolved milestone ticket.
