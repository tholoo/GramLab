# Keep the native rich catalog canonical after text normalization

Type: bug
Status: ready-for-agent
Work state: claimed by coordinator
Blocked by: none

The normal Android gate stopped with 19 passes and one catalog assertion failure. The retained
native result differs from the tracked comprehensive fixture only in preformatted text: its tab
became one ASCII space. The [pinned normalization contract](../../../docs/development/rich-text-cleaning.md)
requires that transformation even within preformatted RichText. Determine whether the catalog
expectation, core transformation or native projection is wrong before changing behavior.

Add a fast public World-boundary check that the fixture advertised as canonical survives the
same send/snapshot path used by the native catalog. Record failure before correcting the fixture,
then verify the original complete native result and rerun the affected native check. Keep the
normal APK and production normalization unchanged if the evidence identifies only stale fixture
content. Retain the partial gate and resume its remaining scope explicitly; never label a partial
run as a passing full gate. Coordinator owns the fixture, test and shared evidence documentation.

## Diagnosis and correction

The fast complete-message check fails in 0.22 seconds before fixture correction. Both the public
World output and the retained native catalog have exactly the source-required single space;
only the fixture was stale. Replace that one tab in the canonical fixture, retaining newline.
The World canonical-catalog and real-bot checks then pass together in 1.96 seconds, and scoped
Ruff, formatting and strict typing pass. The complete retained native catalog now equals the
fixture. This re-evaluated evidence is not a new guest run; native rerun and remaining gate scope
are still required. No production source or APK change was needed.
