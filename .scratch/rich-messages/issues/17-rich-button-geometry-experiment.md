# Observe original rich-button geometry before choosing public targeting

Type: task
Status: ready-for-agent
Work state: claimed by coordinator; experiment preparation
Blocked by: tickets 14 and 15 for native execution

The [shared button contract](../../../docs/development/rich-buttons-contract.md) separates actual
rich content from public input design. Prepare an explicitly opt-in GPL experiment outside the
normal patch series. It reads the selected original message cell after drawing, retains geometry
and action identity in app-private output, and never dispatches an action itself. Use original
layout objects and offsets rather than a Python layout approximation. No exported component,
network endpoint, accessibility node or renderer change is assigned.

The first bounded fixture has one top-level callback row and one paragraph with an inline callback.
The real bot sends the actual rich representation, answers the first callback, then answers and
edits after the second. Observe one matching native message/persona, tap each freshly observed
original button once through guest input, and compare complete callback identity, bot answers,
world/native edit and cold restart. Retain original PNG/XML and geometry; inspect the rectangles
against actual images. Wrong message identity or absent activation must yield no usable target.
All existing accounts and guest isolation requirements apply. Do not substitute native marker
content for the authoritative message.

The experiment is separate from regular APK acceptance. Record independent normal/experimental
APK fingerprints, source/patch differences and terminal resource handles in ignored artifacts.
A compiled helper or source-derived coordinate formula is not input proof. Nested/RTL/alignment,
copy/disabled behavior, duplicate labels and stale edits follow after the first observed callback
loop; the full inventory and public targeting decision remain open.


## Preparation evidence

The opt-in [GPL helper and installation patch](../../../clients/android/experiments/rich-actions/README.md)
are prepared outside the normal series. Scoped javac passes against the pinned SDK, compiled
client and cached AndroidX dependencies. The installation patch applies with zero fuzz to a
private copy and changes only the expected call. An independent source review confirmed the outer
cell top-padding translation, identified the need to reject blockquote transitions, and retained
explicit stale-output/freshness caveats. Compilation and source review are preparation evidence;
no experimental APK, geometry observation or rich-button input has run yet. Ticket remains claimed.

The coordinator has since prepared an independent copy of the normal source and build caches.
All 43,250 files in the worker's fresh pinned 13-patch export compare byte-for-byte before the
experimental overlay. The helper is added and the one-call installation patch applies with zero
fuzz; the normal source remains unchanged. The separately isolated offline experimental build passes in 2 minutes 8 seconds; its APK
is retained separately from the normal APK. These checks establish source preparation, not geometry or input behavior.

The frozen ticket 19 Python harness passes its real-bot simulation and scoped static checks. A
separate read-only review found no blocking source defect in callback/event correlation, wrong
message identity, bounded freshness, single ordinary taps or failure retention. Native execution
and original rectangle-to-PNG inspection remain coordinator acceptance work after the normal gate.
