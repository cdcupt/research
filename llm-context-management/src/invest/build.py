#!/usr/bin/env python3
"""Assemble the AI Investment Outlook report. Inputs (this dir): result.json, sections/*.html, sweep/*.json. Reuses ../build.py helpers."""
import json, re, os, sys, glob
from collections import OrderedDict, Counter
SRC = os.path.dirname(os.path.abspath(__file__))
HERE = os.environ.get('INVEST_DIR', SRC)
sys.path.insert(0, os.path.dirname(SRC))
from build import esc, norm_url, clean_fragment, INK, INK2, MUTED, HAIR, SURFACE, BG, ACCENT  # noqa: E402
TODAY = '2026-08-24'
OUT_FULL = os.path.join(HERE, 'investment-report.html'); OUT_ART = os.path.join(HERE, 'investment-report.artifact.html')
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
    board = ''
    for s in sorted(pub.get('stocks') or [], key=lambda s: s['ticker']):
        board += (f'<div class="stock"><div class="trow"><b>{esc(s["ticker"])}</b><span class="key">{esc(s["key_number"])}</span></div>'
                  f'<div class="nm">{esc(s["name"])}</div><p>{esc(s["situation"])}</p>'
                  f'<div class="asof">as of {esc(s["as_of"])} · <a href="{esc(s["source_url"])}" target="_blank" rel="noopener">source</a></div></div>')
    fig_board = f'<h3>The board: where the AI trade stands</h3><div class="stockboard">{board}</div>' if board else ''

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
<header class="masthead"><div class="wrap">
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
    art = f'{title}\n{fonts}\n<style>{css}</style>\n{body}'
    full = f'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n{title}\n{fonts}\n<style>{css}</style>\n</head>\n<body>\n{body}\n</body>\n</html>\n'
    open(OUT_FULL, 'w', encoding='utf-8').write(full); open(OUT_ART, 'w', encoding='utf-8').write(art)
    print(f'wrote {OUT_FULL} ({len(full)//1024} KB); sections={len(frags)} stocks={len(pub.get("stocks") or [])} expectations={len(exps)} trends={len(prv.get("trends") or [])} compare={len(uc.get("compare") or [])} sources={len(all_src)}')

if __name__ == '__main__':
    main()
