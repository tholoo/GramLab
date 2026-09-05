# Preserve Android rendering through a local adapter

Use a minimally patched Telegram Android client, with a local simulation boundary, instead of a
recreated renderer or Telegram Web/Desktop. The user prioritizes Android fidelity despite its
native build/runtime cost; a pinned profile and an early end-to-end feasibility gate bound the
claim, while isolated patches reduce upgrade drift. This is not a commitment to implement a
wire-compatible MTProto server.
