# Android source feasibility: candidate for review

Research date: 2026-09-05. This is source inspection for [ticket 01](../../.scratch/android-offline-foundation/issues/01-validate-android-seam.md),
not an approved architecture, working adapter, reproducible build or isolation certificate.
Individual public source files and Git tree metadata were read into a temporary research directory;
no complete checkout, dependencies, APK, account, bot or Android runtime were acquired or executed.

The evidence supports investigating an offline replacement for the client's request/update exchange
while retaining its controllers, storage and UI. It does **not** establish that intercepting one
method is sufficient. Initialization, native housekeeping, HTTP media and WebViews require additional
boundaries. The proposed first implementation remains the real bot → rendered message → actual
button action → callback → bot edit → recovery loop from the [foundation spec](../../.scratch/android-offline-foundation/spec.md).

## Candidate pin and build requirements

The candidate is official Telegram Android **12.10.1 (7038)**, commit
`62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`. This exact revision is a proposal for review; no claim is
made that GramLab builds it. The upstream commit identifies the release; the repository README
identifies the official Android source. [Commit](https://github.com/DrKLO/Telegram/commit/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c),
[pinned README](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/README.md).

| Requirement | Exact source evidence and implication |
| --- | --- |
| Gradle / build plugins | Wrapper **8.11.1**; Android Gradle plugin **8.10.1**, Kotlin plugin **2.1.0**. Dependency repositories include Maven Central, Google and Huawei. Provisioning must resolve and hash the actual dependency closure before offline builds. [Wrapper](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/gradle/wrapper/gradle-wrapper.properties), [root build](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/build.gradle). |
| Java / SDK baseline | Upstream Docker starts from `gradle:8.11.1-jdk17`; installs command-line tools **15859902**, SDK **36**, build tools **36.0.0**, NDK **27.2.12479018**, CMake **3.22.1**. Its image tag and downloaded packages are not content-addressed, so copying the Dockerfile alone does not prove reproducibility. [Dockerfile](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/Dockerfile). |
| Android library | Compile/target SDK **36**, minimum SDK **21**, Java source/target **8**, native target `tmessages.49`, static C++ runtime. Includes Firebase/GMS, billing, integrity, reCAPTCHA and media dependencies. These need offline-variant initialization/manifest review even when no services image is used. [Library build](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/build.gradle). |
| Existing test application | `TMessagesProj_AppTests` has AndroidJUnitRunner and debug instrumentation; its `afat` flavor includes **x86_64** as well as x86 and ARM, minimum SDK **26**. It uses a release manifest and upstream signing configuration, so it is a source of conventions, not an already isolated test app. Its packaged locale list excludes Persian; a Persian UI profile would need resource selection review. Persian message text is a distinct requirement. [Test application build](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj_AppTests/build.gradle). |
| Native closure | CMake imports FFmpeg, BoringSSL, codec and other static archives, builds `tgnet`, and imports a Rust tlottie archive. The archive/source relationship and per-ABI inputs must be inventoried; Java-only rendering substitutes would not reproduce this build. [Native build](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/jni/CMakeLists.txt). |

Recommend an Android **API 36 x86_64** dedicated emulator profile, subject to the separate host/runtime
proposal and user approval. SDK compile level does not itself select an emulator image. Exact emulator
binary/image revision, archive hashes, WebView package/version, GPU renderer, fonts, display density,
locale and animation settings remain runtime manifest inputs. Upstream source does not pin them.
Emulator networking includes a virtual router and a special host-loopback address; that routing must
terminate inside the isolated run environment. [Android emulator networking](https://developer.android.com/studio/run/emulator-networking).

The following gitlinks were resolved from the exact, untruncated Git tree; repository locations come
from its `.gitmodules`. These are provenance metadata, not downloaded or licensed dependency audits.
Nested submodules and static archives remain to be reconciled during approved acquisition.
[Pinned Git tree API](https://api.github.com/repos/DrKLO/Telegram/git/trees/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c?recursive=1),
[submodule declarations](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/.gitmodules).

| Submodule path under `TMessagesProj/` | Commit |
| --- | --- |
| `jni/third_party/dav1d` | `54706fc6bc0cdecab7e9593974a4039cc038fca7` |
| `jni/third_party/ffmpeg` | `45f1910444f34b02621f9f0426ea1a538a613c41` |
| `jni/third_party/libvpx` | `1024874c5919305883187e2953de8fcb4c3d7fa6` |
| `jni/third_party/libyuv` | `28ce69c2744a6aafdb58564e7b884aec3f66be5f` |
| `jni/third_party/openh264` | `652bdb7719f30b52b08e506645a7322ff1b2cc6f` |
| `jni/third_party/xiph/ogg` | `be05b13e98b048f0b5a0f5fa8ce514d56db5f822` |
| `jni/third_party/xiph/opus` | `22244de5a79bd1d6d623c32e72bf1954b56235be` |
| `jni/third_party/xiph/opusfile` | `a55c164e9891a9326188b7d4d216ec9a88373739` |
| `jni/tlottie` | `3ce946c9ede5ece8beead2edd9beab68718d990e` |
| `lib/jlatexmath` | `919e50b2f6f64b04b712cdb13d558ff9ecf9c8ed` |

## Schema and license boundary

`TLRPC.LAYER` is **229**. The test generator also selects 229, while the tree includes both
`tlscheme/229.json` and `230.json`: choosing the highest schema filename would therefore give the
wrong declared layer for this candidate. The generator reads Android Java classes and upstream
schema resources to produce Kotlin models/tests; those generated outputs must stay within the
client-derived boundary. [TLRPC](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/TLRPC.java#L73),
[generator](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/buildSrc/src/main/kotlin/com/example/GenerateSchemeTask.kt),
[schema 229](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj_AppTests/tlscheme/229.json).

Observed SHA-256 of exact raw source bytes:

| File at candidate commit | SHA-256 |
| --- | --- |
| `TMessagesProj_AppTests/tlscheme/229.json` | `168d01aee47048488e5c335bc55772b11e8e713cbcdc073643b5b89acb587be2` |
| `LICENSE` | `8177f97513213526df2cf6184d8ff986c675afb514d4e68a404010521b880643` |
| `TMessagesProj/src/main/java/org/telegram/tgnet/ConnectionsManager.java` | `9b1f713e9cce80b75810b911cc64f783ddd59d40638f144879cfcfc6096e6ffb` |

The root license text is GPL version 2; inspected source headers including TLRPC specify version 2
or later. No independently permissive grant was established for the checked-in schema. Proposed
default: keep all imported TL definitions, generators, client object mappings and adapter patches
in the identified copyleft component; write the Python world and its semantic IPC vocabulary
independently. This is a provenance recommendation, not a legal conclusion that IPC settles
distribution obligations. [Pinned license](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/LICENSE),
[source header](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/TLRPC.java#L1).

There is a concrete packaging concern to retain in the acquisition audit: the root build excludes
assets named `licences` while stripping JLatexMath fonts. GramLab must independently preserve
applicable notices/source information and audit the retained fonts rather than inherit that
packaging choice unquestioned. Distinct unofficial branding and dedicated local signing are also
needed. [Packaging rule](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/build.gradle#L18),
[upstream application guidance](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/README.md).

The official Bot API documentation currently identifies **10.3, 2026-08-24**. It documents
`sendRichMessage`, `InputRichMessage`, block entities and later rich-message button/document additions.
Recommend 10.3 as the first named compatibility target, with every implemented method/surface
enumerated. That does not imply complete 10.3 support or a one-to-one relation between Bot API
versions and TL layers. The documentation is mutable: retain reviewed contract fixtures and dated
source attribution when implementing them. [Bot API changes](https://core.telegram.org/bots/api#recent-changes),
[rich-message method](https://core.telegram.org/bots/api#sendrichmessage).

## Concrete source seams and uncertainties

The following rows separate inspected behavior from proposed modifications. Every proposal needs
an isolated prototype after review; no row claims an already complete request inventory.

| Surface | Observed behavior and proposed seam |
| --- | --- |
| Request/response/update exchange | `ConnectionsManager.sendRequestInternal` serializes a TL object and dispatches `native_sendRequest`; callbacks are token-tracked and delivered through the stage queue. `onUnparsedMessageReceived` decodes an `Updates` object and feeds `MessagesController.processUpdates`. Propose replacing dispatch before native serialization with a client-side semantic adapter, preserving queue ordering, cancellation, GUID binding, timestamps and completion/error semantics. Direct native clock, connection-state, pause/resume, proxy, DNS and housekeeping methods also require an offline implementation. DNS fallback includes Google and Mozilla/Cloudflare HTTPS resolvers. Unsupported operations must produce a recorded capability failure with no native fallback. [ConnectionsManager](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/ConnectionsManager.java#L387). |
| Native lifecycle | Native `init` loads configuration and creates a network thread; `initDatacenters` contains production and Test-DC IPv4/IPv6 addresses. Propose a compile-time offline transport guard that prevents this networking lifecycle, while retaining JNI facilities needed for rendering, buffers, database and codecs. Need to trace all JNI entry points and assert that a missed call fails observably. [Native manager](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/jni/tgnet/ConnectionsManager.cpp#L3648). |
| Authentication | The handshake selects trusted RSA keys/fingerprints and performs the native key exchange. Redirecting a DC to a local port does not implement it. The proposed bridge avoids the MTProto wire handshake entirely, consistent with the existing scope. [Handshake](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/jni/tgnet/Handshake.cpp#L353). |
| Startup and background work | `ApplicationLoader` loads native libraries, initializes controllers/connections for every account slot, checks unsent messages, initializes push, starts billing and registers connectivity callbacks. `onCreate` schedules push-service work and proxy rotation. Propose a dedicated offline application variant that selects its adapter before any account/controller initialization, prevents real service initialization and instruments unexpected startup requests. Retain UI/media initialization needed by the renderer. [ApplicationLoader](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/ApplicationLoader.java#L190). |
| Synthetic identity | `UserConfig.isClientActivated` tests whether `currentUser` exists; configuration serializes that user. `setCurrentUser` also triggers premium-related controller work. Propose a synthetic self-user and bot peer installed through client configuration/controller methods before normal activity routing, under a dedicated run directory. An activated Java identity is not proof native authentication has been disabled. [UserConfig](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/UserConfig.java#L237). |
| Entry activity | `LaunchActivity` branches on account activation and constructs login UI when needed. The offline entry must reject an absent/mismatched synthetic run descriptor instead of navigating to login. Exact ordering must be proven from a clean app-data launch. [LaunchActivity](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/LaunchActivity.java#L412). |
| Actual callback | `ChatActivity` routes the message-cell button delegate to `SendMessagesHelper.sendCallback`. The helper requests `messages.getBotCallbackAnswer` with peer, message ID and callback bytes; its response handling clears pending state and supports cached answers. Propose translating that request into the same world callback event a simulation-only action creates; return the answer when the real local bot calls `answerCallbackQuery`. Set the first proof's callback cache lifetime to zero to make repeated taps observable. [ChatActivity](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/ChatActivity.java#L40831), [SendMessagesHelper](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/SendMessagesHelper.java#L3888). |
| Button schema | Layer 229 uses `TL_keyboardInlineButton` with typed callback behavior (`TL_inlineButtonTypeCallback`); historical `TL_keyboardButtonCallback_layer228` is private compatibility code. Use the current pinned classes, not names remembered from older clients. [Keyboard schema](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/tl/TL_keyboard.java#L274). |
| New message and edit | `TL_updateNewMessage` and `TL_updateEditMessage` carry a message, `pts` and `pts_count`. Propose producing those through the adapter from authoritative world changes and passing the normal updates envelope into the controller; do not mutate message-cell content directly. [Update objects](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/tl/TL_update.java#L2536). |
| History and recovery | `MessagesController` requests history/dialogs, obtains initial update state and recovers differences. `loadCurrentState` retries non-401 errors, so simply returning generic errors to every unsupported startup request risks a retry loop. Propose a traced minimum contract for dialogs/history/users/configuration/update-state/difference; distinguish valid empty responses from unsupported behavior. Cursor gaps and edits must pass its normal ordering checks. [MessagesController](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/MessagesController.java#L16230). |
| Persistence and cleanup | `MessagesStorage` owns `cache4.db`, WAL/SHM companions and persisted difference parameters (`seq`, `pts`, `date`, `qts`), with asynchronous storage-queue operations. Treat this as the renderer's replica/cache; propose retaining it on renderer restart and testing replay/reconciliation from the world. World state must survive independently. Reset must close processes and remove only validated run-owned data, including preferences/media/WebView storage, not merely the main database. [MessagesStorage](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/MessagesStorage.java#L315). |

## Media, push and Mini App boundary

| Path | Evidence and proposed treatment |
| --- | --- |
| Telegram media transfer | `FileLoadOperation` includes normal, web-file and CDN transfer paths, chunk offsets, caching and CDN validation. Propose satisfying supported local file requests with deterministic fixture bytes while preserving the original download/decoder/cache behavior; reject DC migration/CDN redirects unless explicitly simulated. Missing fixture IDs must never trigger external retrieval. [Download operation](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/FileLoadOperation.java). |
| Upload | `FileUploadOperation` uses `upload.saveFilePart` / `upload.saveBigFilePart` and request cancellation. A later media interaction must implement chunk assembly, stable local IDs, cancellation and recovery against world-owned assets. Preloading a local image alone would not prove upload semantics. [Upload operation](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/FileUploadOperation.java#L505). |
| HTTP images/files | `ImageLoader` opens HTTP connections itself, including redirects and special image sources. This bypasses the TL request seam. Propose URL admission and redirect validation against the local fixture allowlist, plus OS isolation of every process. [ImageLoader](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/ImageLoader.java#L225). |
| Custom emoji | `AnimatedEmojiDrawable` fetches missing document metadata with `messages.getCustomEmojiDocuments`, persists it, and uses the normal image receiver. Missing IDs in a successful partial result are requested again. A custom-emoji proof therefore needs complete synthetic metadata and licensed/original local bytes, and an explicit failure policy that prevents endless retries. Preserve upstream drawing. [AnimatedEmojiDrawable](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/Components/AnimatedEmojiDrawable.java#L309). |
| Manifest/service startup | The main manifest grants Internet access and declares many receivers/services; the release overlay declares Firebase messaging. Dependency manifest merging may add providers beyond these files. Inspect the **merged APK manifest**, disable external push/analytics/billing/account-sync entry points in the offline variant, and test restart/background launch. A no-Google-services image is not the enforcement boundary. [Main manifest](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/AndroidManifest.xml), [release overlay](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/config/release/AndroidManifest.xml). |
| Mini Apps/WebViews | The pinned path is `ui/web/BotWebViewContainer.java`. It enables JavaScript, installs the Telegram bridge, loads URLs, checks trusted origins and handles navigation/interception; some paths open HTTP connections or delegate URLs to the browser. Propose preserving that bridge/UI with local-only origins and synthetic initialization data, restricting top-level/subresource/navigation/popup/external-intent paths and testing WebSocket/service-worker/native escapes under OS isolation. File access settings alone are insufficient. Pin the actual WebView provider and clear its run-owned data on reset. [BotWebViewContainer](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/web/BotWebViewContainer.java#L432). |

## Accessible and rich rendering proof candidates

Use a private synthetic user–bot dialog, an English/Persian message, and one uniquely labelled inline
callback button. `ChatMessageCell` exposes button title, button class, bounds and accessibility click
action; performing the action invokes the same button delegate used by the UI. This is a promising
semantic automation target, not proof an emulator's UI automation sees it. The prototype must capture
the hierarchy and screenshot, select the actual node and observe the bot callback before claiming the
tap worked. [Accessibility node creation](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/Cells/ChatMessageCell.java#L27610),
[click dispatch](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/Cells/ChatMessageCell.java#L27882).

For the rich exploration case, propose a structured paragraph with Persian/English text, a small
table and an expandable quotation, using explicit Bot API rich blocks rather than an unverified
Markdown parser. The Android `TL_iv.RichMessage` contains RTL/partial flags, blocks, photos and
documents. `RichMessageLayout` consumes those blocks, including table and quotation layouts, and
uses upstream text layout. That makes it a credible fidelity target once the Bot API-to-TL mapping
is verified. [Rich object](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/tl/TL_iv.java#L195),
[layout](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/RichMessageLayout.java#L374),
[Bot API rich blocks](https://core.telegram.org/bots/api#inputrichmessage).

The first rich case should visibly identify unimplemented block/media/emoji capabilities. It does not
replace the later media, custom-emoji, Mini App or full multilingual requirements. Pixel snapshots
need semantic assertions too; a screenshot cannot prove callback delivery, persistence or egress.

## Choices to review before prototype work

1. **Client/runtime baseline:** accept this exact source/layer and an API 36 x86_64 emulator candidate,
   then provision immutable source/dependency/runtime inputs separately from isolated execution.
2. **Bridge and schema boundary:** prefer a narrow, independently defined semantic protocol with
   client-side TL translation inside the copyleft component. Raw TL IPC would reduce translation in
   the client but moves schema decoding/provenance obligations toward the core. Do not adopt either
   as a public SDK contract until the first loop exposes its real requirements.
3. **State/replay:** propose a world-owned transactional state and ordered mutation/update journal;
   renderer SQLite remains a replica. Persist world identity, bot update offsets, message IDs,
   callback correlation and client update cursors together with version/seed information. Exact
   engine, acknowledgement/retry semantics and journal retention need review and behavioral proof.
4. **Runtime isolation:** use independent OS/runtime egress enforcement enclosing emulator, bot,
   simulator and local assets, with no inherited host Internet route or broad proxy/socket mounts.
   Test deliberate IPv4/IPv6/DNS/redirect/WebSocket/native/WebView/background attempts. The separate
   host investigation determines whether system changes are required; no services were enabled by
   this source research.
5. **Bounded prototype gate:** first trace clean synthetic startup under enforced isolation, then
   implement the observed minimum request contract and exercise the complete message/tap/edit and
   restart sequence. Stop and report an exact renderer/build/isolation failure before considering
   changes to client, fidelity or license strategy.

Still unproven: the full startup request inventory; JNI behavior without the native network thread;
clean synthetic activation ordering; instrumented accessibility visibility; signed offline APK build;
asset/dependency license inventory; resource usage; WebView behavior; deterministic replay; and actual
zero-egress execution. Source inspection provides actionable seams and test obligations, not a
successful Android adaptation.
