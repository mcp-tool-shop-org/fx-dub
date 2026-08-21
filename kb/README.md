# kb/ — the fx-dub project knowledge base

**`fxdub.db`** is a committed SQLite database holding everything this project has verified: node availability on Comfy Cloud, model licenses, measured runs (job UUIDs, gpu-sec, credits, decoded output formats), graph registry + statuses, dialog-thread state, the trap ledger, the architecture decisions, and the open action list.

- **Source of truth is [`build_db.py`](build_db.py)** — edit its seed data, rerun (`python kb/build_db.py`), commit script + db together. Never hand-edit the .db.
- Every row carries `class` **A** (measured on-account) or **B** (agent-reported/advisory). Verification dates age per the studio's 30-day freshness rule.
- Entry point for new agents: [`../AGENTS.md`](../AGENTS.md). Query cookbook lives there too.
- Scope discipline: this db holds **fx-dub-specific** truth only. Studio-wide model/license/platform knowledge lives in the readouts monorepo (`E:/AI/readouts/model-knowledge/models.db`, 119 models, adversarially verified) — reference it, don't fork it.

Quick probes:

```bash
python -c "import sqlite3;c=sqlite3.connect('kb/fxdub.db');[print(*r) for r in c.execute('SELECT * FROM v_open_actions')]"
python -c "import sqlite3;c=sqlite3.connect('kb/fxdub.db');[print(r[0]) for r in c.execute(\"SELECT trap FROM traps WHERE severity='high'\")]"
```
