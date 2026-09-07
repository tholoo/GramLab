# Make the first synthetic photo receiver cancellable

Type: bug
Status: ready-for-agent
Work state: claimed
Blocked by: none

Coordinator owns this ticket, append-only native patch 0021 and series/README integration.
Do not change original rendering, gestures, profiles, timeouts or fixtures to conceal the bug.

Two unchanged normal20 native runs show an original cancel tap 1.3–1.5 seconds into a gated
photo transfer. The control changes from cancel to download, but no transfer cancellation occurs.
A separately fingerprinted diagnostic APK then records both image and thumbnail receiver tags
as zero, with no queued receiver removal. The original cell attachment and ImageLoader paths
both start the same transfer. Source confirms the first ImageLoader registration assigns its
zero-initialized counter, while cancellation treats tag zero as absent.

Correct reserved-zero allocation at the synthetic local-photo ImageLocation boundary. Preserve
ordinary non-synthetic upstream behavior and the original renderer. Verify the same first-photo
native cancel/retry scenario without warming up an unrelated image or altering timeouts. Also
check shared consumers and the unchanged photo fault/codec/lifecycle gates. Native wraparound
is not dynamically covered; source review must show the allocation guard also handles a zero
counter after wrap. Keep the cache/edit failure as a separate finding; do not suppress original
MessagesStorage cleanup to pass its prior assertion.

Ignored evidence: `artifacts/media-interaction-native-01.xml`, `media-interaction-native-02.xml`,
and `artifacts/photo-cancel-diagnostic-native-01/photo-cancellation-diagnostic.log`. The diagnostic
source overlay was removed and all eight normal20 source fingerprints restored; its separate APK
and provenance remain retained. Diagnostic runs do not replace normal native acceptance.


## Focused normal APK result

Patch 0021 compiles in 3m21s and the first-photo original cancel/retry case passes retained
transfer/cache/binding assertions: cancellation occurs after 1.21 seconds, release after 1.84
seconds, and only explicit retry starts the successful replacement request. Absent/wrong-World/
missing-message activation assertions pass. The loading screenshot was taken before visible
cells, so corrected capture ordering needs fresh native evidence. Shared-consumer and ordinary
late-edit cases remain failed for separately observed upstream behavior; unchanged fault/codec
and combined native regression are still required. Keep this ticket claimed.
