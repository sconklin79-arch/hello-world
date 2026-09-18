# hello-world

A GitHub Flow practice repo that also hosts an imported set of Obsidian Agent Skills.

## Layout
- `utils.py` — small standalone helper functions (`average`, `get_first`, `parse_int`, `divide`), each guarded against empty/invalid/zero-divisor input. No test suite yet.
- `scripts/review_and_fix.py` — example use of the Claude Agent SDK (`claude_agent_sdk`) to run an agentic review-and-fix loop against `utils.py`.
- `dashboard.canvas` — a JSON Canvas file (Obsidian format).
- `skills/` — Agent Skills (per the [Agent Skills spec](https://agentskills.io/specification)) for working with Obsidian: `obsidian-markdown`, `obsidian-bases`, `obsidian-cli`, `json-canvas`, `defuddle`, `knap`. See `README.md` for what each does.
- `.claude-plugin/` — marketplace/plugin manifests so this repo's skills can be installed as a plugin (`/plugin marketplace add kepano/obsidian-skills`).

## Conventions
- Development happens on `claude/*`-prefixed branches, merged into `main` via PR (see closed PRs #1, #3, #4 for style/scope).
- Keep changes minimal and scoped — this repo is intentionally small; don't add build tooling, CI, or abstractions unless a task specifically calls for them.
- `utils.py` functions raise clear `ValueError`/`ZeroDivisionError` on bad input rather than crashing with default exceptions — follow that pattern if adding more helpers here.
