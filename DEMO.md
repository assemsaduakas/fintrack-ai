# FinTrack AI — Demo Guide (2–5 minutes)

This file describes a short demo to record the FinTrack AI system: live operation, tests, and commentary.

Structure (suggested timing):
- 0:00–0:30 — Quick project overview and architecture (agents: Bookkeeper, Market Analyst, Financial Advisor).
- 0:30–1:30 — Live demo: run `main.py`, show an example conversation (log an expense, summarize, ask for budget advice).
- 1:30–2:30 — Run automated tests: show `pytest` passing (LLM behavior, user-flow, and edge/adversarial tests).
- 2:30–3:30 — Self-review: open key files (`main.py`, `database.py`, `tests/`) and briefly explain important parts (delegation logic, sanitization, rate limiting).

Recording tips:
- Use a terminal recorder (QuickTime on macOS or any screen recorder).
- Ensure `venv312` is activated and `OPENAI_API_KEY` is set (tests use a dummy key).
- Mute or blur any sensitive environment values when recording.

Commands to run during demo (copy into terminal):

```bash
# activate venv
source venv312/bin/activate

# run the app (example inputs will be provided interactively)
python main.py

# in a separate terminal, run tests
python -m pytest -q

# tail logs (optional)
tail -n +1 -f fintrack_ai.log
```

Recommended sample user interactions to demonstrate:
- "Log an expense of $25 for groceries."
- "Summarize my expenses for this month."
- "Suggest a budget plan based on my expenses."

Notes:
- Tests included: `tests/test_llm_behavior.py`, `tests/test_user_flow.py`, `tests/test_edge_adversarial.py`.
- The demo highlights core capabilities: expense logging, RAG queries, market lookup fallback, delegation, sanitization, and rate-limiting.
