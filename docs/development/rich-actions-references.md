# Rich links and buttons: source findings

Research checkpoint against Bot API server `2efabc722e9493b9cac450233198d09e5cea0573`,
TDLib `bc9c263e2bfee06aaab41e82db51a103376030bc`, and Android
`62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`. These findings do not establish live server
acceptance, native rendering or input behavior. No runtime, account or DC was used.

## Shapes and canonical output

| Feature | Input shape |
| --- | --- |
| URL text | `{"type":"url","text":RichText,"url":"…"}` |
| Email text | `{"type":"email_address","text":RichText,"email_address":"…"}` |
| Phone text | `{"type":"phone_number","text":RichText,"phone_number":"…"}` |
| Button row | `{"type":"buttons","buttons":[RichMessageButton],"align":"left"}` |
| Inline rich-text button | `{"type":"button","button":RichMessageButton}` |

The pinned server reads these shapes in its [rich text parser](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L12183)
and [row parser](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L12369).
Button styles are case-normalized; missing, empty or `default` becomes omitted default output.
Alignment accepts exact left/center/right; missing or empty is omitted. Button output retains
rich text and the selected action. Login actions serialize as URL actions; user-profile actions
as `tg://user?id=…`; disabled actions as `{}`. See the [button parser](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L10378)
and [serialization](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L18115).

## Documentation versus pinned conversion

Current [official button documentation](https://core.telegram.org/bots/api#richmessagebutton)
specifies rich text, optional primary/danger/success/link style, and exactly one action among URL,
callback, Web App, login URL, three switch-inline forms, copy text and disabled. Link style is
callback-only; labels allow plain text, custom emoji and date/time entities. The documented
[row limit](https://core.telegram.org/bots/api#inputrichblockbuttons) is 1–8 buttons. Callback
payloads are 1–64 bytes and [copied text](https://core.telegram.org/bots/api#copytextbutton)
is 1–256 characters. These mutable pages are distinct from the immutable source observations.

The pinned [action parser](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L10390)
selects the first recognized action instead of rejecting multiple actions; nonempty URL precedes
nonempty callback data. It also recognizes pay/game actions outside the documented rich-button
inventory. GramLab's existing strict field/action policy must not silently broaden to match that
parser permissiveness. Pinned [string readers](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/tdutils/td/utils/JsonBuilder.cpp#L711)
also accept JSON numbers as strings; strict string-only validation is an explicit profile limit.

TDLib rejects empty rows and null button objects, but its [button conversion](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/WebPageBlock.cpp#L2498)
recursively accepts labels through ordinary RichText conversion, validating actions with a
placeholder label. That path does not establish the documented maximum count, nonempty labels,
label entity restrictions or callback-only link style. Missing/null text and empty concatenations
normalize to empty plain text. Compare the [row conversion](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/WebPageBlock.cpp#L5772)
and [pinned schema](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/generate/scheme/td_api.tl#L4023).

URL/email/phone text wrappers undergo [string cleaning](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/misc.cpp#L76),
not button URL validation; empty targets survive the inspected [wrapper conversion](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/WebPageBlock.cpp#L276).
Cleaning includes control normalization, removal of selected Unicode controls and truncation.
Button URLs instead use [action validation](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/InlineKeyboardButton.cpp#L227)
and [link normalization](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/LinkManager.cpp#L1950).
Login/Web App targets require HTTPS outside the test-DC path. The parser also knows tg/ton/tonsite
schemes; that vocabulary does not grant GramLab runtime networking or define its supported profile.

## Original native seam

| JSON concept | Pinned native type or flags |
| --- | --- |
| URL/email/phone text | `TL_iv.textUrl`, `textEmail`, `textPhone`; URL webpage ID zero |
| Button row | `TL_iv.pageBlockButtonRow`; alignment bits 0/1/2, absent means fill |
| Row button | `TL_keyboard.PageButton`; optional style bit 0 |
| Inline text button | `TL_iv.textButton`; optional style bit 0 |
| Style | `RichButtonStyle` primary/danger/success/link bits 0/1/2/3 |
| Callback/URL/copy/disabled | Corresponding `TL_inlineButtonType` constructors |

Default canonical style maps to null. Callback data retains UTF-8 bytes with
`requires_password=false`. See the [text/row schema](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/tl/TL_iv.java#L423)
and [action/style schema](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/tl/TL_keyboard.java#L441).

Original [text formatting](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/RichMessageLayout.java#L2053)
creates URL spans, adds mailto for email, and strips phone formatting before adding tel.
[Chat navigation](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/ChatActivity.java#L36529)
may leave the chat or initiate network operations. Rich buttons use the [existing action dispatcher](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/Components/ChatActivityEnterView.java#L11439):
callback dispatches a callback, copy writes the guest clipboard, URL navigates, disabled ignores
touch. An offline navigation contract is required before enabling navigation actions.

The original [rich row implementation](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/RichMessageLayout.java#L4836)
implements touch handling but does not override the [base accessibility element count](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/RichMessageLayout.java#L9363)
of zero. Per-button accessibility targeting therefore remains unproven. Observe native geometry
and input before choosing a targeting seam; consult before changing the renderer or fidelity target.

The next split can separate independent core normalization, GPL native projection/codec,
scenario targeting, and coordinator-owned navigation/visual acceptance. Commit the exact supported
profile first. This research does not authorize network access or establish implemented support.
