# GramLab

GramLab is a laboratory for testing Telegram bots and previewing their conversations without
real Telegram accounts.

## Language

**Virtual user**: A synthetic participant in a simulated Telegram world, not an authenticated
Telegram account. _Avoid_: test account when referring to simulated participants.

**Simulated world**: The isolated users, chats, permissions, messages and pending events belonging
to one simulation run.

**Scenario**: A repeatable description of participant actions and expected observable outcomes.

**Simulation-only mode**: Scenario execution without an Android client or rendered UI.
_Avoid_: headless UI when there is no rendering.

**Headless Android mode**: Execution with the Android client rendering without a visible runtime
window. It can produce UI evidence.

**Interactive Android mode**: Execution with a visible Android client for exploration and review.

**Fidelity profile**: The specified client revision, platform, display, language, assets and
supported surfaces against which compatibility claims are evaluated.

**Compatibility evidence**: Reproducible observations establishing a particular modeled behavior
or rendering match for a fidelity profile.

**Conversation example**: A synthetic, labeled conversation used for previews, tutorials or help.
