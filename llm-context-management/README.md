# Context Window Playbook — how people manage an LLM's context

**Report:** [`report.html`](report.html) (self-contained HTML, 293 KB) · **Date:** 2026-08-20

A sourced survey of the popular ways to manage an LLM's context window, ranked by how much the
literature and the community talk about them, each with a concrete implementation recipe, a code
snippet against a real API, tools, pitfalls and 12 sources.

## Findings at a glance

| # | Technique | Stage | Sources |
|---|---|---|---|
| 1 | Long-term memory systems (MemGPT/Letta tiers, mem0, Zep/Graphiti, memory files) | write | 47 |
| 2 | Compaction & summarization (auto-compact, running summaries, handoffs) | compress | 42 |
| 3 | Model & infra foundations (effective context, prompt caching, KV cache, benchmarks) | foundations | 43 |
| 4 | Retrieval & just-in-time loading (RAG, repo maps, MCP resources, tool loadout) | select | 26 |
| 5 | Offloading & cache-friendly prompts (file system as context, stable prefix) | write | 28 |
| 6 | Sub-agent isolation (orchestrator/workers, state schemas) | isolate | 27 |
| 7 | Pruning & context editing (sliding windows, tool-result clearing) | compress | 19 |
| 8 | Prompt compression (LLMLingua family, gisting) | compress | 12 |
| † | Addenda: vendor server-side state (OpenAI Responses/compact); token accounting & observability | | |

Evidence base: 164 unique sources — 52 papers, 42 blog posts, 33 doc pages, 17 videos/talks,
9 community threads, 6 repos. Popularity = distinct sources that substantively cover a technique
(ranking also weighs stars, citations and how many frameworks ship it). Search was US-only and never
surfaced Reddit; community signal comes from Hacker News, X and GitHub.

## Figures

| Lifecycle map | Popularity |
|---|---|
| ![lifecycle](preview/fig1-lifecycle-map.png) | ![popularity](preview/fig2-popularity.png) |

| Recipe map (technique × implementation steps) | Decision flow |
|---|---|
| ![recipe](preview/fig3-recipe-map.png) | ![decision](preview/fig4-decision-flow.png) |

## How it was made

`workflow.js` is the Claude Code `Workflow` script: 6 parallel source sweeps (papers, engineering
blogs, videos/talks, community, framework docs, model/infra) with hard search/fetch/time caps →
taxonomist (dedupe, cluster, rank) → one deep-read agent per technique writing an HTML fragment under
a strict contract plus a structured summary → completeness critic → ≤ 2 bounded gap-fills.
18 agents, 34 minutes, 0 errors. Every URL was present in a search result or fetched page; all links
were then audited (`src/links.tsv`: 147 live, 16 bot-blocked but confirmed, 1 dead and dropped).

## Rebuild

```bash
cd src
python3 build.py            # reads result.json, taxonomy.json, sections/, sweep/, links.tsv, decision.json
cp llm-context-management.html ../report.html
# visual check (needs the Playwright workspace at ~/browser-automation):
NODE_PATH=~/browser-automation/node_modules node shoot.js llm-context-management.html ./shots
```

`build.py` generates every SVG figure programmatically (lifecycle map, popularity chart, recipe map,
per-section step rails, decision flow from `decision.json`). To re-run the research itself, edit the
`DIR` constant in `workflow.js` to a writable folder and run it through the Claude Code `Workflow` tool.
