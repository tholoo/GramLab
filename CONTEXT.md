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


**Media asset**: Immutable validated media belonging to one simulated world. Different messages
can refer to the same asset without changing its bytes.

**Bot file identity**: A reusable file reference belonging to one bot in one simulated world.
It is distinct from a content identity or a custom-emoji identity.

**Media grant**: A recipient's access to media published in their conversation, retained until
the owning world is deleted even if that message is later edited.

**Custom-emoji identity**: A logical identifier for a registered emoji in one simulated world.
It does not grant access to the emoji's files.

**Client instance**: One virtual or rendered client participating in a simulated world, with its
own local state such as its clipboard and cache.

**Rich-button target**: One observed occurrence of a button in a particular message revision and
client lifetime. Its label need not distinguish it from other buttons.

**Message publication**: The atomic appearance of a final message revision in a simulated world,
including its event, recipient access and pending bot delivery where applicable.

**Media group**: An ordered set of two to ten homogeneous photo or document messages published by
one bot as a single atomic action.

**Client bridge schema**: A versioned semantic contract through which a client instance observes
and changes one simulated world. It does not include client-specific rendering translation.
