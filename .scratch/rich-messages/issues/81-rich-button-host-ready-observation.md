# Prepare from the current validated native observation

Type: task
Status: ready-for-agent
Work state: claimed
Blocked by: native acceptance

Coordinator owns this ticket, `src/gramlab/_android_rich_buttons.py` and focused additions to
`tests/test_android_rich_button_host.py`. Other workers must not edit these files.

Native public acceptance finds a transient unfocused initial draw before a later focused draw.
Preparation currently validates a newer observation but freezes geometry from the preceding
read. Demonstrate this race with independent external guest observations and a real World,
then freeze the exact validated sample. Preserve strict checks after capture and immediately
before input: later geometry, revision or lifetime changes must still reject without a touch.

Investigate bounded initial focus readiness separately from post-input confirmation. Do not
relax foreground clipboard or lifetime requirements to make retained effects pass. Preserve
the original native failure, and obtain new native evidence after any correction. Focused
host tests substitute the guest boundary and cannot establish original Android acceptance.
