#!/usr/bin/env python3
"""Assemble the context-management MARKET report from the ctx-market-research workflow outputs.
Inputs (this dir): result.json (workflow return), sections/*.html, sweep/*.json
Outputs: market-report.html (standalone) + market-report.artifact.html (body-only)
Reuses SVG/text helpers from ../build.py.
"""
import json, re, os, sys, glob, math, html
from collections import OrderedDict, Counter
SRC = os.path.dirname(os.path.abspath(__file__))
HERE = os.environ.get('MARKET_DIR', SRC)
sys.path.insert(0, os.path.dirname(SRC))
import build as base  # noqa: E402  (helpers: t, tlines, wrap, chevron, svg_open, svg_rail, esc, norm_url, clean_fragment, STAGES, colours)
from build import series_nav, t, tlines, wrap, chevron, svg_open, svg_rail, esc, norm_url, clean_fragment, INK, INK2, MUTED, HAIR, SURFACE, BG, ACCENT, ARROW_DEFS, fmt_stars  # noqa: E402

TODAY = '2026-08-21'
OUT_FULL = os.path.join(HERE, 'market-report.html'); OUT_ART = os.path.join(HERE, 'market-report.artifact.html')
# validated categorical set (all-pairs on white): blue, orange, violet, aqua + neutral
CAT_COLORS = OrderedDict([('memory-layer', '#2a78d6'), ('retrieval-rag', '#1baf7a'), ('vector-graph-db', '#eb6834'), ('observability-evals', '#4a3aa7'), ('other', '#5b6472')])
CAT_NAMES = {'memory-layer': 'Memory layer', 'retrieval-rag': 'Retrieval / RAG', 'vector-graph-db': 'Vector & graph DBs', 'observability-evals': 'Observability & evals', 'framework': 'Frameworks', 'gateway-caching': 'Gateways & caching', 'coding-agent': 'Coding agents', 'consumer-memory': 'Consumer memory', 'other': 'Other'}
RAMP = ['#86b6ef', '#2a78d6', '#104281']  # ordinal blue steps 250 / 450 / 650 (low / mid / high)
def ramp(v, lo=1, hi=5):
    return RAMP[0] if v <= 2 else (RAMP[1] if v == 3 else RAMP[2])
LANES = OrderedDict([('memory-layer', ('Context & memory layer', '#2a78d6')), ('retrieval-rag', ('Retrieval / RAG', '#1baf7a')), ('vector-graph-db', ('Vector & graph DBs', '#eb6834')), ('observability-evals', ('Observability & evals', '#4a3aa7')), ('framework', ('Frameworks & tooling', '#5b6472')), ('application', ('Applications & agents', '#8a93a3')), ('serving-infra', ('Serving & infra', '#5b6472')), ('other', ('Other', '#8a93a3'))])
def norm_cat(c):
    c = (c or '').lower()
    if 'memory' in c: return 'memory-layer'
    if 'retriev' in c or 'rag' in c or 'search' in c: return 'retrieval-rag'
    if 'vector' in c or 'graph' in c or c.endswith('db') or 'database' in c: return 'vector-graph-db'
    if 'observ' in c or 'eval' in c: return 'observability-evals'
    if 'framework' in c or 'tooling' in c: return 'framework'
    if 'app' in c or 'agent' in c: return 'application'
    if 'serving' in c or 'infra' in c or 'gateway' in c or 'caching' in c: return 'serving-infra'
    return 'other'
def cat_color(c): return CAT_COLORS.get(c, CAT_COLORS['other'])
def money(n):
    if not n: return 'undisclosed'
    return f'${n/1e9:.1f}B' if n >= 1e9 else (f'${n/1e6:.0f}M' if n >= 1e6 else f'${n/1e3:.0f}K')
def fund_link(s):
    u = str(s.get('funding_source_url', '') or '')
    return f'<a href="{esc(u)}" target="_blank" rel="noopener">link</a>' if u.startswith('http') else '—'
def cust(s):
    return {'developers': 'Developers', 'both': 'Developers + enterprise', 'enterprise': 'Enterprise', 'consumer': 'Consumer'}.get(s, s or '?')

# ---------------- F1: value chain ----------------
def svg_value_chain(layers, startups):
    W = 1120; left = 16; y = 16; out = [svg_open(W, 10, 'Value chain of the context-management market', minw=900)]
    by_name = {s['name'].lower(): s for s in startups}
    for i, L in enumerate(layers):
        desc = wrap(L.get('description', ''), 58, 2)
        chips = []; x = left + 300; cy = y + 34; maxh = 0; rowh = 26
        for p in (L.get('players') or [])[:14]:
            lab = p; s = by_name.get(p.lower()); 
            if s and s.get('total_funding_usd'): lab = f'{p} · {money(s["total_funding_usd"])}'
            w = 7.2 * len(lab) + 18
            if x + w > W - left: x = left + 300; cy += rowh
            chips.append((x, cy, w, lab)); x += w + 8
        h = max(70, (cy - y) + 36)
        out.append(f'<rect x="{left}" y="{y}" width="{W-2*left}" height="{h}" rx="6" fill="{SURFACE if i % 2 else BG}" stroke="{HAIR}"/>')
        out.append(t(left + 14, y + 26, L.get('layer', ''), 14, INK, 700))
        out.append(tlines(left + 14, y + 46, desc, 11.5, 14, MUTED))
        for cx, cy2, w, lab in chips:
            out.append(f'<rect x="{cx:.1f}" y="{cy2 - 16}" width="{w:.1f}" height="22" rx="11" fill="{SURFACE}" stroke="{HAIR}"/>')
            out.append(t(cx + w / 2, cy2 - 1, lab, 11.5, INK2, 600, 'middle'))
        y += h + 10
    out[0] = out[0].replace(f'viewBox="0 0 {W} 10"', f'viewBox="0 0 {W} {y + 6}"'); out.append('</svg>'); return ''.join(out)

# ---------------- label placement (radial, right/left) ----------------
def place_points(items, key_xy, X, Y, jitter=20):
    """Return [(cx, cy, item, ang)] with same-coordinate groups spread on a ring."""
    groups = {}
    for it in items: groups.setdefault(key_xy(it), []).append(it)
    out = []
    for (fx, fy), its in groups.items():
        n = len(its)
        for k, it in enumerate(its):
            ang = (2 * math.pi * k / n + (0.0 if n == 2 else -math.pi / 2)) if n > 1 else 0.0
            off = 0 if n == 1 else jitter
            out.append((X(fx) + off * math.cos(ang), Y(fy) + off * math.sin(ang), it, ang if n > 1 else None))
    return out
def num_in(cx, cy, n, fill, size=10):
    ink = INK if fill == RAMP[0] else '#ffffff'
    return t(cx, cy + size * 0.36, str(n), size, ink, 700, 'middle')
def key_list(x, y, items, size=11, lh=16, width=30):
    out = []
    for n, name in items:
        lines = wrap(name, width, 2)
        out.append(f'<circle cx="{x + 7}" cy="{y - 4}" r="7" fill="{INK}"/>' + t(x + 7, y - 0.5, str(n), 9, '#fff', 700, 'middle'))
        out.append(tlines(x + 20, y, lines, size, lh - 3, INK2, 600)); y += lh + (lh - 3) * (len(lines) - 1)
    return ''.join(out), y
def label_for(cx, cy, r, ang, text, mid_x, size=10.5, width=22):
    """Radial label: for ring members follow the ring angle; singles go right unless near the right edge."""
    lines = wrap(text, width, 2); lh = size * 1.15
    if ang is None:
        right = cx < mid_x
        x = cx + r + 6 if right else cx - r - 6
        return tlines(x, cy + 4 - (len(lines) - 1) * lh / 2, lines, size, lh, INK, 600, 'start' if right else 'end')
    dx, dy = math.cos(ang), math.sin(ang)
    x = cx + (r + 6) * dx; y = cy + (r + 6) * dy
    anchor = 'start' if dx > 0.3 else ('end' if dx < -0.3 else 'middle')
    y_adj = y + (4 if abs(dy) < 0.3 else (lh * len(lines) - 2 if dy > 0 else -(lh * (len(lines) - 1)) - 2))
    return tlines(x, y_adj, lines, size, lh, INK, 600, anchor)

# ---------------- F2: problem map + ranked opportunity ----------------
def score(p): return round(p['frequency'] * p['severity'] * p['willingness_to_pay'] / max(p['platform_risk'], 1), 1)
def svg_problem_map(problems):
    ranked = sorted(problems, key=lambda p: -score(p)); rank = {p['id']: i + 1 for i, p in enumerate(ranked)}
    W = 960; key_h = 26 * len(ranked) + 30 + 200; H = max(560, key_h + 40); x0, y0, pw, ph = 70, 30, W - 70 - 320, min(H - 30 - 80, 470)
    def X(v): return x0 + pw * (v - 0.6) / 4.8
    def Y(v): return y0 + ph - ph * (v - 0.6) / 4.8
    out = [svg_open(W, H, 'Problem map: frequency versus severity, bubble size = willingness to pay, shade = platform risk', minw=760)]
    for v in range(1, 6):
        out.append(f'<line x1="{X(v):.1f}" y1="{y0}" x2="{X(v):.1f}" y2="{y0 + ph}" stroke="{HAIR}"/>'); out.append(t(X(v), y0 + ph + 18, str(v), 11, MUTED, 400, 'middle'))
        out.append(f'<line x1="{x0}" y1="{Y(v):.1f}" x2="{x0 + pw}" y2="{Y(v):.1f}" stroke="{HAIR}"/>'); out.append(t(x0 - 10, Y(v) + 4, str(v), 11, MUTED, 400, 'end'))
    out.append(t(x0 + pw / 2, y0 + ph + 38, 'How often teams hit it (frequency, 1–5)', 11.5, MUTED, 600, 'middle'))
    out.append(f'<text transform="translate(18,{y0 + ph/2:.0f}) rotate(-90)" font-size="11.5" fill="{MUTED}" font-weight="600" text-anchor="middle" font-family="inherit">How much it hurts (severity, 1–5)</text>')
    placed = place_points(problems, lambda p: (p['frequency'], p['severity']), X, Y, jitter=24)
    for cx, cy, p, ang in sorted(placed, key=lambda z: -(5 + 2.2 * z[2]['willingness_to_pay'])):
        r = 7 + 2.4 * p['willingness_to_pay']; fill = ramp(p['platform_risk'])
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}" stroke="{SURFACE}" stroke-width="2"><title>#{rank[p["id"]]} {esc(p["name"])}: freq {p["frequency"]}, sev {p["severity"]}, WTP {p["willingness_to_pay"]}, platform risk {p["platform_risk"]}</title></circle>')
        out.append(num_in(cx, cy, rank[p['id']], fill))
    lx, ly = x0 + pw + 24, y0 + 10
    out.append(t(lx, ly, 'Number = opportunity rank (Figure 3)', 11, MUTED, 600)); ly += 18
    kl, ly = key_list(lx, ly, [(rank[p['id']], p['name']) for p in ranked], width=34); out.append(kl); ly += 10
    out.append(t(lx, ly, 'Bubble = willingness to pay', 11, MUTED, 600)); ly += 20
    for v in (1, 3, 5):
        out.append(f'<circle cx="{lx + 12}" cy="{ly - 4}" r="{5 + 2.2 * v:.1f}" fill="none" stroke="{INK2}"/>'); out.append(t(lx + 34, ly, f'{v}', 11, INK2)); ly += 26
    ly += 8; out.append(t(lx, ly, 'Shade = platform risk', 11, MUTED, 600)); ly += 20
    for lab, col in (('1–2 low: vendors unlikely to absorb', RAMP[0]), ('3 medium', RAMP[1]), ('4–5 high: vendors likely to ship it', RAMP[2])):
        out.append(f'<circle cx="{lx + 12}" cy="{ly - 4}" r="7" fill="{col}"/>'); out.append(tlines(lx + 28, ly, wrap(lab, 26, 2), 11, 12, INK2)); ly += 30
    out.append('</svg>'); return ''.join(out)

def svg_opportunity_bars(problems):
    rows = sorted(problems, key=lambda p: -score(p)); W = 820; lab_w = 300; x0 = lab_w + 10; bw = W - x0 - 70; rh = 34; top = 16
    mx = max(score(p) for p in rows) or 1; H = top + rh * len(rows) + 44
    out = [svg_open(W, H, 'Opportunity score per problem', minw=640)]
    for i, p in enumerate(rows):
        y = top + i * rh; v = score(p); w = bw * v / mx
        out.append(t(12, y + rh / 2 + 4, f'{i+1}. {p["name"]}', 12.5, INK, 600))
        out.append(f'<path d="M{x0},{y + 8} h{max(w-4,0):.1f} a4,4 0 0 1 4,4 v10 a4,4 0 0 1 -4,4 h-{max(w-4,0):.1f} z" fill="{ramp(p["platform_risk"])}"><title>{esc(p["name"])}: score {v}</title></path>')
        out.append(t(x0 + w + 8, y + rh / 2 + 4, f'{v:g}', 11.5, INK2, 600))
    out.append(t(x0, H - 10, 'score = frequency × severity × willingness to pay ÷ platform risk; shade = platform risk', 11, MUTED))
    out.append('</svg>'); return ''.join(out)

# ---------------- F3: landscape matrix ----------------
def svg_landscape(startups):
    cats = [c for c in ['memory-layer', 'retrieval-rag', 'vector-graph-db', 'observability-evals', 'framework', 'gateway-caching', 'coding-agent', 'consumer-memory', 'other'] if any(s['category'] == c for s in startups)]
    cols = [c for c in ['developers', 'both', 'enterprise', 'consumer'] if any(s['target_customer'] == c for s in startups)]
    W = 1120; lab_w = 180; cw = (W - lab_w - 16) / max(len(cols), 1); top = 40; out = [svg_open(W, 10, 'Startup landscape: category by target customer, chips show funding', minw=900)]
    for j, c in enumerate(cols): out.append(t(lab_w + j * cw + cw / 2, 24, cust(c).upper(), 11, MUTED, 700, 'middle', extra='letter-spacing=".08em"'))
    y = top
    for cat in cats:
        rowmax = 0; cells = []
        for j, c in enumerate(cols):
            items = sorted([s for s in startups if s['category'] == cat and s['target_customer'] == c], key=lambda s: -(s.get('total_funding_usd') or 0))
            x = lab_w + j * cw + 8; cy = y + 24; chips = []
            for s in items:
                lab = s['name'] + (f' · {money(s["total_funding_usd"])}' if s.get('total_funding_usd') else '') + (' · OSS' if s.get('open_source') else '')
                w = 6.9 * len(lab) + 16
                if x + w > lab_w + (j + 1) * cw - 6 and x > lab_w + j * cw + 8: x = lab_w + j * cw + 8; cy += 26
                chips.append((x, cy, w, lab, s)); x += w + 6
            cells.append(chips); rowmax = max(rowmax, cy - y + 14)
        h = max(rowmax + 6, 44)
        out.append(f'<rect x="8" y="{y}" width="{W-16}" height="{h}" fill="{BG if cats.index(cat) % 2 == 0 else SURFACE}" stroke="{HAIR}"/>')
        out.append(f'<rect x="14" y="{y + 10}" width="10" height="10" rx="2" fill="{cat_color(cat)}"/>')
        out.append(tlines(30, y + 19, wrap(CAT_NAMES.get(cat, cat), 18, 2), 12.5, 14, INK, 700))
        for chips in cells:
            for cx, cy, w, lab, s in chips:
                out.append(f'<a href="{esc(s.get("url") or "#")}" target="_blank"><rect x="{cx:.1f}" y="{cy - 16}" width="{w:.1f}" height="22" rx="11" fill="{SURFACE}" stroke="{cat_color(cat)}" stroke-width="1.2"><title>{esc(s.get("product", ""))}</title></rect>')
                out.append(t(cx + w / 2, cy - 1, lab, 11, INK, 600, 'middle') + '</a>')
        y += h + 6
    out[0] = out[0].replace(f'viewBox="0 0 {W} 10"', f'viewBox="0 0 {W} {y + 6}"'); out.append('</svg>'); return ''.join(out)

# ---------------- F4: funding timeline ----------------
def ym(s):
    m = re.match(r'(\d{4})-(\d{2})', str(s)); return (int(m.group(1)) + (int(m.group(2)) - 1) / 12) if m else None
def svg_funding_timeline(rounds):
    rs = [r for r in rounds if ym(r.get('date')) and (r.get('amount_usd') or 0) > 0]
    if not rs: return ''
    for r in rs: r['_lane'] = norm_cat(r.get('category'))
    cats = [c for c in LANES if any(r['_lane'] == c for r in rs)]
    W = 1100; left = 170; right = 44; top = 34; lane = 72; x0 = left; pw = W - left - right
    lo = math.floor(min(ym(r['date']) for r in rs)); hi = max(ym(r['date']) for r in rs) + 0.25
    def X(v): return x0 + pw * (v - lo) / (hi - lo)
    H = top + lane * len(cats) + 50; out = [svg_open(W, H, 'Funding rounds 2024–2026 by category; bubble area = amount', minw=900)]
    yr = lo
    while yr <= hi:
        out.append(f'<line x1="{X(yr):.1f}" y1="{top - 8}" x2="{X(yr):.1f}" y2="{top + lane*len(cats)}" stroke="{HAIR}"/>'); out.append(t(min(X(yr), x0 + pw), top + lane * len(cats) + 16, str(int(yr)), 11, MUTED, 400, 'end' if X(yr) > x0 + pw - 24 else 'middle'))
        if yr + 0.5 <= hi: out.append(f'<line x1="{X(yr + 0.5):.1f}" y1="{top - 2}" x2="{X(yr + 0.5):.1f}" y2="{top + lane*len(cats)}" stroke="{HAIR}" stroke-dasharray="0" stroke-opacity="0.5"/>')
        yr += 1
    mxa = max(r['amount_usd'] for r in rs)
    for i, c in enumerate(cats):
        cy = top + i * lane + lane / 2
        out.append(f'<line x1="{x0}" y1="{cy:.1f}" x2="{x0 + pw}" y2="{cy:.1f}" stroke="{HAIR}"/>')
        name, col = LANES[c]
        out.append(f'<rect x="12" y="{cy - 6}" width="10" height="10" rx="2" fill="{col}"/>'); out.append(tlines(28, cy + 4, wrap(name, 20, 2), 12, 13, INK, 700))
        items = sorted([r for r in rs if r['_lane'] == c], key=lambda r: ym(r['date']))
        for k, r in enumerate(items):
            rad = 4 + 18 * math.sqrt(r['amount_usd'] / mxa); x = X(ym(r['date']))
            out.append(f'<circle cx="{x:.1f}" cy="{cy:.1f}" r="{rad:.1f}" fill="{col}" fill-opacity="0.7" stroke="{SURFACE}" stroke-width="1.5"><title>{esc(r["company"])} {esc(r["round"])} {money(r["amount_usd"])} ({esc(r["date"])}) lead: {esc(r.get("lead", ""))}</title></circle>')
            dy = [-rad - 6, rad + 14, -rad - 19][k % 3]
            out.append(t(x, cy + dy, f'{r["company"]} {money(r["amount_usd"])}', 10.5, INK2, 600, 'middle'))
    out.append('</svg>'); return ''.join(out)

# ---------------- F5: incumbent moves ----------------
def svg_incumbent_timeline(moves):
    ms = [m for m in moves if ym(m.get('date'))]
    if not ms: return ''
    vendors = list(OrderedDict.fromkeys(m['vendor'] for m in sorted(ms, key=lambda m: ym(m['date']))))
    W = 1100; left = 130; right = 44; top = 24; lane = 92; pw = W - left - right
    lo = math.floor(min(ym(m['date']) for m in ms)); hi = max(ym(m['date']) for m in ms) + 0.25
    def X(v): return left + pw * (v - lo) / (hi - lo)
    H = top + lane * len(vendors) + 70; out = [svg_open(W, H, 'Incumbent moves 2024–2026; shade = threat level to startups', minw=900)]
    yr = lo
    while yr <= hi:
        out.append(f'<line x1="{X(yr):.1f}" y1="{top - 6}" x2="{X(yr):.1f}" y2="{top + lane*len(vendors)}" stroke="{HAIR}"/>'); out.append(t(min(X(yr), left + pw), top + lane * len(vendors) + 16, str(int(yr)), 11, MUTED, 400, 'end' if X(yr) > left + pw - 24 else 'middle'))
        if yr + 0.5 <= hi: out.append(f'<line x1="{X(yr + 0.5):.1f}" y1="{top - 2}" x2="{X(yr + 0.5):.1f}" y2="{top + lane*len(vendors)}" stroke="{HAIR}" stroke-opacity="0.5"/>')
        yr += 1
    for i, v in enumerate(vendors):
        cy = top + i * lane + lane / 2
        out.append(f'<line x1="{left}" y1="{cy:.1f}" x2="{left + pw}" y2="{cy:.1f}" stroke="{HAIR}"/>'); out.append(tlines(12, cy + 4, wrap(v, 16, 2), 12, 13, INK, 700))
        items = sorted([m for m in ms if m['vendor'] == v], key=lambda m: ym(m['date']))
        for k, m in enumerate(items):
            x = X(ym(m['date'])); col = ramp(m.get('threat_level', 3))
            out.append(f'<circle cx="{x:.1f}" cy="{cy:.1f}" r="7" fill="{col}" stroke="{SURFACE}" stroke-width="1.5"><title>{esc(m["feature"])} ({esc(m["date"])}) threat {m.get("threat_level")}: {esc(m.get("commoditizes", ""))}</title></circle>')
            lab = wrap(m['feature'], 22, 3); dy = -14 - 11 * (len(lab) - 1) if k % 2 == 0 else 20
            out.append(tlines(x, cy + dy, lab, 10, 11, INK2, 600, 'middle'))
    ly = H - 32; lx = left
    out.append(t(lx, ly, 'Threat level:', 11, MUTED, 600)); lx += 82
    for lab, col in (('1–2 low', RAMP[0]), ('3 medium', RAMP[1]), ('4–5 high', RAMP[2])):
        out.append(f'<circle cx="{lx + 7}" cy="{ly - 4}" r="7" fill="{col}"/>'); out.append(t(lx + 20, ly, lab, 11, INK2)); lx += 100
    out.append('</svg>'); return ''.join(out)

# ---------------- F6: wedge scorecard ----------------
def svg_wedges(wedges, recommended):
    order = sorted(wedges, key=lambda w: (-w['attractiveness'], w['difficulty'])); wnum = {w['name']: i + 1 for i, w in enumerate(order)}
    W, H = 880, 470; x0, y0, pw, ph = 70, 24, W - 70 - 300, H - 24 - 80
    def X(v): return x0 + pw * (v - 0.6) / 4.8
    def Y(v): return y0 + ph - ph * (v - 0.6) / 4.8
    out = [svg_open(W, H, 'Wedge scorecard: attractiveness versus difficulty, shade = platform risk', minw=700)]
    for v in range(1, 6):
        out.append(f'<line x1="{X(v):.1f}" y1="{y0}" x2="{X(v):.1f}" y2="{y0 + ph}" stroke="{HAIR}"/>'); out.append(t(X(v), y0 + ph + 18, str(v), 11, MUTED, 400, 'middle'))
        out.append(f'<line x1="{x0}" y1="{Y(v):.1f}" x2="{x0 + pw}" y2="{Y(v):.1f}" stroke="{HAIR}"/>'); out.append(t(x0 - 10, Y(v) + 4, str(v), 11, MUTED, 400, 'end'))
    out.append(t(x0 + pw / 2, y0 + ph + 38, 'Difficulty to execute (1 easy – 5 hard)', 11.5, MUTED, 600, 'middle'))
    out.append(f'<text transform="translate(18,{y0 + ph/2:.0f}) rotate(-90)" font-size="11.5" fill="{MUTED}" font-weight="600" text-anchor="middle" font-family="inherit">Attractiveness (1–5)</text>')
    for cx, cy, w, ang in place_points(wedges, lambda w: (w['difficulty'], w['attractiveness']), X, Y, jitter=20):
        rec = bool(recommended) and w['name'].lower()[:18] in recommended.lower(); fill = ramp(w['platform_risk'])
        if rec: out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="19" fill="none" stroke="{ACCENT}" stroke-width="2.5"/>')
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="12" fill="{fill}" stroke="{SURFACE}" stroke-width="2"><title>{esc(w["name"])}: attractiveness {w["attractiveness"]}, difficulty {w["difficulty"]}, platform risk {w["platform_risk"]}</title></circle>')
        out.append(num_in(cx, cy, wnum[w['name']], fill, 11))
    lx, ly = x0 + pw + 24, y0 + 14
    out.append(t(lx, ly, 'Wedges', 11, MUTED, 600)); ly += 18
    kl, ly = key_list(lx, ly, [(wnum[w['name']], w['name']) for w in order], width=42); out.append(kl); ly += 10
    out.append(t(lx, ly, 'Shade = platform risk', 11, MUTED, 600)); ly += 20
    for lab, col in (('1–2 low', RAMP[0]), ('3 medium', RAMP[1]), ('4–5 high', RAMP[2])):
        out.append(f'<circle cx="{lx + 8}" cy="{ly - 4}" r="7" fill="{col}"/>'); out.append(t(lx + 22, ly, lab, 11, INK2)); ly += 22
    ly += 6; out.append(f'<circle cx="{lx + 8}" cy="{ly - 4}" r="9" fill="none" stroke="{ACCENT}" stroke-width="2.5"/>'); out.append(t(lx + 22, ly, 'recommended wedge', 11, INK2))
    out.append('</svg>'); return ''.join(out)

# ---------------- assembly ----------------
def main():
    res = json.load(open(os.path.join(HERE, 'result.json')))
    order = ['problems', 'market', 'startups-memory', 'startups-infra', 'incumbents', 'cases', 'gtm']
    secs = OrderedDict((k, res.get(k.replace('-', '_'))) for k in order)
    secs['startups-memory'] = res.get('startups_memory'); secs['startups-infra'] = res.get('startups_infra')
    for g in res.get('gapSections') or []: secs[g['slug']] = g
    problems = (res.get('problems') or {}).get('problems') or []
    startups = ((res.get('startups_memory') or {}).get('startups') or []) + ((res.get('startups_infra') or {}).get('startups') or [])
    # dedupe startups by name
    sd = OrderedDict()
    for s in startups:
        k = s['name'].strip().lower()
        if k not in sd or (s.get('total_funding_usd') or 0) > (sd[k].get('total_funding_usd') or 0): sd[k] = s
    startups = list(sd.values())
    market = res.get('market') or {}; incumbents = res.get('incumbents') or {}; gtm = res.get('gtm') or {}; cases = res.get('cases') or {}
    critic = res.get('critic') or {}

    # sources index from sweeps
    all_src = OrderedDict()
    for f in sorted(glob.glob(os.path.join(HERE, 'sweep', '*.json'))):
        try: data = json.load(open(f))
        except Exception as e: print('skip', f, e); continue
        for s in data.get('sources', []):
            k = norm_url(s.get('url'))
            if k and k not in all_src: all_src[k] = dict(s, modality=os.path.basename(f)[:-5])
    by_type = Counter((s.get('type') or 'other') for s in all_src.values()); total = res.get('totalUniqueSources') or len(all_src)
    type_order = ['news', 'blog', 'paper', 'report', 'docs', 'thread', 'repo', 'talk', 'directory', 'filing', 'other']
    PL = dict(news='news articles', blog='blog posts', paper='papers', report='reports', docs='doc pages', thread='threads', repo='repos', talk='talks', directory='directories', filing='filings', other='other')
    tiles = [f'<div class="tile"><b>{total}</b><span>sources</span></div>'] + [f'<div class="tile"><b>{by_type[tp]}</b><span>{PL[tp]}</span></div>' for tp in type_order if by_type.get(tp)]

    # fragments
    frags = []
    for slug, s in secs.items():
        path = os.path.join(HERE, 'sections', f'{slug}.html')
        if not os.path.exists(path): print('MISSING fragment', path); continue
        frag = clean_fragment(open(path, encoding='utf-8').read())
        inject = ''
        if slug == 'problems' and problems:
            inject = (f'<figure class="breakout"><div class="scroll">{svg_problem_map(problems)}</div><figcaption><span class="swipe">Swipe sideways to see the whole figure. </span><b>Figure 2.</b> The problem map. Right and up is worse; bigger bubbles mean teams will pay to fix it; darker means the model vendors are likely to ship a native fix, which shrinks the opportunity.</figcaption></figure>'
                      f'<figure class="breakout"><div class="scroll">{svg_opportunity_bars(problems)}</div><figcaption><span class="swipe">Swipe sideways to see the whole figure. </span><b>Figure 3.</b> Opportunity ranking. The score rewards frequent, painful, paid-for problems and penalises those the platforms are about to absorb. Scores are judgement calls by the research agents, anchored on the evidence quoted in the text; treat differences of a few points as ties.</figcaption></figure>')
        if slug == 'market':
            vc = market.get('value_chain') or []; rounds = market.get('rounds') or []
            if vc: inject += f'<figure class="breakout"><div class="scroll">{svg_value_chain(vc, startups)}</div><figcaption><span class="swipe">Swipe sideways to see the whole figure. </span><b>Figure 1.</b> The value chain, top to bottom, with the players named in the research; chips carry disclosed total funding where known.</figcaption></figure>'
            ft = svg_funding_timeline(rounds)
            if ft: inject += f'<figure class="breakout"><div class="scroll">{ft}</div><figcaption><span class="swipe">Swipe sideways to see the whole figure. </span><b>Figure 4.</b> Sourced funding rounds, 2024–2026, by category; bubble area is proportional to the amount. Only rounds with a citation are plotted.</figcaption><details><summary>Table view</summary><div class="table-wrap"><table><thead><tr><th>Company</th><th>Round</th><th class="n">Amount</th><th>Date</th><th>Lead</th><th>Category</th><th>Source</th></tr></thead><tbody>' + ''.join(f'<tr><td>{esc(r["company"])}</td><td>{esc(r["round"])}</td><td class="n">{money(r["amount_usd"])}</td><td>{esc(r["date"])}</td><td>{esc(r.get("lead", ""))}</td><td>{esc(LANES[norm_cat(r.get("category"))][0])}</td><td><a href="{esc(r["source_url"])}" target="_blank" rel="noopener">source</a></td></tr>' for r in sorted(rounds, key=lambda r: str(r.get("date")))) + '</tbody></table></div></details></figure>'
        if slug == 'startups-memory' and startups:
            inject = (f'<figure class="breakout"><div class="scroll">{svg_landscape(startups)}</div><figcaption><span class="swipe">Swipe sideways to see the whole figure. </span><b>Figure 5.</b> The startup landscape: rows are product categories, columns the customer each company sells to; chips show disclosed total funding and whether the core is open source. Hover for the product one-liner; click to open the company site.</figcaption>'
                      f'<details><summary>Table view</summary><div class="table-wrap"><table><thead><tr><th>Company</th><th>Category</th><th>Founded</th><th class="n">Funding</th><th>Last round</th><th>Investors</th><th>Customer</th><th>OSS ★</th><th>Pricing</th><th>Funding source</th></tr></thead><tbody>' + ''.join(f'<tr><td><a href="{esc(s["url"])}" target="_blank" rel="noopener">{esc(s["name"])}</a></td><td>{esc(CAT_NAMES.get(s["category"], s["category"]))}</td><td>{s.get("founded") or ""}</td><td class="n">{money(s.get("total_funding_usd"))}</td><td>{esc(s.get("last_round", ""))} {esc(s.get("last_round_date", ""))}</td><td>{esc(", ".join(s.get("investors") or [])[:80])}</td><td>{cust(s.get("target_customer"))}</td><td>{fmt_stars(s["github_stars"]) if s.get("open_source") and s.get("github_stars") else ("yes" if s.get("open_source") else "—")}</td><td>{esc(s.get("pricing_model", ""))}</td><td>{fund_link(s)}</td></tr>' for s in sorted(startups, key=lambda s: -(s.get("total_funding_usd") or 0))) + '</tbody></table></div></details></figure>')
        if slug == 'incumbents' and incumbents.get('moves'):
            it = svg_incumbent_timeline(incumbents['moves'])
            if it: inject = f'<figure class="breakout"><div class="scroll">{it}</div><figcaption><span class="swipe">Swipe sideways to see the whole figure. </span><b>Figure 6.</b> What the platforms shipped, when, and how directly it competes with the startup layer (darker = higher threat).</figcaption></figure>'
        if slug == 'gtm' and gtm.get('wedges'):
            inject = (f'<figure class="breakout"><div class="scroll">{svg_wedges(gtm["wedges"], gtm.get("recommended_wedge", ""))}</div><figcaption><span class="swipe">Swipe sideways to see the whole figure. </span><b>Figure 7.</b> Candidate wedges scored on attractiveness and difficulty; the ring marks the recommended one.</figcaption></figure>'
                      + (f'<figure class="rail"><div class="scroll">{svg_rail(gtm["first_90_days"], ACCENT, "first 90 days")}</div><figcaption><span class="swipe">Swipe sideways for all steps. </span><b>Figure 8.</b> The first 90 days for the recommended wedge.</figcaption></figure>' if gtm.get('first_90_days') else ''))
        frag = re.sub(r'(<h3>)', inject + r'\1', frag, count=1) if inject else frag
        frags.append(frag)

    # executive summary
    top5 = sorted(problems, key=lambda p: -score(p))[:5]
    cards = ''.join(f'<div class="card"><b><a href="#{esc(k)}">{esc(s.get("title", k))}</a></b><p>{esc(s.get("takeaway", ""))}</p></div>' for k, s in secs.items() if s)
    top_html = ''.join(f'<li><b>{esc(p["name"])}</b> — felt by {esc(p["who"])}; score {score(p):g}</li>' for p in top5)
    wedge_html = esc(gtm.get('recommended_wedge', '')) if gtm else ''
    nav = ['<li><a href="#summary">Summary</a></li>'] + [f'<li><a href="#{esc(k)}">{esc(short)}</a></li>' for k, short in [('problems', 'Problems'), ('market', 'Market & money'), ('startups-memory', 'Memory startups'), ('startups-infra', 'Adjacent startups'), ('incumbents', 'Incumbents'), ('cases', 'Case studies'), ('gtm', 'Playbook')] if secs.get(k)] + [f'<li><a href="#{esc(k)}">{esc(v.get("title", k)[:28])}</a></li>' for k, v in secs.items() if k.startswith('addendum') and v] + ['<li><a href="#method">Method &amp; sources</a></li>']

    idx = []
    for tp in type_order:
        items = [s for s in all_src.values() if (s.get('type') or 'other') == tp]
        if not items: continue
        items.sort(key=lambda s: (-(s.get('year') or 0), (s.get('title') or '').lower()))
        lis = ''.join(f'<li><a href="{esc(s.get("url"))}" target="_blank" rel="noopener">{esc(s.get("title"))}</a> — {esc(s.get("venue_or_author"))}, {esc(s.get("year"))}' + (f' <span class="tags">{esc(", ".join((s.get("topics") or [])[:3]))}</span>' if s.get('topics') else '') + '</li>' for s in items)
        idx.append(f'<details><summary>{PL[tp].capitalize()} ({len(items)})</summary><ol class="sources">{lis}</ol></details>')
    stats = res.get('sweepStats') or {}
    def clean_note(n): return re.sub(r'\s*/Users/\S+', ' (local file)', str(n or ''))
    stats_lis = ''.join(f'<li><b>{esc(k)}</b>: {v.get("unique_kept", v.get("returned", 0))} unique sources' + (f' — <span class="muted">{esc(clean_note(v.get("note")))[:420]}</span>' if v.get('note') else '') + '</li>' for k, v in stats.items())
    fixes = ''.join(f'<li><b>{esc(f["section"])}</b>: {esc(f["issue"])} → {esc(f["fix"])}</li>' for f in (critic.get('fixes') or []))

    body = f'''
{{NAV}}<header class="masthead"><div class="wrap">
  <p class="eyebrow">Market research · {TODAY} · {total} sources · companion to the <a href="report.html">Context Window Playbook</a></p>
  <h1>Context Market Map</h1>
  <p class="dek">Who is building the memory and context layer for LLM applications, what still breaks for the teams using it, which of those problems are worth a startup's time, and how a new entrant should pick its wedge — with the money, the incumbents and the reference companies laid out.</p>
  <div class="tiles">{''.join(tiles)}</div>
</div></header>
<nav class="toc"><div class="wide"><ul>{''.join(nav)}</ul></div></nav>
<main>
<section class="part wide" id="summary">
  <h2>Summary</h2>
  <div class="cards">{cards}</div>
  <div class="two">
    <div><h3>Problems most worth solving</h3><ol class="top">{top_html}</ol></div>
    <div><h3>Recommended wedge</h3><p class="callout">{wedge_html}</p></div>
  </div>
</section>
{''.join(f'<div class="wrap">{f}</div>' for f in frags)}
<section class="part wrap" id="method">
  <h2>Method &amp; sources</h2>
  <p>Seven parallel research sweeps ran on {TODAY}, each restricted to one kind of evidence and capped at roughly 14 searches / 8 fetches / 15 minutes: practitioner pain points, open research problems, memory-layer startups, adjacent context-infrastructure startups, incumbent platform moves, market sizing and investor theses, and buyer / go-to-market evidence. Six synthesis agents then wrote the sections from that evidence, verifying numbers against primary sources (≤ 10 fetches each), a playbook agent built the wedge analysis on top of them, and a critic checked for unsourced figures, contradictions and missing companies before one bounded gap-fill round.</p>
  <p><b>Scores are judgement, not measurement.</b> Frequency, severity, willingness-to-pay, platform-risk, attractiveness and difficulty are 1–5 ratings assigned by the research agents from the quoted evidence; they are useful for ranking and arguing, not as precise quantities. Funding figures are only shown when a source could be cited; "undisclosed" means none was found within the caps. Web search was US-only and never surfaced Reddit. <b>Coverage limitation:</b> a session-wide search quota was exhausted partway through the sweeps, so four to six planned queries per sweep never ran (notably coding-agent context products, agent frameworks, some YC-batch memory startups and several 2026 rounds); the per-sweep notes below list what was not covered, and the two addenda were researched to close the most important gaps.</p>
  <ul>{stats_lis}</ul>
  <p><b>Critic verdict:</b> <i>{esc(critic.get("verdict", "n/a"))}</i>. {esc(clean_note(critic.get("notes", "")))}</p>
  {('<p><b>Corrections applied after the critic pass:</b></p><ul>' + fixes + '</ul>') if fixes else ''}
  <h3>Source index</h3>
  <p class="muted">All {len(all_src)} unique sources gathered by the sweeps, grouped by type, newest first.</p>
  {''.join(idx)}
</section>
</main>
<footer class="wrap"><p class="muted">Compiled {TODAY} by Claude Code (multi-agent research workflow). Verify figures against the linked primary sources before relying on them; funding and valuation data change quickly.</p></footer>
'''
    css = open(os.path.join(os.path.dirname(SRC), 'style.css'), encoding='utf-8').read() + '''
section.msection{padding:44px 0;border-bottom:1px solid var(--hair);scroll-margin-top:64px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;margin:8px 0 24px}
.card{background:var(--surface);border:1px solid var(--hair);border-radius:8px;padding:14px 16px;font-size:15px}
.card b{display:block;font-size:15px;margin-bottom:6px;font-family:"Bricolage Grotesque",system-ui,sans-serif}
.card p{margin:0;color:var(--ink2)}
.two{display:grid;grid-template-columns:1fr 1fr;gap:28px}
@media (max-width:800px){.two{grid-template-columns:1fr}}
ol.top li{margin:0 0 8px}
.callout{background:var(--surface);border-left:4px solid var(--accent);padding:12px 16px;border-radius:0 6px 6px 0;font-size:17px}
.masthead a{color:var(--accent)}
#method li{overflow-wrap:anywhere}
.wrap figure.breakout{width:min(1160px,calc(100vw - 40px));max-width:none;position:relative;left:50%;transform:translateX(-50%)}
'''
    fonts = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=Source+Sans+3:ital,wght@0,400;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;600&display=swap">'
    title = '<title>Context Market Map</title>'
    art = f'{title}\n{fonts}\n<style>{css}</style>\n' + body.replace('{NAV}', series_nav('market-report.html', 'artifact'))
    fbody = body.replace('{NAV}', series_nav('market-report.html', 'file'))
    full = f'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n{title}\n{fonts}\n<style>{css}</style>\n</head>\n<body>\n{fbody}\n</body>\n</html>\n'
    open(OUT_FULL, 'w', encoding='utf-8').write(full); open(OUT_ART, 'w', encoding='utf-8').write(art)
    print(f'wrote {OUT_FULL} ({len(full)//1024} KB); sections={len(frags)} startups={len(startups)} problems={len(problems)} rounds={len(market.get("rounds") or [])} moves={len(incumbents.get("moves") or [])} wedges={len(gtm.get("wedges") or [])} sources={len(all_src)}')

if __name__ == '__main__':
    main()
