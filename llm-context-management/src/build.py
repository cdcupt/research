#!/usr/bin/env python3
"""Assemble the LLM context-management report from workflow outputs.
Inputs (same dir): result.json (workflow return), taxonomy.json (fallback), sections/*.html, sweep/*.json
Outputs: llm-context-management.html (standalone) + llm-context-management.artifact.html (body-only for Artifact)
"""
import json, re, html, textwrap, glob, os, sys, datetime
from collections import Counter, OrderedDict

DIR = os.path.dirname(os.path.abspath(__file__))
OUT_FULL = os.path.join(DIR, 'llm-context-management.html')
OUT_ART = os.path.join(DIR, 'llm-context-management.artifact.html')
TODAY = '2026-08-20'

# ---- palette (validated with dataviz validator; see notes) ----
INK, INK2, MUTED, HAIR, SURFACE, BG, ACCENT = '#0e1116', '#3e4656', '#6b7385', '#dde2ea', '#ffffff', '#f6f7fa', '#1f5fe0'
STAGES = OrderedDict([
    ('write',       dict(name='Write',       color='#2a78d6', verb='write out',  blurb='Save context outside the window: notes, scratchpads, memory files, state.')),
    ('select',      dict(name='Select',      color='#1baf7a', verb='pull in',    blurb='Bring only the right context in: retrieval, memory recall, tool/skill selection.')),
    ('compress',    dict(name='Compress',    color='#eb6834', verb='shrink',     blurb='Keep the essentials: summarize, prune, trim, compress tokens.')),
    ('isolate',     dict(name='Isolate',     color='#4a3aa7', verb='split',      blurb='Give work its own window: sub-agents, state schemas, sandboxes.')),
    ('foundations', dict(name='Foundations', color='#5b6472', verb='beneath',    blurb='Model & serving layer: long context, caching, KV cache, benchmarks.')),
])
SHORT = {
    'long-term-memory-systems': 'Long-term memory systems',
    'compaction-summarization': 'Compaction & summarization',
    'model-infra-foundations': 'Model & infra foundations',
    'retrieval-jit-context-loading': 'Retrieval & just-in-time loading',
    'offloading-cache-friendly-prompt-design': 'Offloading & cache-friendly prompts',
    'sub-agent-isolation': 'Sub-agent isolation',
    'pruning-context-editing': 'Pruning & context editing',
    'prompt-compression': 'Prompt compression',
    'addendum-vendor-server-side-state-openai-gemini': 'Vendor-managed server-side state',
    'addendum-token-accounting-context-observability': 'Token accounting & observability',
}
SUBS = {
    'long-term-memory-systems': ['Memory tiers (MemGPT / Letta)', 'Self-editing memory blocks', 'Fact-extraction layers (mem0)', 'Temporal graphs (Zep Graphiti)', 'Memory files (CLAUDE.md)'],
    'compaction-summarization': ['Auto-compact at a threshold', 'Recursive / running summaries', 'Compaction at task boundaries', 'Survival: hooks, handoff notes', 'Sub-agents compress & report'],
    'model-infra-foundations': ['1M windows vs effective length', 'NIAH / RULER / context rot', 'Prompt-caching economics', 'Prefix reuse (vLLM, SGLang)', 'KV eviction & quantization'],
    'retrieval-jit-context-loading': ['Classic & agentic RAG', 'JIT refs: paths, grep, URIs', 'Code-aware repo maps (aider)', 'MCP resources', 'Tool selection / loadout'],
    'offloading-cache-friendly-prompt-design': ['File system as context', 'Scratchpads & todo recitation', 'Stable append-only prefix', "Mask tools, don't remove", 'Own your context window'],
    'sub-agent-isolation': ['Orchestrator + worker agents', 'Own prompt, tools, window each', 'Fresh window per iteration', 'State schemas & sandboxes', 'Single-writer principle'],
    'pruning-context-editing': ['Sliding window / last-N', 'Clear tool results & thinking', 'Observation masking', 'Message-pruning APIs', 'Flush history into memory'],
    'prompt-compression': ['Token pruning (LLMLingua)', 'LLMLingua-2 distilled pruning', 'Question-aware (LongLLMLingua)', 'Doc compression (RECOMP)', 'Gist tokens & ICAE'],
    'addendum-vendor-server-side-state-openai-gemini': ['OpenAI Responses API (store)', 'previous_response_id threads', 'Conversations API', '/responses/compact endpoint', 'Agents SDK sessions'],
    'addendum-token-accounting-context-observability': ['Anthropic count_tokens', 'Gemini countTokens + usage', 'tiktoken (OpenAI models)', 'Claude Code /context', 'OTel gen_ai.usage spans'],
}
def sname(c, dagger=False):
    n = SHORT.get(c.get('slug'), c.get('name', ''))
    return n + (' †' if dagger and c.get('addendum') else n and '')
def stage_key(s):
    s = (s or '').lower()
    for k in STAGES:
        if k in s: return k
    return 'foundations'

def esc(s): return html.escape(str(s if s is not None else ''), quote=True)
def wrap(s, width, max_lines=None):
    lines = textwrap.wrap(str(s or ''), width=width) or ['']
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]; lines[-1] = lines[-1][:max(0, width-1)].rstrip() + '…'
    return lines
def norm_url(u):
    s = str(u or '').strip()
    s = re.sub(r'^http://', 'https://', s, flags=re.I); s = re.sub(r'^https://www\.', 'https://', s, flags=re.I)
    s = s.split('#')[0]; s = re.sub(r'[?&](utm_[^&]*|ref|source|si|feature)=[^&]*', '', s, flags=re.I)
    return s.rstrip('?').rstrip('/').lower()

# ---- SVG helpers ----
FONT = 'font-family="inherit"'
def t(x, y, s, size=13, fill=INK, weight=400, anchor='start', extra=''):
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}" {FONT} {extra}>{esc(s)}</text>'
def tlines(x, y, lines, size=13, lh=None, fill=INK, weight=400, anchor='start'):
    lh = lh or round(size * 1.25, 1)
    spans = ''.join(f'<tspan x="{x:.1f}" dy="{0 if i == 0 else lh}">{esc(l)}</tspan>' for i, l in enumerate(lines))
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}" {FONT}>{spans}</text>'
def chevron(x, y, w, h, color, first=False, notch=14):
    pts = [(x, y), (x + w - notch, y), (x + w, y + h / 2), (x + w - notch, y + h), (x, y + h)]
    if not first: pts.append((x + notch, y + h / 2))
    pstr = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    fill = f'fill="{color}" fill-opacity="0.16"' if first else f'fill="{SURFACE}"'
    return f'<polygon points="{pstr}" {fill} stroke="{color}" stroke-width="1.2"/>'
def svg_open(w, h, title, minw=None):
    style = f' style="min-width:{minw}px"' if minw else ''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{esc(title)}"{style}>'
            f'<title>{esc(title)}</title>')
ARROW_DEFS = ('<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
              f'<path d="M0,0 L10,5 L0,10 z" fill="{MUTED}"/></marker></defs>')

# ---------------- Figure 1: lifecycle map ----------------
def svg_lifecycle(cats):
    W = 1140; left = 16; col_w = 212; gap = 12
    out = [svg_open(W, 10, 'Context lifecycle map', minw=960), ARROW_DEFS]
    # context window bar
    out.append(f'<rect x="{left}" y="18" width="{W-2*left}" height="74" rx="6" fill="{SURFACE}" stroke="{INK}" stroke-width="1.5"/>')
    out.append(t(left + 14, 40, 'THE CONTEXT WINDOW — everything the model sees on one call', 12, MUTED, 700, extra='letter-spacing=".08em"'))
    segs = ['System prompt', 'Tool definitions', 'Memory / notes', 'Conversation history', 'Retrieved docs', 'Tool results']
    sx = left + 14; sw = (W - 2 * left - 28 - 5 * 8) / len(segs)
    for i, s in enumerate(segs):
        x = sx + i * (sw + 8)
        out.append(f'<rect x="{x:.1f}" y="52" width="{sw:.1f}" height="28" rx="4" fill="{BG}" stroke="{HAIR}"/>')
        out.append(t(x + sw / 2, 70, s, 12.5, INK2, 600, 'middle'))
    # columns
    y0 = 118; maxh = 0; bodies = []
    for i, (k, st) in enumerate(STAGES.items()):
        x = left + i * (col_w + gap)
        # arrow from bar to column header with verb
        out.append(f'<line x1="{x + col_w/2:.1f}" y1="93" x2="{x + col_w/2:.1f}" y2="{y0 - 3}" stroke="{MUTED}" stroke-width="1.2" marker-end="url(#arr)"/>')
        out.append(f'<rect x="{x + col_w/2 - 34:.1f}" y="98" width="68" height="16" rx="8" fill="{SURFACE}"/>')
        out.append(t(x + col_w / 2, 110, st['verb'], 10.5, MUTED, 600, 'middle'))
        out.append(f'<rect x="{x}" y="{y0}" width="{col_w}" height="36" rx="5" fill="{st["color"]}" fill-opacity="0.16" stroke="{st["color"]}" stroke-width="1.2"/>')
        out.append(f'<rect x="{x + 10}" y="{y0 + 11}" width="14" height="14" rx="3" fill="{st["color"]}"/>')
        out.append(t(x + 32, y0 + 23, st['name'].upper(), 13, INK, 800, extra='letter-spacing=".1em"'))
        # cards
        y = y0 + 46
        mine = [c for c in cats if stage_key(c.get('stage')) == k]
        if not mine:
            out.append(t(x + 12, y + 18, '— no category ranked here —', 12, MUTED, 400))
            y += 30
        for c in mine:
            name_lines = wrap(sname(c, True), 26, 2)
            subs = SUBS.get(c.get('slug')) or [wrap(s.split(' (')[0].split(':')[0], 31, 1)[0] for s in (c.get('sub_techniques') or [])[:5]]
            h = 12 + 17 * len(name_lines) + 18 + 15 * len(subs) + 10
            out.append(f'<rect x="{x}" y="{y}" width="{col_w}" height="{h}" rx="5" fill="{SURFACE}" stroke="{HAIR}"/>')
            out.append(f'<circle cx="{x + 16}" cy="{y + 18}" r="10" fill="{INK}"/>')
            out.append(t(x + 16, y + 22, str(c.get('rank', '')), 11, '#fff', 700, 'middle'))
            out.append(tlines(x + 32, y + 22, name_lines, 13, 17, INK, 700))
            yy = y + 12 + 17 * len(name_lines) + 12
            out.append(t(x + 32, yy, f"{c.get('source_count', 0)} sources in this survey", 11, MUTED))
            for s in subs:
                yy += 15; out.append(t(x + 32, yy, '· ' + s, 11.5, INK2))
            y += h + 8
        maxh = max(maxh, y)
        # blurb under column
        bodies.append((x, st['blurb']))
    yb = maxh + 6
    for x, blurb in bodies:
        out.append(tlines(x, yb + 12, wrap(blurb, 34, 3), 11, 14, MUTED))
    H = yb + 12 + 14 * 3 + 10
    out[0] = out[0].replace('viewBox="0 0 %d 10"' % W, f'viewBox="0 0 {W} {H:.0f}"')
    out.append('</svg>'); return ''.join(out)

# ---------------- Figure 2: popularity ranking ----------------
def svg_popularity(cats):
    rows = sorted(cats, key=lambda c: c.get('rank', 99))
    W = 820; lab_w = 270; x0 = lab_w + 10; bar_w = W - x0 - 70; rh = 46; top = 26
    mx = max([c.get('source_count', 0) for c in rows] + [1])
    H = top + rh * len(rows) + 70
    out = [svg_open(W, H, 'Popularity ranking by number of sources', minw=640)]
    # gridlines
    step = 5 if mx <= 30 else 10
    for v in range(0, mx + step, step):
        gx = x0 + bar_w * v / mx
        if gx > x0 + bar_w + 1: break
        out.append(f'<line x1="{gx:.1f}" y1="{top - 6}" x2="{gx:.1f}" y2="{top + rh*len(rows)}" stroke="{HAIR}" stroke-width="1"/>')
        out.append(t(gx, top + rh * len(rows) + 16, str(v), 11, MUTED, 400, 'middle'))
    out.append(f'<line x1="{x0}" y1="{top - 6}" x2="{x0}" y2="{top + rh*len(rows)}" stroke="#c3c2b7" stroke-width="1"/>')
    for i, c in enumerate(rows):
        y = top + i * rh; col = STAGES[stage_key(c.get('stage'))]['color']
        name_lines = wrap(sname(c, True), 30, 2)
        out.append(f'<circle cx="18" cy="{y + rh/2:.1f}" r="11" fill="{INK}"/>')
        out.append(t(18, y + rh / 2 + 4, str(c.get('rank', '')), 11.5, '#fff', 700, 'middle'))
        out.append(tlines(38, y + rh / 2 - (6 if len(name_lines) > 1 else -1), name_lines, 13, 15, INK, 600))
        bw = bar_w * c.get('source_count', 0) / mx; bh = 18; by = y + rh / 2 - bh / 2
        out.append(f'<path d="M{x0},{by:.1f} h{max(bw-4,0):.1f} a4,4 0 0 1 4,4 v{bh-8} a4,4 0 0 1 -4,4 h-{max(bw-4,0):.1f} z" fill="{col}"><title>{esc(c["name"])}: {c.get("source_count",0)} sources</title></path>')
        out.append(t(x0 + bw + 8, y + rh / 2 + 4, str(c.get('source_count', 0)), 12.5, INK2, 600))
    # legend
    ly = top + rh * len(rows) + 44; lx = 38
    out.append(t(lx, ly, 'Stage:', 11.5, MUTED, 600)); lx += 44
    for k, st in STAGES.items():
        out.append(f'<rect x="{lx}" y="{ly - 10}" width="12" height="12" rx="2" fill="{st["color"]}"/>')
        out.append(t(lx + 17, ly, st['name'], 11.5, INK2)); lx += 17 + 7.2 * len(st['name']) + 22
    out.append(t(W - 8, ly, 'bar = distinct sources that substantively cover the technique', 11, MUTED, 400, 'end'))
    out.append('</svg>'); return ''.join(out)

# ---------------- Figure 3: recipe map (ways × how to achieve) ----------------
def svg_recipe_map(summaries, cats_by_slug):
    rows = sorted(summaries, key=lambda s: cats_by_slug.get(s['slug'], {}).get('rank', 99))
    nmax = max([len(s.get('steps') or []) for s in rows] + [3]); nmax = min(nmax, 6)
    lab_w = 262; cw = 184; ch = 58; cg = 6; rh = 78; top = 34
    W = lab_w + nmax * (cw + cg) + 16; H = top + rh * len(rows) + 12
    out = [svg_open(W, H, 'Recipe map: each technique and the steps to implement it', minw=1000)]
    out.append(t(lab_w + 6, 20, 'HOW TO ACHIEVE IT  →  implementation steps, left to right', 11, MUTED, 700, extra='letter-spacing=".08em"'))
    out.append(t(16, 20, 'TECHNIQUE (by popularity)', 11, MUTED, 700, extra='letter-spacing=".08em"'))
    for i, s in enumerate(rows):
        y = top + i * rh; c = cats_by_slug.get(s['slug'], {}); col = STAGES[stage_key(s.get('stage') or c.get('stage'))]['color']
        if i % 2 == 0: out.append(f'<rect x="0" y="{y - 6}" width="{W}" height="{rh}" fill="{BG}"/>')
        out.append(f'<circle cx="22" cy="{y + ch/2:.1f}" r="12" fill="{INK}"/>')
        out.append(t(22, y + ch / 2 + 4.5, str(c.get('rank', i + 1)), 12, '#fff', 700, 'middle'))
        name_lines = wrap(sname(c) if c else s.get('name'), 26, 2)
        out.append(tlines(44, y + ch / 2 - (6 if len(name_lines) > 1 else -2), name_lines, 13.5, 16, INK, 700))
        out.append(f'<rect x="44" y="{y + ch - 4}" width="10" height="10" rx="2" fill="{col}"/>')
        out.append(t(58, y + ch + 5, STAGES[stage_key(s.get('stage') or c.get('stage'))]['name'], 10.5, MUTED, 600))
        for j, step in enumerate((s.get('steps') or [])[:nmax]):
            x = lab_w + j * (cw + cg)
            out.append(chevron(x, y, cw, ch, col, first=(j == 0)))
            lines = wrap(f'{j+1}. {step}', 24, 4)
            ty = y + ch / 2 - (len(lines) - 1) * 6.5 + 4
            out.append(tlines(x + (14 if j == 0 else 22), ty, lines, 11.2, 13, INK, 600 if j == 0 else 500))
    out.append('</svg>'); return ''.join(out)

# ---------------- per-section rail ----------------
def svg_rail(steps, color, name):
    n = min(len(steps), 6); cw = 186; ch = 54; W = n * (cw + 4) + 8; H = ch + 8
    out = [svg_open(W, H, f'Steps to implement {name}', minw=min(W, 900))]
    for j, step in enumerate(steps[:n]):
        x = 4 + j * (cw + 4)
        out.append(chevron(x, 4, cw, ch, color, first=(j == 0)))
        lines = wrap(f'{j+1}. {step}', 25, 4); ty = 4 + ch / 2 - (len(lines) - 1) * 6.5 + 4
        out.append(tlines(x + (14 if j == 0 else 22), ty, lines, 11.2, 13, INK, 600 if j == 0 else 500))
    out.append('</svg>'); return ''.join(out)

# ---------------- Figure 4: decision flow (spec supplied in decision.json) ----------------
def svg_flow(spec):
    W, H = spec['w'], spec['h']
    out = [svg_open(W, H, spec.get('title', 'Decision flow'), minw=spec.get('minw', 900)), ARROW_DEFS]
    nodes = {n['id']: n for n in spec['nodes']}
    for e in spec['edges']:
        a, b = nodes[e['from']], nodes[e['to']]
        ax, ay = a['x'] + a['w'] / 2, a['y'] + a['h'] / 2; bx, by = b['x'] + b['w'] / 2, b['y'] + b['h'] / 2
        # exit/entry points on box edges (orthogonal-ish routing)
        if abs(by - ay) >= abs(bx - ax):  # vertical-ish
            sy = a['y'] + a['h'] if by > ay else a['y']; ey = b['y'] if by > ay else b['y'] + b['h']
            d = f'M{ax},{sy} L{ax},{(sy+ey)/2} L{bx},{(sy+ey)/2} L{bx},{ey}'; lx, ly = (ax + bx) / 2, (sy + ey) / 2 - 6
        else:
            sx = a['x'] + a['w'] if bx > ax else a['x']; ex = b['x'] if bx > ax else b['x'] + b['w']
            d = f'M{sx},{ay} L{(sx+ex)/2},{ay} L{(sx+ex)/2},{by} L{ex},{by}'; lx, ly = (sx + ex) / 2, min(ay, by) - 8
        out.append(f'<path d="{d}" fill="none" stroke="{MUTED}" stroke-width="1.3" marker-end="url(#arr)"/>')
        if e.get('label'):
            lw = 7 * len(e['label']) + 12
            out.append(f'<rect x="{lx - lw/2:.1f}" y="{ly - 11}" width="{lw:.1f}" height="16" rx="8" fill="{SURFACE}" stroke="{HAIR}"/>')
            out.append(t(lx, ly + 1, e['label'], 10.5, INK2, 600, 'middle'))
    for n in spec['nodes']:
        kind = n.get('kind', 'q')
        if kind == 'q':
            out.append(f'<rect x="{n["x"]}" y="{n["y"]}" width="{n["w"]}" height="{n["h"]}" rx="6" fill="{SURFACE}" stroke="{INK}" stroke-width="1.3"/>')
            fill, weight = INK, 600
        elif kind == 'start':
            out.append(f'<rect x="{n["x"]}" y="{n["y"]}" width="{n["w"]}" height="{n["h"]}" rx="{n["h"]/2}" fill="{INK}"/>'); fill, weight = '#fff', 700
        else:
            col = STAGES[stage_key(n.get('stage'))]['color']
            out.append(f'<rect x="{n["x"]}" y="{n["y"]}" width="{n["w"]}" height="{n["h"]}" rx="6" fill="{col}" fill-opacity="0.16" stroke="{col}" stroke-width="1.3"/>'); fill, weight = INK, 700
        lines = wrap(n['text'], n.get('chars', 24), 4); size = n.get('size', 12)
        ty = n['y'] + n['h'] / 2 - (len(lines) - 1) * size * 0.62 + size * 0.35
        out.append(tlines(n['x'] + n['w'] / 2, ty, lines, size, size * 1.25, fill, weight, 'middle'))
        if n.get('sub'):
            out.append(t(n['x'] + n['w'] / 2, n['y'] + n['h'] + 13, n['sub'], 10.5, MUTED, 500, 'middle'))
    out.append('</svg>'); return ''.join(out)

# ---------------- fragment hygiene ----------------
def clean_fragment(frag):
    frag = re.sub(r'<script\b.*?</script>', '', frag, flags=re.S | re.I)
    frag = re.sub(r'<style\b.*?</style>', '', frag, flags=re.S | re.I)
    frag = re.sub(r'\sstyle="[^"]*"', '', frag)
    frag = re.sub(r'<a\s+(?![^>]*target=)', '<a target="_blank" rel="noopener" ', frag)
    return frag.strip()

# ---------------- main ----------------
def main():
    res = json.load(open(os.path.join(DIR, 'result.json'))) if os.path.exists(os.path.join(DIR, 'result.json')) else {}
    cats = res.get('categories') or []
    if not cats and os.path.exists(os.path.join(DIR, 'taxonomy.json')):
        tx = json.load(open(os.path.join(DIR, 'taxonomy.json')))
        cats = [dict(c, rank=c.get('popularity_rank')) for c in tx.get('categories', [])]
    tax_notes = ''
    if os.path.exists(os.path.join(DIR, 'taxonomy.json')):
        try: tax_notes = json.load(open(os.path.join(DIR, 'taxonomy.json'))).get('notes', '')
        except Exception as e: print('taxonomy notes skipped:', e)
    summaries = list(res.get('summaries') or []) + list(res.get('gapSummaries') or [])
    # addenda become categories ranked after the taxonomy
    for i, g in enumerate(res.get('gapSummaries') or []):
        cats.append(dict(slug=g['slug'], name=g['name'], stage=g.get('stage'), rank=len(cats) + 1,
                         source_count=(g.get('popularity') or {}).get('source_count', len(g.get('sources') or [])),
                         sub_techniques=g.get('tools') or [], signals=(g.get('popularity') or {}).get('signals', []), addendum=True))
    cats = sorted(cats, key=lambda c: c.get('rank', 99))
    cats_by_slug = {c['slug']: c for c in cats}
    sums_by_slug = {s['slug']: s for s in summaries}
    framings = res.get('framings') or []

    # dead links (from links.tsv: status<TAB>url) and citation counts (Semantic Scholar dump)
    dead = set()
    lt = os.path.join(DIR, 'links.tsv')
    if os.path.exists(lt):
        for line in open(lt):
            parts = line.rstrip('\n').split('\t')
            if len(parts) == 2 and parts[0] in ('404', '410'): dead.add(norm_url(parts[1]))
    cites = {}
    ssp = os.path.join(DIR, 'semanticscholar_papers.json')
    if os.path.exists(ssp):
        try:
            for pp in json.load(open(ssp)):
                ax = ((pp.get('externalIds') or {}).get('ArXiv') or '').split('v')[0]
                if ax and pp.get('citationCount') is not None: cites[ax] = pp['citationCount']
        except Exception as e: print('citations skipped:', e)
    def arxiv_id(u):
        m = re.search(r'arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5})', u or '')
        return m.group(1) if m else None
    # sources index from sweep files
    all_src = OrderedDict()
    for f in sorted(glob.glob(os.path.join(DIR, 'sweep', '*.json'))):
        try: data = json.load(open(f))
        except Exception as e: print('skip', f, e); continue
        for s in data.get('sources', []):
            k = norm_url(s.get('url'))
            if k in dead: print('dropping dead link', s.get('url')); continue
            if k and k not in all_src: all_src[k] = dict(s, modality=os.path.basename(f)[:-5])
    by_type = Counter((s.get('type') or 'other') for s in all_src.values())
    total = res.get('totalUniqueSources') or len(all_src)

    # fragments
    sections_html = []
    for c in cats:
        path = os.path.join(DIR, 'sections', f"{c['slug']}.html")
        if not os.path.exists(path):
            print('MISSING fragment', path); continue
        frag = clean_fragment(open(path, encoding='utf-8').read())
        s = sums_by_slug.get(c['slug']); st = STAGES[stage_key(c.get('stage') or (s or {}).get('stage'))]
        meta = (f'<div class="meta-row"><span class="stage-chip"><i class="dot" style="background:{st["color"]}"></i>{st["name"]} · {st["verb"]}</span>'
                + (f'<span>Addendum · added by the completeness check</span>' if c.get('addendum') else f'<span>Popularity rank #{c.get("rank")}</span>')
                + f'<span>·</span><span>{c.get("source_count", 0)} sources in this survey</span></div>')
        rail = ''
        if s and s.get('steps'):
            rail = (f'<figure class="rail"><div class="scroll">{svg_rail(s["steps"], st["color"], s.get("name") or c["name"])}</div>'
                    f'<figcaption><span class="swipe">Swipe sideways for all steps. </span><b>Recipe.</b> {esc(s.get("one_line", ""))}</figcaption></figure>')
        # inject meta after h2, rail before first h3
        frag = re.sub(r'(</h2>)', r'\1' + meta, frag, count=1)
        frag = re.sub(r'(<h3>)', rail + r'\1', frag, count=1)
        sections_html.append(frag)

    decision = json.load(open(os.path.join(DIR, 'decision.json'))) if os.path.exists(os.path.join(DIR, 'decision.json')) else None

    # ---- nav ----
    def short(n):
        n = re.split(r'\s[\(—–-]\s|\(', n)[0].strip(); return n if len(n) <= 30 else n[:29].rstrip() + '…'
    nav = ['<li><a href="#glance">At a glance</a></li>'] + \
          [f'<li><a href="#{esc(c["slug"])}">{c.get("rank")}. {esc(sname(c))}</a></li>' for c in cats if c['slug'] in sums_by_slug or os.path.exists(os.path.join(DIR, 'sections', c['slug'] + '.html'))]
    if decision: nav.append('<li><a href="#decide">Which one when</a></li>')
    nav.append('<li><a href="#method">Method &amp; sources</a></li>')

    # ---- tiles ----
    type_order = ['paper', 'blog', 'docs', 'repo', 'video', 'talk', 'thread', 'other']
    PLURAL = dict(paper='papers', blog='blog posts', docs='doc pages', repo='repos', video='videos', talk='talks', thread='threads', other='other')
    tiles = [f'<div class="tile"><b>{total}</b><span>sources</span></div>'] + \
            [f'<div class="tile"><b>{by_type[tp]}</b><span>{PLURAL[tp]}</span></div>' for tp in type_order if by_type.get(tp)]

    # ---- popularity table twin ----
    table = ['<div class="table-wrap"><table><thead><tr><th>#</th><th>Technique</th><th>Stage</th><th class="n">Sources</th><th>Popularity signals</th></tr></thead><tbody>']
    for c in cats:
        sig = '; '.join((c.get('signals') or [])[:3])
        table.append(f'<tr><td>{c.get("rank")}{" †" if c.get("addendum") else ""}</td><td><a href="#{esc(c["slug"])}">{esc(c["name"])}</a></td><td>{STAGES[stage_key(c.get("stage"))]["name"]}</td><td class="n">{c.get("source_count", 0)}</td><td>{esc(sig)}</td></tr>')
    table.append('</tbody></table></div>')

    framings_html = ''.join(f'<li><a href="{esc(f["source_url"])}" target="_blank" rel="noopener">{esc(f["name"])}</a> — {esc(f["description"])}</li>' for f in framings)

    # ---- source index ----
    idx = []
    for tp in type_order:
        items = [s for s in all_src.values() if (s.get('type') or 'other') == tp]
        if not items: continue
        items.sort(key=lambda s: (-(s.get('year') or 0), (s.get('title') or '').lower()))
        def cite_note(s):
            c = cites.get(arxiv_id(s.get('url')) or '')
            return f' <span class="tags">· {c:,} citations</span>' if c else ''
        lis = ''.join(f'<li><a href="{esc(s.get("url"))}" target="_blank" rel="noopener">{esc(s.get("title"))}</a> — {esc(s.get("venue_or_author"))}, {esc(s.get("year"))}{cite_note(s)}'
                      + (f' <span class="tags">{esc(", ".join((s.get("techniques") or [])[:3]))}</span>' if s.get('techniques') else '') + '</li>' for s in items)
        idx.append(f'<details><summary>{tp.capitalize()}s ({len(items)})</summary><ol class="sources">{lis}</ol></details>')

    sweep_stats = res.get('sweepStats') or {}
    stats_lis = ''.join(f'<li><b>{esc(k)}</b>: {v.get("unique_kept", v.get("returned", 0))} unique sources kept' + (f' — <span class="muted">{esc(v.get("note", ""))[:220]}</span>' if v.get('note') else '') + '</li>' for k, v in sweep_stats.items())
    critic = res.get('critic') or {}

    fig_decide = ''
    if decision:
        fig_decide = (f'<section class="part wide" id="decide"><h2>Which one to reach for</h2><p class="lede">{esc(decision.get("lede", ""))}</p>'
                      f'<figure><div class="scroll">{svg_flow(decision)}</div><figcaption><span class="swipe">Swipe sideways to see the whole figure. </span><b>Figure 4.</b> {esc(decision.get("caption", ""))}</figcaption></figure></section>')

    body = f'''
<header class="masthead"><div class="wrap">
  <p class="eyebrow">Research report · {TODAY} · {total} sources across papers, blogs, docs, videos and community threads</p>
  <h1>Context Window Playbook</h1>
  <p class="dek">The popular ways engineers manage an LLM's context window — summarize, retrieve, remember, prune, compress, isolate, and the model-level foundations underneath — ranked by how much the literature and the community talk about them, each with a concrete recipe for implementing it.</p>
  <div class="tiles">{''.join(tiles)}</div>
</div></header>
<nav class="toc"><div class="wide"><ul>{''.join(nav)}</ul></div></nav>
<main>
<section class="part wide" id="glance">
  <h2>At a glance</h2>
  <p class="lede">Almost every technique is one of four verbs applied to the window — <b>write</b> context out, <b>select</b> context in, <b>compress</b> what stays, <b>isolate</b> work into separate windows — resting on a <b>foundations</b> layer of model and serving capabilities. The map below places each ranked technique on that lifecycle.</p>
  <figure><div class="scroll">{svg_lifecycle(cats)}</div><figcaption><span class="swipe">Swipe sideways to see the whole figure. </span><b>Figure 1.</b> The context lifecycle. Top: what a single call's window contains. Columns: the five stages and the techniques that act on them, numbered by popularity rank († = addendum from the completeness check).</figcaption></figure>
  <figure><div class="scroll">{svg_popularity(cats)}</div><figcaption><span class="swipe">Swipe sideways to see the whole figure. </span><b>Figure 2.</b> Bars show how many distinct sources in this survey substantively cover each technique. The rank number also weighs external signals (GitHub stars, citations, views, how many frameworks ship it), which is why a few neighbours swap order by a source or two. † = addendum added by the completeness check; its bar counts that section's own sources. Values and signals in the table below.</figcaption>
    <details><summary>Table view</summary>{''.join(table)}</details></figure>
  <figure><div class="scroll">{svg_recipe_map(summaries, cats_by_slug)}</div><figcaption><span class="swipe">Swipe sideways to see the whole figure. </span><b>Figure 3.</b> How to achieve each technique, compressed to its implementation steps. Each row's detailed section follows, with code and sources.</figcaption></figure>
  <h3>The framings the field already uses</h3>
  <p>Several well-known write-ups organise the same techniques in their own way. This report's categories map onto all of them:</p>
  <ul class="framings">{framings_html}</ul>
</section>
{''.join(f'<div class="wrap">{s}</div>' for s in sections_html)}
{fig_decide}
<section class="part wrap" id="method">
  <h2>Method &amp; sources</h2>
  <p>Six parallel research sweeps ran on {TODAY}, each restricted to one kind of source and capped at roughly 14 searches / 8 page fetches / 15 minutes: academic papers, industry engineering blogs, videos and conference talks, social and community threads, framework and tool documentation, and model/inference-level research. Results were de-duplicated by URL, clustered into the categories above, and each category was then deep-read by a dedicated pass (≤ 10 fetches) that wrote its section from primary sources. A final completeness check looked for missing techniques and triggered one bounded gap-fill round.</p>
  <p><b>Popularity</b> is a source-count: how many distinct gathered sources substantively cover a technique. It is a measure of attention in the literature and community, not of production adoption, and is biased toward English-language, publicly indexed material (web search was US-only).</p>
  <ul>{stats_lis}</ul>
  <h3>How the ranking was decided</h3>
  <p>{esc(tax_notes)}</p>
  <p><b>Completeness check:</b> verdict <i>{esc(critic.get("verdict", "n/a"))}</i>. {esc(critic.get("notes", ""))}</p>
  <h3>Source index</h3>
  <p class="muted">All {len(all_src)} unique sources gathered by the sweeps, grouped by type, newest first. The per-technique source lists above are the curated subset actually read.</p>
  {''.join(idx)}
</section>
</main>
<footer class="wrap"><p class="muted">Compiled {TODAY} by Claude Code (multi-agent research workflow). Every link was present in a search result or fetched page at research time; verify details against the primary sources before relying on them.</p></footer>
'''
    css = open(os.path.join(DIR, 'style.css'), encoding='utf-8').read()
    fonts = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=Source+Sans+3:ital,wght@0,400;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;600&display=swap">'
    title = '<title>Context Window Playbook</title>'
    art = f'{title}\n{fonts}\n<style>{css}</style>\n{body}'
    full = f'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n{title}\n{fonts}\n<style>{css}</style>\n</head>\n<body>\n{body}\n</body>\n</html>\n'
    open(OUT_FULL, 'w', encoding='utf-8').write(full); open(OUT_ART, 'w', encoding='utf-8').write(art)
    print(f'wrote {OUT_FULL} ({len(full)//1024} KB) and artifact variant; categories={len(cats)} sections={len(sections_html)} summaries={len(summaries)} sources={len(all_src)}')

if __name__ == '__main__':
    main()
