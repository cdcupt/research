#!/usr/bin/env python3
"""Assemble the AI Investment Outlook report. Inputs (this dir): result.json, sections/*.html, sweep/*.json. Reuses ../build.py helpers."""
import json, re, os, sys, glob
from collections import OrderedDict, Counter
SRC = os.path.dirname(os.path.abspath(__file__))
HERE = os.environ.get('INVEST_DIR', SRC)
sys.path.insert(0, os.path.dirname(SRC))
from build import series_nav, esc, norm_url, clean_fragment, INK, INK2, MUTED, HAIR, SURFACE, BG, ACCENT, t, tlines, wrap, svg_open  # noqa: E402
TODAY = '2026-08-24'
OUT_FULL = os.path.join(HERE, 'investment-report.html'); OUT_ART = os.path.join(HERE, 'investment-report.artifact.html')
UP, UP_TXT, DOWN = '#0ca30c', '#006300', '#d03b3b'
PANEL_COLORS = ['#2a78d6', '#eb6834', '#4a3aa7', '#1baf7a']  # validated categorical set
ALIAS = {'MINIMAX-W (HK)': '0100.HK', 'MINIMAX-W': '0100.HK', 'MINIMAX': '0100.HK'}
def load_prices():
    fp = os.path.join(HERE, 'prices.json')
    if not os.path.exists(fp): fp = os.path.join(SRC, 'prices.json')
    return json.load(open(fp)) if os.path.exists(fp) else None
def series_for(prices, ticker):
    if not prices: return None
    k = ALIAS.get(ticker.strip().upper(), ticker.strip().upper())
    return prices['series'].get(k)
def sparkline(pts, w=150, h=36):
    vals = [v for _, v in pts]
    lo, hi = min(vals), max(vals); rng = (hi - lo) or 1
    xs = [4 + (w - 8) * i / max(len(vals) - 1, 1) for i in range(len(vals))]
    ys = [4 + (h - 8) * (1 - (v - lo) / rng) for v in vals]
    chg = (vals[-1] / vals[0] - 1) * 100
    col = UP if chg >= 0 else DOWN
    d = 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in zip(xs, ys))
    return (f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="price sparkline">'
            f'<path d="{d}" fill="none" stroke="{col}" stroke-width="1.8"/>'
            f'<circle cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="2.6" fill="{col}"/></svg>'), chg
def spread(vals, gap):
    idx = sorted(range(len(vals)), key=lambda i: vals[i]); out = list(vals)
    for a, b in zip(idx, idx[1:]):
        if out[b] - out[a] < gap: out[b] = out[a] + gap
    return out
import datetime as _dt
def _ord(ds): y, m, d = (list(map(int, ds.split('-'))) + [1, 1])[:3]; return _dt.date(y, m, d).toordinal()
def svg_indexed_panels(prices):
    PANELS = [('Hyperscalers', ['MSFT', 'GOOGL', 'META', 'AMZN'], 'lin'), ('Semis & AI infrastructure', ['NVDA', 'SMCI', 'CRWV'], 'lin'),
              ('Software incumbents', ['MDB', 'SNOW', 'DDOG'], 'lin'), ('China: platforms & 2026 listings', ['BABA', '0700.HK', '688256.SS', '2513.HK'], 'log')]
    PW, PH, GX, GY, W = 528, 250, 40, 56, 1230
    H = GY + 2 * (PH + 64)
    import math as _mm
    out = [svg_open(W, H, 'Indexed share-price performance 2026 year-to-date, four panels', minw=1000)]
    for pi, (title, tickers, scale) in enumerate(PANELS):
        px = 12 + (pi % 2) * (PW + 90); py = 34 + (pi // 2) * (PH + 64)
        out.append(t(px + 4, py - 8, title.upper(), 11.5, MUTED, 700, extra='letter-spacing=".07em"'))
        sers = [(tk, series_for(prices, tk)) for tk in tickers]; sers = [(tk, s_) for tk, s_ in sers if s_ and len(s_['points']) > 5]
        if not sers: continue
        allx = [_ord(p[0]) for tk, s_ in sers for p in s_['points']]; x0d, x1d = min(allx), max(allx)
        def IX(o): return px + 44 + (PW - 52) * (o - x0d) / max(x1d - x0d, 1)
        idxd = {}
        for tk, s_ in sers:
            base = s_['points'][0][1]; idxd[tk] = [(_ord(d_), v / base * 100) for d_, v in s_['points']]
        vals = [v for pts in idxd.values() for _, v in pts]; lo, hi = min(vals), max(vals)
        if scale == 'log':
            L0, L1 = _mm.log10(lo), _mm.log10(hi)
            def IY(v): return py + PH - (PH - 8) * (_mm.log10(v) - L0) / max(L1 - L0, 0.01)
            ticks = [x for x in [50, 100, 200, 400, 800, 1600] if lo * 0.9 <= x <= hi * 1.1]
        else:
            pad = (hi - lo) * 0.06 or 1; lo -= pad; hi += pad
            def IY(v): return py + PH - (PH - 8) * (v - lo) / (hi - lo)
            step = max(round((hi - lo) / 4 / 10) * 10, 10); ticks = [x for x in range(int(lo // step * step), int(hi) + step, step) if lo <= x <= hi]
        for tv in ticks:
            out.append(f'<line x1="{px + 44}" y1="{IY(tv):.1f}" x2="{px + PW - 8}" y2="{IY(tv):.1f}" stroke="{HAIR}"/>'); out.append(t(px + 40, IY(tv) + 3.5, str(tv), 10, MUTED, 400, 'end'))
        base_y = IY(100)
        out.append(f'<line x1="{px + 44}" y1="{base_y:.1f}" x2="{px + PW - 8}" y2="{base_y:.1f}" stroke="#c3c2b7" stroke-width="1.2"/>')
        for mo in range(1, 9): 
            o = _dt.date(2026, mo, 1).toordinal()
            if x0d <= o <= x1d: out.append(t(IX(o), py + PH + 14, f'{mo}月'[:0] + ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug'][mo-1], 9.5, MUTED, 400, 'middle'))
        ends = []
        for ci, (tk, s_) in enumerate(sers):
            col = PANEL_COLORS[ci % 4]; pts = idxd[tk]
            d = 'M' + ' L'.join(f'{IX(o):.1f},{IY(v):.1f}' for o, v in pts)
            out.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2"><title>{esc(s_["name"])} indexed to 100 at first 2026 close</title></path>')
            ends.append((tk, s_, col, pts[-1][1]))
        eys = spread([IY(v) for tk, s_, col, v in ends], 13)
        for (tk, s_, col, v), ey in zip(ends, eys):
            out.append(f'<circle cx="{IX(x1d):.1f}" cy="{IY(v):.1f}" r="3" fill="{col}"/>')
            out.append(t(px + PW + 2, ey + 3.5, f'{tk} {v - 100:+.0f}%', 10.5, col, 700))
    out.append('</svg>'); return ''.join(out)
def svg_valuations(V):
    import math as _mm
    W = 1120; px, py, PW, PH = 60, 40, W - 260, 380
    x0d, x1d = _dt.date(2024, 1, 1).toordinal(), _dt.date(2026, 11, 1).toordinal()
    def X(o): return px + PW * (o - x0d) / (x1d - x0d)
    def Y(v): return py + PH - PH * (_mm.log10(v) - 0) / (_mm.log10(2000) - 0)
    out = [svg_open(W, py + PH + 70, 'Reported valuations of frontier AI labs, 2024-2026, log scale, US versus China', minw=900)]
    for tv, lab in [(1, '$1B'), (10, '$10B'), (100, '$100B'), (1000, '$1T')]:
        out.append(f'<line x1="{px}" y1="{Y(tv):.1f}" x2="{px + PW}" y2="{Y(tv):.1f}" stroke="{HAIR}"/>'); out.append(t(px - 6, Y(tv) + 3.5, lab, 10.5, MUTED, 400, 'end'))
    for yr in (2024, 2025, 2026):
        o = _dt.date(yr, 1, 1).toordinal(); out.append(f'<line x1="{X(o):.1f}" y1="{py}" x2="{X(o):.1f}" y2="{py + PH}" stroke="{HAIR}"/>'); out.append(t(X(o), py + PH + 16, str(yr), 11, MUTED, 400, 'middle'))
    SIDE = {'US': '#2a78d6', 'China': '#eb6834'}
    ends = [(c, c['points'][-1][1]) for c in V['companies']]
    eys = spread([Y(v) for c, v in ends], 15)
    for (c, endv), ey in zip(ends, eys):
        col = SIDE[c['side']]; pts = [(_ord(d_ + '-01' if len(d_) == 7 else d_), v, lab) for d_, v, lab in c['points']]
        if len(pts) > 1:
            d = 'M' + ' L'.join(f'{X(o):.1f},{Y(v):.1f}' for o, v, _ in pts)
            out.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2" stroke-opacity="0.75"/>')
        for o, v, lab in pts:
            out.append(f'<circle cx="{X(o):.1f}" cy="{Y(v):.1f}" r="4.5" fill="{col}" stroke="{SURFACE}" stroke-width="1.5"><title>{esc(c["name"])}: ${v}B — {esc(lab)}</title></circle>')
        out.append(t(px + PW + 10, ey + 3.5, f"{c['name']} ${endv:g}B", 11.5, col, 700))
    ly = py + PH + 44
    out.append(f'<rect x="{px}" y="{ly - 10}" width="12" height="12" rx="2" fill="{SIDE["US"]}"/>' + t(px + 17, ly, 'United States', 11.5, INK2))
    out.append(f'<rect x="{px + 130}" y="{ly - 10}" width="12" height="12" rx="2" fill="{SIDE["China"]}"/>' + t(px + 147, ly, 'China', 11.5, INK2))
    out.append(t(px + 230, ly, 'hover a point for the round and sourcing label; all figures are reported, several per headline', 11, MUTED))
    out.append('</svg>'); return ''.join(out)

STANCE = OrderedDict([('bull', ('Bulls', '#1baf7a')), ('mixed', ('Mixed', '#5b6472')), ('cautious', ('Cautious', '#eb6834')), ('bear', ('Bears', '#d03b3b'))])

def main():
    res = json.load(open(os.path.join(HERE, 'result.json')))
    pub = res.get('public') or {}; prv = res.get('private') or {}; uc = res.get('usvschina') or {}
    secs = OrderedDict([('public-markets', pub), ('private-markets', prv), ('us-vs-china', uc)])
    for g in res.get('gapSections') or []:
        if os.path.exists(os.path.join(HERE, 'sections', g['slug'] + '.html')): secs[g['slug']] = g
    critic = res.get('critic') or {}
    all_src = OrderedDict()
    for f in sorted(glob.glob(os.path.join(HERE, 'sweep', '*.json'))):
        try: data = json.load(open(f))
        except Exception as e: print('skip', f, e); continue
        for s in data.get('sources', []):
            k = norm_url(s.get('url'))
            if k and k not in all_src: all_src[k] = dict(s, modality=os.path.basename(f)[:-5])
    by_type = Counter((s.get('type') or 'other') for s in all_src.values()); zh = sum(1 for s in all_src.values() if s.get('lang') == 'zh')
    PL = dict(news='news articles', blog='blog posts', paper='papers', report='reports', docs='doc pages', thread='threads', repo='repos', filing='filings', talk='talks', other='other')
    type_order = list(PL)
    tiles = [f'<div class="tile"><b>{len(all_src)}</b><span>sources</span></div>', f'<div class="tile"><b>{zh}</b><span>Chinese-language</span></div>'] + \
            [f'<div class="tile"><b>{by_type[tp]}</b><span>{PL[tp]}</span></div>' for tp in type_order if by_type.get(tp)]

    # --- stock board ---
    prices = load_prices()
    board = ''
    for s in sorted(pub.get('stocks') or [], key=lambda s: s['ticker']):
        ser = series_for(prices, s['ticker']); spark = ''
        if ser:
            svg_, chg = sparkline(ser['points'])
            pcol = UP_TXT if chg >= 0 else DOWN
            spark = (f'<div class="sparkrow">{svg_}<span class="pct" style="color:{pcol}">{chg:+.0f}%<em>2026 YTD ({esc(ser["currency"])})</em></span></div>')
        board += (f'<div class="stock"><div class="trow"><b>{esc(s["ticker"])}</b><span class="key">{esc(s["key_number"])}</span></div>'
                  f'<div class="nm">{esc(s["name"])}</div>{spark}<p>{esc(s["situation"])}</p>'
                  f'<div class="asof">as of {esc(s["as_of"])} · <a href="{esc(s["source_url"])}" target="_blank" rel="noopener">source</a></div></div>')
    fig_board = f'<h3>The board: where the AI trade stands</h3><div class="stockboard">{board}</div>' if board else ''
    if prices:
        fig_board += (f'<figure class="breakout"><div class="scroll">{svg_indexed_panels(prices)}</div><figcaption><span class="swipe">Swipe sideways to see the whole figure. </span><b>Figure A.</b> 2026 share-price trends, indexed to 100 at each name\'s first close of the year (HK listings from their debut). Daily closes from Yahoo Finance (US) and Tencent (HK/A-shares), as of {esc(prices.get("fetched", ""))}; the China panel is log-scaled because Cambricon and Zhipu moved in multiples, not percent.</figcaption></figure>')
    vals_p = os.path.join(HERE, 'valuations.json'); vals_p = vals_p if os.path.exists(vals_p) else os.path.join(SRC, 'valuations.json')
    if os.path.exists(vals_p):
        V = json.load(open(vals_p))
        fig_board += (f'<figure class="breakout"><div class="scroll">{svg_valuations(V)}</div><figcaption><span class="swipe">Swipe sideways to see the whole figure. </span><b>Figure B.</b> Private-lab valuation trajectories, 2024-2026, on a log scale — the startups\' equivalent of a stock chart. Every point is a reported figure from the sources in this report; hover for the round and label. {esc(V.get("note", ""))}</figcaption></figure>')

    # --- expectations board ---
    exps = prv.get('expectations') or []
    cols = ''
    for k, (name, col) in STANCE.items():
        items = [e for e in exps if e.get('stance') == k]
        if not items: continue
        lis = ''.join(f'<li><b>{esc(e["investor"])}</b> <span class="asof">({esc(e["date"])})</span><br>{esc(e["expectation"])} <a href="{esc(e["source_url"])}" target="_blank" rel="noopener">→</a></li>' for e in items)
        cols += f'<div class="stancecol"><h4><i class="dot" style="background:{col}"></i>{name} ({len(items)})</h4><ul>{lis}</ul></div>'
    fig_exp = f'<h3>What named investors expect</h3><div class="stancegrid">{cols}</div>' if cols else ''

    # --- trend cards ---
    cards = ''.join(f'<div class="metric"><b>{esc(t["value"])}</b><span>{esc(t["metric"])}</span><div class="asof">{esc(t["period"])} · <a href="{esc(t["source_url"])}" target="_blank" rel="noopener">source</a></div></div>' for t in (prv.get('trends') or []))
    fig_tr = f'<h3>The numbers that carry the argument</h3><div class="metrics">{cards}</div>' if cards else ''

    # --- US vs China matrix ---
    rows = ''.join(f'<tr><td class="dim">{esc(c["dimension"])}</td><td>{esc(c["us"])}</td><td>{esc(c["china"])}</td><td><a href="{esc(c["source_url"])}" target="_blank" rel="noopener">src</a></td></tr>' for c in (uc.get('compare') or []))
    fig_cmp = f'<h3>Side by side</h3><div class="table-wrap"><table class="cmp"><thead><tr><th></th><th>United States</th><th>China</th><th></th></tr></thead><tbody>{rows}</tbody></table></div>' if rows else ''

    frags = []
    for slug, s in secs.items():
        path = os.path.join(HERE, 'sections', f'{slug}.html')
        if not os.path.exists(path): print('MISSING', path); continue
        frag = clean_fragment(open(path, encoding='utf-8').read())
        inj = {'public-markets': fig_board, 'private-markets': fig_exp + fig_tr, 'us-vs-china': fig_cmp}.get(slug, '')
        if inj: frag = re.sub(r'(<h3>)', inj + r'\1', frag, count=1)
        frags.append(frag)

    cards_html = ''.join(f'<div class="card"><b><a href="#{esc(k)}">{esc(s.get("title", k))}</a></b><p>{esc(s.get("takeaway", ""))}</p></div>' for k, s in secs.items() if s)
    SHORTNAV = {'public-markets': 'Stocks', 'private-markets': 'Private markets', 'us-vs-china': 'US vs China'}
    nav = ['<li><a href="#summary">Summary</a></li>'] + [f'<li><a href="#{esc(k)}">{esc(SHORTNAV.get(k, (s.get("title") or k)[:30]))}</a></li>' for k, s in secs.items() if s] + ['<li><a href="#method">Method &amp; sources</a></li>']
    idx = []
    for tp in type_order:
        items = [s for s in all_src.values() if (s.get('type') or 'other') == tp]
        if not items: continue
        items.sort(key=lambda s: (-(s.get('year') or 0), (s.get('title') or '').lower()))
        lis = ''.join(f'<li><a href="{esc(s.get("url"))}" target="_blank" rel="noopener">{esc(s.get("title"))}</a> — {esc(s.get("venue_or_author"))}, {esc(s.get("year"))}{" · 中文" if s.get("lang") == "zh" else ""}</li>' for s in items)
        idx.append(f'<details><summary>{PL[tp].capitalize()} ({len(items)})</summary><ol class="sources">{lis}</ol></details>')
    stats = res.get('stats') or {}
    def clean_note(n): return re.sub(r'\s*/Users/\S+', ' (local file)', str(n or ''))
    stats_lis = ''.join(f'<li><b>{esc(k)}</b>: {v.get("unique_kept", v.get("returned", 0))} unique sources' + (f' — <span class="muted">{esc(clean_note(v.get("note")))[:400]}</span>' if v.get('note') else '') + '</li>' for k, v in stats.items())
    sent = esc(pub.get('sentiment_summary', ''))

    body = f'''
{{NAV}}<header class="masthead"><div class="wrap">
  <p class="eyebrow">Market research · {TODAY} · {len(all_src)} sources · companion to the <a href="report.html">Context Window Playbook</a> and the <a href="market-report.html">Context Market Map</a></p>
  <h1>AI Investment Outlook</h1>
  <p class="dek">Where investors stand on AI in late August 2026 — the public-market situation and the bubble debate, private funding trends and what named investors expect next, and the US-versus-China competitive picture — with every number dated and sourced.</p>
  <div class="tiles">{''.join(tiles)}</div>
</div></header>
<nav class="toc"><div class="wide"><ul>{''.join(nav)}</ul></div></nav>
<main>
<section class="part wide" id="summary">
  <h2>Summary</h2>
  <div class="cards">{cards_html}</div>
  {f'<p class="callout">{sent}</p>' if sent else ''}
</section>
{''.join(f'<div class="wrap">{f}</div>' for f in frags)}
<section class="part wrap" id="method">
  <h2>Method &amp; sources</h2>
  <p>Researched on {TODAY} by a bounded multi-agent workflow: five source sweeps (US public markets, private markets and investor statements, China investment flows, the Chinese context-management stack, the Chinese context market), three section writers with verification fetches, an accuracy critic, and up to two gap-fill rounds. This session had no web-search quota left, so discovery ran through Google News RSS (English and Chinese), Mojeek and DuckDuckGo with direct page fetches — news coverage is therefore strong while general-web and forum coverage is thinner than usual; facts attributed to a headline rather than a fetched article are marked in the text.</p>
  <p><b>Not investment advice.</b> Figures are journalists' and analysts' numbers as of their stated dates; valuations of private companies are often "reportedly"; verify against primary sources before acting.</p>
  <ul>{stats_lis}</ul>
  <p><b>Critic verdict:</b> <i>{esc(critic.get("verdict", "n/a"))}</i>. {esc(clean_note(critic.get("notes", "")))}</p>
  <h3>Source index</h3>
  {''.join(idx)}
</section>
</main>
<footer class="wrap"><p class="muted">Compiled {TODAY} by Claude Code (multi-agent research workflow). Market data changes daily; treat this as a dated snapshot.</p></footer>
'''
    css = open(os.path.join(os.path.dirname(SRC), 'style.css'), encoding='utf-8').read() + '''
section.msection{padding:44px 0;border-bottom:1px solid var(--hair);scroll-margin-top:64px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;margin:8px 0 20px}
.card{background:var(--surface);border:1px solid var(--hair);border-radius:8px;padding:14px 16px;font-size:15px}
.card b{display:block;font-size:15px;margin-bottom:6px;font-family:"Bricolage Grotesque",system-ui,sans-serif}
.card p{margin:0;color:var(--ink2)}
.callout{background:var(--surface);border-left:4px solid var(--accent);padding:12px 16px;border-radius:0 6px 6px 0;font-size:17px}
.stockboard{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px;margin:12px 0 20px}
.stock{background:var(--surface);border:1px solid var(--hair);border-radius:8px;padding:12px 14px;font-size:14px}
.stock .trow{display:flex;justify-content:space-between;align-items:baseline}
.stock b{font-size:18px}
.stock .key{color:var(--accent);font-weight:700}
.stock .nm{color:var(--muted);font-size:12.5px;margin:2px 0 6px}
.stock p{margin:0 0 8px;color:var(--ink2)}
.sparkrow{display:flex;align-items:center;gap:10px;margin:2px 0 8px}
.sparkrow .pct{font-weight:700;font-size:15px}
.sparkrow .pct em{display:block;font-style:normal;font-weight:400;font-size:10.5px;color:var(--muted)}
.asof{font-size:11.5px;color:var(--muted)}
.stancegrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px;margin:12px 0 20px}
.stancecol h4{font-size:15px;margin:0 0 8px;display:flex;align-items:center;gap:7px;font-family:"Bricolage Grotesque",system-ui,sans-serif}
.stancecol ul{list-style:none;padding:0;margin:0}
.stancecol li{background:var(--surface);border:1px solid var(--hair);border-radius:6px;padding:9px 11px;margin:0 0 8px;font-size:13.5px}
.metrics{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px;margin:12px 0 20px}
.metric{background:var(--bg);border:1px solid var(--hair);border-radius:6px;padding:12px 14px}
.metric b{display:block;font-size:22px;line-height:1.15}
.metric span{font-size:13px;color:var(--ink2)}
table.cmp td.dim{font-weight:700;min-width:130px}
table.cmp td{vertical-align:top}
.masthead a{color:var(--accent)}
#method li{overflow-wrap:anywhere}
'''
    fonts = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=Source+Sans+3:ital,wght@0,400;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;600&display=swap">'
    title = '<title>AI Investment Outlook</title>'
    art = f'{title}\n{fonts}\n<style>{css}</style>\n' + body.replace('{NAV}', series_nav('investment-report.html', 'artifact'))
    fbody = body.replace('{NAV}', series_nav('investment-report.html', 'file'))
    full = f'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n{title}\n{fonts}\n<style>{css}</style>\n</head>\n<body>\n{fbody}\n</body>\n</html>\n'
    open(OUT_FULL, 'w', encoding='utf-8').write(full); open(OUT_ART, 'w', encoding='utf-8').write(art)
    print(f'wrote {OUT_FULL} ({len(full)//1024} KB); sections={len(frags)} stocks={len(pub.get("stocks") or [])} expectations={len(exps)} trends={len(prv.get("trends") or [])} compare={len(uc.get("compare") or [])} sources={len(all_src)}')

if __name__ == '__main__':
    main()
