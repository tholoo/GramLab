# Share simulated worlds across three execution modes

Use one world model for simulation-only, headless Android and interactive Android execution.
This separates scalable semantic testing from resource-intensive rendering without creating a
second UI-only truth; only Android modes establish client rendering evidence, and no mode may
fall back to real Telegram connectivity.
