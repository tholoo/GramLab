from gramlab import Scenario

lab = Scenario.from_environment()
chat = lab.conversation(user=lab.user("Alex", language_code="en"), bot="echo")
chat.send("Hello!")
history = chat.wait_for_messages(2, timeout=5)

if history[1].text != "Echo: Hello!":
    raise AssertionError("Unexpected bot reply")
chat.capture("hello", contains=["Echo: Hello!"])
