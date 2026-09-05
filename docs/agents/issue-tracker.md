# Issue tracker: Local Markdown

Issues and specs live in `.scratch/` and are version-controlled.

## Conventions

- One feature per directory: `.scratch/<feature-slug>/`.
- Specification: `spec.md`.
- One implementation ticket per file:
  `issues/<NN>-<slug>.md`, numbered from `01`.
- Record triage state in a `Status:` line using `triage-labels.md`.
- Append discussion under `## Comments`.
- Keep credentials and generated run artifacts outside the tracker.

## Skill operations

“Publish to the issue tracker” means write local Markdown.
“Fetch the relevant ticket” means read the referenced ticket file.
Neither operation authorizes publishing to an external service.

## Wayfinding

Use `.scratch/<effort>/map.md` for Notes, Decisions-so-far and Fog,
with one child file per ticket under `issues/`.

Record ticket kind in `Type:` and dependencies in `Blocked by:`.
For wayfinding tickets, track progress separately in `Work state:`
using `open`, `claimed` or `resolved`; retain `Status:` for triage.

Claim the first numbered open, unblocked ticket before working.
Resolve it by appending `## Answer`, updating its work state,
and adding a linked finding to the map.

The same work-state field can track implementation ticket progress. A triage label alone does
not mean a task has been implemented or verified. Dependencies refer to tickets in the same effort.
