"""A causal rich group journey using a distinct creator and acting member."""

import time

from gramlab import Scenario


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


lab = Scenario.from_environment()
owner = lab.user("Mina")
member = lab.user("Arman")
group = lab.group("Study group", creator=owner, user=member, bot="helper")
expect(group.raw["type"] == "supergroup" and group.id < 0, "Wrong group identity")
expect(
    lab.get_chat_member(chat_id=group.id, user_id=owner.id)["status"] == "creator",
    "Wrong creator membership",
)

group.send("/game")
reply = group.wait_for_messages(2, timeout=10)[1]
expect(reply.text == "" and "rich_message" in reply.raw, "Unexpected rich group reply")
group.capture("group-before", contains=["/game", "Ready for the group"])
targets = lab.rich_buttons(chat_id=group.id, message_id=reply.id, user_id=member.id)["targets"]
expect([target["label"] for target in targets] == ["Continue"], "Wrong rich group target")
receipt = lab.tap_rich_button(target_id=targets[0]["target_id"])
callback = receipt["effect"]["callback"]
expect(callback["user_id"] == member.id and callback["data"] == "continue", "Wrong group actor")
deadline = time.monotonic() + 10
while lab.get_callback(user_id=member.id, callback_id=callback["id"])["answer"] is None:
    expect(time.monotonic() < deadline, "Group callback answer missing")
    time.sleep(0.02)
expect(group.history()[1].text == "Continued for the group", "Group edit was not retained")
group.capture("group-after", contains=["/game", "Continued for the group"])

initial = lab.bot("helper").status()
stopped = lab.stop_bot("helper", generation=initial.generation)
started = lab.start_bot("helper", generation=stopped["generation"])
expect(started["generation"] == initial.generation + 1, "Wrong replacement generation")
group.type("after restart")
restarted_reply = group.wait_for_messages(4, timeout=10)[-1]
expect(
    restarted_reply.text == "" and "rich_message" in restarted_reply.raw,
    "Rich group delivery failed after bot restart",
)
group.capture("group-restarted", contains=["after restart", "Ready for the group"])
