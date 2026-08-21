export const meta = {
  name: 'ctx-mgmt-research',
  description: 'Multi-source research on LLM context-management techniques: sweep → taxonomy → per-technique deep sections → gap check',
  phases: [
    { title: 'Sweep', detail: '6 source modalities in parallel (papers, blogs, videos, community, frameworks, model/infra)' },
    { title: 'Taxonomy', detail: 'dedupe + cluster techniques into categories with popularity scores' },
    { title: 'Deep-read', detail: 'one agent per category: fetch sources, write HTML section + JSON summary' },
    { title: 'Gap check', detail: 'completeness critic + one bounded gap-fill round' },
  ],
}

const DIR = '/private/tmp/claude-501/-Users-daichenchai/b250f2e9-8308-4b77-ab17-c1b1f27581d5/scratchpad/ctx-report'
const TODAY = '2026-08-20'

const COMMON_RULES = `
GROUND RULES (read carefully):
- Today is ${TODAY}. Cover 2024–2026 material AND the foundational classics. Prefer primary sources.
- FIRST call ToolSearch with query "select:WebSearch,WebFetch" to load the web tools. WebSearch is US-only.
- NEVER invent a URL. Every url you return must be one you saw in a WebSearch result or fetched with WebFetch. If you cannot confirm a URL, omit the source.
- Bounded effort: stop when you hit the caps below and return what you have — partial results are fine, grinding is not.
- Your final output is machine-read. Return ONLY the structured object. No prose preamble.`

const SOURCE_SCHEMA = {
  type: 'object', required: ['sources', 'notes'],
  properties: {
    sources: { type: 'array', items: { type: 'object', required: ['title', 'url', 'type', 'year', 'venue_or_author', 'techniques', 'summary', 'popularity_signal'],
      properties: {
        title: { type: 'string' }, url: { type: 'string' },
        type: { type: 'string', enum: ['paper', 'blog', 'video', 'thread', 'docs', 'repo', 'talk', 'other'] },
        year: { type: 'integer' }, venue_or_author: { type: 'string' },
        techniques: { type: 'array', items: { type: 'string' }, description: 'short technique tags, e.g. "compaction/summarization", "RAG", "KV-cache compression", "sub-agent isolation", "memory files", "prompt caching"' },
        summary: { type: 'string', description: '1-2 sentences: the key claim or contribution' },
        popularity_signal: { type: 'string', description: 'citations / GitHub stars / views / upvotes / HN points / "widely referenced by X" — or "unknown"' },
      } } },
    notes: { type: 'string', description: 'what you searched, what you could not find, caps hit?' },
  },
}

const SWEEPS = [
  { key: 'papers', label: 'academic papers', caps: '≤14 WebSearch, ≤8 WebFetch, 15 min', guidance: `Academic papers (arXiv, ACL, NeurIPS, ICLR, ICML) on managing LLM context. Cover: context-engineering surveys ("A Survey of Context Engineering for Large Language Models", Mei et al. 2025 and any 2026 successors); memory-augmented agents (MemGPT, Generative Agents, A-Mem, Mem0 paper, MemoryBank, RecurrentGPT, "memory in LLM agents" surveys); prompt/context compression (LLMLingua 1/2, LongLLMLingua, gist tokens, AutoCompressors, ICAE, "Selective Context", RECOMP); summarization-based conversation memory; retrieval-augmented generation & agentic RAG; long-context vs RAG comparisons; "Lost in the Middle" (Liu et al.), context rot, NIAH/RULER/LongBench benchmarks; KV-cache eviction/compression (StreamingLLM/attention sinks, H2O, SnapKV, PyramidKV, KIVI), context-window extension (RoPE scaling, YaRN, Infini-attention, Ring Attention). Search arxiv.org, aclanthology.org, openreview.net, semanticscholar.org, paperswithcode. Capture citation counts where visible. Target 20–30 sources.` },
  { key: 'blogs', label: 'industry engineering blogs', caps: '≤14 WebSearch, ≤8 WebFetch, 15 min', guidance: `Engineering blogs and official guides from AI labs and agent builders. Must-find: Anthropic "Effective context engineering for AI agents" (2025) and "Building effective agents", Anthropic context-editing / memory tool / prompt-caching docs, Claude Code auto-compact and CLAUDE.md docs; LangChain/LangGraph "Context Engineering for Agents" (Lance Martin; write/select/compress/isolate); Manus "Context Engineering for AI Agents: Lessons from Building Manus" (KV-cache hit rate, mask don't remove, file system as context, recitation); Cognition "Don't Build Multi-Agents"; Chroma "Context Rot" research; OpenAI Agents SDK sessions / prompt caching / Responses API state; Google Gemini context caching & ADK memory; Letta/MemGPT blog posts; mem0, Zep/Graphiti blogs; Cursor, Factory, Devin, Cline, Windsurf posts on context management; Dex Horthy "12-Factor Agents" (own your context window); Martin Fowler / Simon Willison / Eugene Yan / Hamel Husain / Philipp Schmid / Drew Breunig ("How Long Contexts Fail", "How to Fix Your Context"). Also any 2026 posts. Target 20–30 sources.` },
  { key: 'videos', label: 'videos & conference talks', caps: '≤12 WebSearch, ≤6 WebFetch, 15 min', guidance: `Videos and talks: YouTube, conference recordings (AI Engineer World's Fair / Summit, LangChain Interrupt, Anthropic "Code with Claude", OpenAI DevDay, NeurIPS/ICLR talks), podcasts (Latent Space, Lex, etc.), and popular explainers on LLM context management / context engineering / agent memory / RAG vs long context / KV cache. Include Andrej Karpathy material (Software 3.0 talk; "context engineering" remarks), Lance Martin's context engineering videos, Anthropic and Manus talks, Harrison Chase, Dex Horthy's 12-factor agents talk, Jason Liu, Hamel Husain, Simon Willison talks, LlamaIndex/LangChain webinars. Capture view counts where visible (from search snippets or fetched pages). Use youtube.com search result pages and conference sites. Target 12–20 sources.` },
  { key: 'community', label: 'social & community threads', caps: '≤14 WebSearch, ≤6 WebFetch, 15 min', guidance: `Community discussion: Hacker News threads (news.ycombinator.com — capture points/comments), Reddit (r/LocalLLaMA, r/ClaudeAI, r/ChatGPTCoding, r/LangChain, r/MachineLearning, r/cursor — capture upvotes), X/Twitter posts (Karpathy, Tobi Lütke's "context engineering" post, Shopify, Dex Horthy, swyx, Harrison Chase, Anthropic devs), Lobsters, dev.to / Medium / Substack essays with traction, GitHub Discussions/issues in Claude Code, Cursor, Cline, Aider, OpenCode about compaction/context limits, and popular GitHub "awesome-context-engineering" / "awesome-llm-memory" lists (stars). Focus on what practitioners actually do: /compact strategies, CLAUDE.md/AGENTS.md memory files, handoff documents, scratchpads, sub-agents, "context rot" complaints, context-window budgeting, prompt caching tips. Target 15–25 sources.` },
  { key: 'frameworks', label: 'framework & tool documentation', caps: '≤14 WebSearch, ≤10 WebFetch, 15 min', guidance: `Official docs of frameworks/tools and how each implements context management: LangGraph (memory, checkpointers, state schema, summarization node, trim_messages), LangChain memory classes, LlamaIndex (memory blocks, chat stores, compression), Letta/MemGPT (core memory blocks, archival/recall, sleep-time compute), mem0, Zep + Graphiti (temporal knowledge graph), Cognee, OpenAI Agents SDK (Sessions, handoffs), Claude Agent SDK / Claude Code (auto-compact, /compact, /clear, CLAUDE.md, sub-agents, context editing API, memory tool, 1M context), Google ADK (sessions, memory bank, context caching), Microsoft Semantic Kernel / AutoGen (chat history reducers, summarization), CrewAI memory, Pydantic AI (history processors), Vercel AI SDK, Model Context Protocol resources, Cline/Cursor/Aider repo-map & context features, DSPy. Capture GitHub stars for each project. Target 18–28 sources (doc pages + repos).` },
  { key: 'infra', label: 'model & inference-level techniques', caps: '≤12 WebSearch, ≤8 WebFetch, 15 min', guidance: `Model/serving-level ways to handle context: long-context models and their real limits (Claude 1M, Gemini 1M/2M, GPT-4.1 1M, Llama 4 10M claims; effective vs nominal context; NIAH, RULER, LongBench, Fiction.LiveBench, "context rot"); prompt caching across providers (Anthropic cache_control, OpenAI automatic prompt caching, Gemini context caching — pricing/TTL and how to structure prompts for cache hits); KV-cache management in vLLM/SGLang (PagedAttention, prefix caching/RadixAttention, KV offloading, LMCache); KV compression/eviction (StreamingLLM, H2O, SnapKV, quantized KV); sliding-window / hybrid attention architectures (Mistral SWA, Gemma, Mamba/hybrid SSMs, Jamba); tokenizer-level compression; speculative/structured decoding relevance; cost/latency math of big contexts. Use vendor docs, vLLM/SGLang docs & blogs, arXiv, and benchmark pages. Target 15–25 sources.` },
]

function normUrl(u) {
  try {
    let s = String(u).trim()
    s = s.replace(/^http:\/\//i, 'https://').replace(/^https:\/\/www\./i, 'https://')
    s = s.split('#')[0]
    s = s.replace(/[?&](utm_[^&]*|ref|source|si|feature)=[^&]*/gi, '')
    s = s.replace(/\?$/, '').replace(/\/$/, '')
    return s.toLowerCase()
  } catch (e) { return String(u) }
}

// ---------------- Phase 1: Sweep (barrier is correct: taxonomy needs ALL sources) ----------------
phase('Sweep')
log(`Sweeping ${SWEEPS.length} source modalities in parallel (caps per agent: ~14 searches / ~8 fetches / 15 min)`)
const sweepResults = await parallel(SWEEPS.map(s => () => agent(`
You are researching "how people manage an LLM's context window" — the techniques for managing, compressing, summarizing, retrieving, isolating and offloading context for LLM apps and agents.
YOUR MODALITY: ${s.label}.
${s.guidance}

CAPS: ${s.caps}. When you hit a cap, stop and return what you have.
${COMMON_RULES}
- Tag each source with short technique tags (techniques[]). Reuse tags across sources where they mean the same thing.
- Before returning, ALSO write the full list as JSON to ${DIR}/sweep/${s.key}.json (use the Write tool). Then return the same data as your structured output.
`, { label: `sweep:${s.key}`, phase: 'Sweep', schema: SOURCE_SCHEMA })))

const allSources = []
const seen = new Set()
const sweepStats = {}
sweepResults.forEach((r, i) => {
  const key = SWEEPS[i].key
  if (!r) { sweepStats[key] = { returned: 0, note: 'agent failed/skipped' }; return }
  let kept = 0
  for (const src of (r.sources || [])) {
    const k = normUrl(src.url)
    if (!k || seen.has(k)) continue
    seen.add(k); kept++
    allSources.push({ ...src, modality: key })
  }
  sweepStats[key] = { returned: (r.sources || []).length, unique_kept: kept, note: r.notes }
})
const tagCounts = {}
for (const s of allSources) for (const t of (s.techniques || [])) { const k = t.toLowerCase().trim(); tagCounts[k] = (tagCounts[k] || 0) + 1 }
const topTags = Object.entries(tagCounts).sort((a, b) => b[1] - a[1]).slice(0, 60)
log(`Sweep done: ${allSources.length} unique sources across ${Object.keys(sweepStats).length} modalities; ${Object.keys(tagCounts).length} distinct technique tags`)

// ---------------- Phase 2: Taxonomy ----------------
phase('Taxonomy')
const TAXONOMY_SCHEMA = {
  type: 'object', required: ['framings', 'categories', 'notes'],
  properties: {
    framings: { type: 'array', description: 'the popular umbrella framings/taxonomies found in the literature (e.g. write/select/compress/isolate; Anthropic compaction+notes+sub-agents+JIT retrieval; Manus lessons; 12-factor agents)', items: { type: 'object', required: ['name', 'source_url', 'description'], properties: { name: { type: 'string' }, source_url: { type: 'string' }, description: { type: 'string' } } } },
    categories: { type: 'array', minItems: 6, maxItems: 8, items: { type: 'object', required: ['slug', 'name', 'stage', 'description', 'sub_techniques', 'source_count', 'popularity_rank', 'signals', 'source_urls'],
      properties: {
        slug: { type: 'string', description: 'kebab-case, e.g. compaction-summarization' },
        name: { type: 'string' }, stage: { type: 'string', description: 'one of: write | select | compress | isolate | foundations (model/infra)' },
        description: { type: 'string' }, sub_techniques: { type: 'array', items: { type: 'string' } },
        source_count: { type: 'integer', description: 'number of distinct sources in the list that substantively cover this category' },
        popularity_rank: { type: 'integer', description: '1 = most popular' },
        signals: { type: 'array', items: { type: 'string' }, description: 'concrete popularity evidence (stars, citations, views, how many frameworks ship it, etc.)' },
        source_urls: { type: 'array', items: { type: 'string' }, description: '8-15 best source URLs for this category, drawn ONLY from the provided list' },
      } } },
    notes: { type: 'string' },
  },
}
const compact = allSources.map(s => ({ url: s.url, title: s.title, type: s.type, year: s.year, by: s.venue_or_author, tags: s.techniques, pop: s.popularity_signal, sum: String(s.summary || '').slice(0, 220), via: s.modality }))
const taxonomy = await agent(`
You are the taxonomist for a research report titled "How to manage an LLM's context: the popular ways and how to achieve them".
Below is the deduplicated list of ${compact.length} sources gathered by six parallel sweeps (papers, blogs, videos, community, frameworks, infra), plus technique-tag frequencies.

TASK: cluster the techniques into 6–8 clear CATEGORIES a practitioner would recognize, rank them by popularity, and assign sources to each.
- Suggested starting point (adjust to the evidence): (1) compaction & summarization of history, (2) retrieval / just-in-time context loading (RAG, agentic search, file-system-as-context), (3) long-term memory systems (MemGPT/Letta, mem0, Zep, memory files like CLAUDE.md, episodic/semantic/procedural memory), (4) pruning/trimming/context editing (sliding windows, clearing tool results, observation masking), (5) prompt/context compression (LLMLingua, gist tokens), (6) isolation via sub-agents / multi-agent / state schemas / sandboxes, (7) structured context engineering & cache-friendly prompt design (system-prompt altitude, tool curation, progressive disclosure, append-only prefixes for prompt caching, recitation/todo), (8) model & infra foundations (long-context windows, prompt caching, KV-cache compression, attention variants, benchmarks & context rot).
- Popularity = how many distinct sources substantively cover it (count them) PLUS concrete external signals (GitHub stars, citations, views, upvotes, number of frameworks shipping it). Rank 1 = most popular. Be honest; do not flatten differences.
- Every category MUST get a stage: write | select | compress | isolate | foundations.
- source_urls must be copied verbatim from the list below — never invent.
- Write the final taxonomy JSON to ${DIR}/taxonomy.json with the Write tool, then return it as structured output. No web access needed; no prose.

TECHNIQUE TAG FREQUENCIES (top 60): ${JSON.stringify(topTags)}

SOURCES: ${JSON.stringify(compact)}
`, { label: 'taxonomy', phase: 'Taxonomy', schema: TAXONOMY_SCHEMA })

if (!taxonomy) throw new Error('taxonomy agent failed')
const cats = (taxonomy.categories || []).slice().sort((a, b) => a.popularity_rank - b.popularity_rank).slice(0, 8)
log(`Taxonomy: ${cats.length} categories → ${cats.map(c => `#${c.popularity_rank} ${c.name} (${c.source_count})`).join('; ')}`)

// ---------------- Phase 3: Deep-read (pipeline: each category independent) ----------------
phase('Deep-read')
const SUMMARY_SCHEMA = {
  type: 'object', required: ['slug', 'name', 'stage', 'one_line', 'steps', 'tools', 'sources', 'popularity', 'pitfalls', 'fragment_path', 'fetched_count', 'notes'],
  properties: {
    slug: { type: 'string' }, name: { type: 'string' }, stage: { type: 'string' },
    one_line: { type: 'string', description: '≤ 18 words: what it does' },
    steps: { type: 'array', minItems: 3, maxItems: 6, items: { type: 'string' }, description: 'implementation steps, ≤ 8 words each (used in a diagram)' },
    tools: { type: 'array', items: { type: 'string' }, description: 'names of libraries/products that implement it' },
    sources: { type: 'array', items: { type: 'object', required: ['title', 'url', 'type'], properties: { title: { type: 'string' }, url: { type: 'string' }, type: { type: 'string' }, year: { type: 'integer' } } } },
    popularity: { type: 'object', required: ['source_count', 'signals'], properties: { source_count: { type: 'integer' }, signals: { type: 'array', items: { type: 'string' } } } },
    pitfalls: { type: 'array', items: { type: 'string' } },
    fragment_path: { type: 'string' }, fetched_count: { type: 'integer' }, notes: { type: 'string' },
  },
}
const byUrl = new Map(allSources.map(s => [normUrl(s.url), s]))
const FRAGMENT_CONTRACT = `
HTML FRAGMENT CONTRACT (write EXACTLY this structure; no <html>/<head>/<body>/<h1>, no <style>, no <script>, no inline style attributes, no images, no external assets; HTML-escape < > & inside <code>):
<section class="technique" id="{slug}">
  <h2><span class="num">{rank}</span> {Name}</h2>
  <p class="lede">{≤ 60 words: what it is and why people use it}</p>
  <div class="kv">
    <div><b>Problem it solves</b><span>{1 sentence}</span></div>
    <div><b>Lifecycle stage</b><span>{write | select | compress | isolate | foundations} — {3-6 words why}</span></div>
    <div><b>Popularity signals</b><span>{concrete: N sources in this survey; stars; citations; views; which products ship it}</span></div>
  </div>
  <h3>How it works</h3>
  <p>{80-140 words}</p>
  <h3>How to achieve it</h3>
  <ol class="steps">{4-6 <li> items, each 1-2 sentences, concrete and actionable}</ol>
  <pre><code class="lang-{python|typescript|bash|text}">{minimal, realistic snippet ≤ 28 lines using a real API from the sources — e.g. LangGraph, Letta, Anthropic SDK, OpenAI SDK, mem0, LlamaIndex, vLLM; escape &lt; &gt; &amp;}</code></pre>
  <h3>Variants &amp; tools</h3>
  <ul class="tools">{3-8 <li><a href="URL">Tool/Variant</a> — one line</li>}</ul>
  <h3>Trade-offs &amp; pitfalls</h3>
  <ul>{3-5 <li>}</ul>
  <h3>Sources</h3>
  <ol class="sources">{6-12 <li><a href="URL">Title</a> <span class="src-type {paper|blog|video|thread|docs|repo|talk}">{type}</span> — {author/venue}, {year}</li>, real URLs only}</ol>
</section>
Word budget: 450–800 words excluding code and sources. Plain, direct English; no marketing tone; no em-dash overuse.`

const summaries = await pipeline(cats, async (c, _item, idx) => {
  const srcs = (c.source_urls || []).map(u => byUrl.get(normUrl(u))).filter(Boolean).map(s => ({ title: s.title, url: s.url, type: s.type, year: s.year, by: s.venue_or_author, sum: String(s.summary || '').slice(0, 200) }))
  return agent(`
You are writing ONE section of a research report: "How to manage an LLM's context — the popular ways and how to achieve them".
YOUR CATEGORY (popularity rank #${c.popularity_rank} of ${cats.length}): ${c.name}
Stage: ${c.stage}
Description: ${c.description}
Sub-techniques to cover: ${JSON.stringify(c.sub_techniques)}
Known popularity signals: ${JSON.stringify(c.signals)}; source_count from taxonomy: ${c.source_count}

ASSIGNED SOURCES (fetch the most important ones; prefer primary sources; you may add up to 4 more via WebSearch if something essential is missing):
${JSON.stringify(srcs)}

CAPS: ≤ 10 WebFetch, ≤ 6 WebSearch, 20 minutes. When a cap hits, stop and write with what you have.
${COMMON_RULES}

DELIVERABLES:
1) Write the HTML fragment to ${DIR}/sections/${c.slug}.html with the Write tool, following the contract below. Use rank number ${c.popularity_rank} in <span class="num">.
2) Return the structured summary (schema enforced). steps[] = the same implementation steps, compressed to ≤ 8 words each (they feed a diagram). sources[] = the same sources as in the fragment. fragment_path = the path you wrote. fetched_count = number of successful WebFetch calls.
${FRAGMENT_CONTRACT}
`, { label: `deep:${c.slug}`, phase: 'Deep-read', schema: SUMMARY_SCHEMA })
})
const okSummaries = summaries.filter(Boolean)
log(`Deep-read done: ${okSummaries.length}/${cats.length} sections written`)

// ---------------- Phase 4: Gap check (barrier justified: critic needs everything) ----------------
phase('Gap check')
const GAP_SCHEMA = {
  type: 'object', required: ['verdict', 'gaps', 'notes'],
  properties: {
    verdict: { type: 'string', enum: ['complete', 'minor-gaps', 'major-gaps'] },
    gaps: { type: 'array', maxItems: 2, items: { type: 'object', required: ['slug', 'title', 'why', 'queries'], properties: { slug: { type: 'string' }, title: { type: 'string' }, why: { type: 'string' }, queries: { type: 'array', items: { type: 'string' } } } } },
    notes: { type: 'string' },
  },
}
const critic = await agent(`
You are the completeness critic for a research report: "How to manage an LLM's context — the popular ways and how to achieve them".
The report's audience: a senior engineer who builds LLM apps/agents and wants (a) a list of the popular ways to manage context and (b) how to achieve each.

TAXONOMY (categories, ranks, signals): ${JSON.stringify(cats.map(c => ({ rank: c.popularity_rank, name: c.name, stage: c.stage, subs: c.sub_techniques, source_count: c.source_count })))}
FRAMINGS FOUND: ${JSON.stringify(taxonomy.framings)}
SECTION SUMMARIES: ${JSON.stringify(okSummaries.map(s => ({ slug: s.slug, name: s.name, one_line: s.one_line, steps: s.steps, tools: s.tools, n_sources: (s.sources || []).length, pitfalls: s.pitfalls, notes: s.notes })))}
SWEEP STATS: ${JSON.stringify(sweepStats)}
Section files are in ${DIR}/sections/ — read any you need to judge quality (Read tool).

QUESTION: what is MISSING or WRONG? Consider: a major technique absent (e.g. handoff/checkpoint documents between sessions, context budgeting & token accounting, evaluation of context strategies, multimodal context, tool-result offloading, prompt caching economics, security of memory/context poisoning), a modality under-covered (videos? community?), a category with thin or weak sources, contradictory popularity claims, stale (pre-2024) framing presented as current, or obviously fabricated-looking URLs.
Return verdict + at most 2 gaps worth one bounded research round each (each with 2-3 concrete search queries). If the report is complete enough, return zero gaps. No web access needed. No prose outside the schema.
`, { label: 'critic', phase: 'Gap check', schema: GAP_SCHEMA })

let gapSummaries = []
const gaps = (critic && critic.gaps) ? critic.gaps.slice(0, 2) : []
if (gaps.length) {
  log(`Critic verdict: ${critic.verdict}; running ${gaps.length} bounded gap-fill agent(s) (single round)`)
  gapSummaries = (await parallel(gaps.map((g, i) => () => agent(`
You are filling ONE gap in a research report: "How to manage an LLM's context — the popular ways and how to achieve them".
GAP: ${g.title}
WHY IT MATTERS: ${g.why}
SUGGESTED QUERIES: ${JSON.stringify(g.queries)}
Existing categories (do not duplicate them; position your topic relative to them): ${JSON.stringify(cats.map(c => c.name))}

CAPS: ≤ 8 WebSearch, ≤ 8 WebFetch, 15 minutes. Stop at the cap and write with what you have.
${COMMON_RULES}

DELIVERABLES:
1) Write the HTML fragment to ${DIR}/sections/addendum-${g.slug}.html with the Write tool, following the contract below; use rank number ${cats.length + i + 1} in <span class="num"> and id "addendum-${g.slug}".
2) Return the structured summary (schema enforced) with slug "addendum-${g.slug}", fragment_path = the path written, fetched_count = successful fetches.
${FRAGMENT_CONTRACT}
`, { label: `gapfill:${g.slug}`, phase: 'Gap check', schema: SUMMARY_SCHEMA })))).filter(Boolean)
} else {
  log(`Critic verdict: ${critic ? critic.verdict : 'critic failed'} — no gap-fill round needed`)
}

return {
  sweepStats,
  totalUniqueSources: allSources.length,
  topTags: topTags.slice(0, 30),
  framings: taxonomy.framings,
  categories: cats.map(c => ({ slug: c.slug, name: c.name, stage: c.stage, rank: c.popularity_rank, source_count: c.source_count, signals: c.signals, sub_techniques: c.sub_techniques })),
  summaries: okSummaries,
  critic,
  gapSummaries,
  files: { taxonomy: `${DIR}/taxonomy.json`, sweeps: `${DIR}/sweep/`, sections: `${DIR}/sections/` },
}
