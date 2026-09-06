# Implement versioned update selection and recovery offsets

Type: task
Status: ready-for-agent
Work state: claimed
Blocked by: 01 (contract confirmation)

The coordinator owns world/Bot API implementation, dedicated tests and shared documentation.
Inspect migration and polling behavior while the reference ticket resolves the exact contract.
Implement persistent update selection and negative offsets only after source confirmation;
verify behavior at the HTTP/world boundary, including malformed requests before side effects.
Keep the full product goal and consumer workflow open; this ticket covers update delivery only.
