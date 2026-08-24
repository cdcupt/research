# research

Research reports produced with Claude Code — one folder per topic. Each folder holds the
finished report (`report.html`, self-contained, opens offline), the raw material it was built
from (`src/`: agent outputs, source lists, link audit), the generator that turns that material
into the report, and the multi-agent workflow script that gathered it.

| Topic | Date | Report | Summary |
|---|---|---|---|
| [llm-context-management](llm-context-management/) | 2026-08-20 | [report.html](llm-context-management/report.html) | How engineers manage an LLM's context window: 8 ranked techniques + 2 addenda from 164 papers, blogs, docs, talks and threads, each with an implementation recipe, code and sources; plus the open-source landscape (30 repos). |
| [llm-context-management](llm-context-management/) | 2026-08-21 | [market-report.html](llm-context-management/market-report.html) | Context Market Map: the problems worth solving, the startup and incumbent landscape with funding, a go-to-market playbook — plus the Chinese context/memory market. |
| [llm-context-management](llm-context-management/) | 2026-08-24 | [investment-report.html](llm-context-management/investment-report.html) | AI Investment Outlook: the stock situation, private funding trends and named investor expectations, and the US-vs-China capital picture — 80 sources, every figure dated. |

## Conventions

- `topic-slug/report.html` — the deliverable. Light theme, inline SVG figures, no external assets except Google Fonts (falls back to system fonts offline).
- `topic-slug/preview/` — PNG renders of the key figures, for READMEs and quick looks.
- `topic-slug/src/` — everything needed to rebuild: generator (`build.py`, `style.css`), agent outputs (`result.json`, `taxonomy.json`, `sections/*.html`, `sweep/*.json`), and audits (`links.tsv`).
- `topic-slug/workflow.js` — the Claude Code `Workflow` script that ran the research (bounded multi-agent sweep → taxonomy → deep-read → critic).
