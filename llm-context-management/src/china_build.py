#!/usr/bin/env python3
"""Build the standalone China Context Brief from the china data."""
import json, re, os, sys, glob
from collections import OrderedDict, Counter
SRC = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(SRC)); sys.path.insert(0, SRC)
import build as base
from build import esc, clean_fragment, series_nav, svg_cn_stack
CN = os.path.join(SRC, 'china')

def main():
    cn = json.load(open(os.path.join(CN, 'result.json')))
    stack = cn.get('china_stack') or {}; market = cn.get('china_market') or {}
    frag_stack = clean_fragment(open(os.path.join(CN, 'sections', 'china-stack.html'), encoding='utf-8').read())
    frag_stack = frag_stack.replace('<span class="num">CN</span> ', '')
    if stack.get('players'):
        figc = f'<figure class="breakout"><div class="scroll">{svg_cn_stack(stack["players"])}</div><figcaption><span class="swipe">Swipe sideways to see the whole figure. </span><b>Figure 1.</b> The Chinese context-management stack by layer; a filled dot means the weights are open. Hover a chip for the contribution.</figcaption></figure>'
        frag_stack = re.sub(r'(<h3>)', figc + r'\1', frag_stack, count=1)
    frags = [frag_stack, clean_fragment(open(os.path.join(CN, 'sections', 'china-market.html'), encoding='utf-8').read())]
    nav_items = ['<li><a href="#china-stack">The stack</a></li>', '<li><a href="#china-market">The market</a></li>']
    for ap in sorted(glob.glob(os.path.join(CN, 'sections', 'addendum-*.html'))):
        t = clean_fragment(open(ap, encoding='utf-8').read()); frags.append(t)
        m = re.search(r'id="([^"]+)"', t); h = re.search(r'<h2>(.*?)</h2>', t, re.S)
        name = re.sub(r'<[^>]+>', '', h.group(1)).strip() if h else 'Addendum'
        name = re.sub(r'^Addendum:\s*', '', name)[:30]
        if m: nav_items.append(f'<li><a href="#{m.group(1)}">{esc(name)}</a></li>')
    nav_items.append('<li><a href="#method">Method &amp; sources</a></li>')
    all_src = OrderedDict()
    for f in sorted(glob.glob(os.path.join(CN, 'sweep', '*.json'))):
        d = json.load(open(f))
        for s_ in d.get('sources', []):
            k = base.norm_url(s_.get('url'))
            if k and k not in all_src: all_src[k] = dict(s_, modality=os.path.basename(f)[:-5])
    zh = sum(1 for s_ in all_src.values() if s_.get('lang') == 'zh')
    by_type = Counter((s_.get('type') or 'other') for s_ in all_src.values())
    PL = dict(news='news articles', blog='blog posts', paper='papers', docs='doc pages', repo='repos', thread='threads', report='reports', talk='talks', other='other')
    tiles = [f'<div class="tile"><b>{len(all_src)}</b><span>sources</span></div>', f'<div class="tile"><b>{zh}</b><span>Chinese-language</span></div>'] + [f'<div class="tile"><b>{by_type[tp]}</b><span>{PL[tp]}</span></div>' for tp in PL if by_type.get(tp)]
    idx = []
    for tp in PL:
        items = sorted([s_ for s_ in all_src.values() if (s_.get('type') or 'other') == tp], key=lambda s_: (-(s_.get('year') or 0), (s_.get('title') or '').lower()))
        if not items: continue
        lis = ''.join(f'<li><a href="{esc(s_.get("url"))}" target="_blank" rel="noopener">{esc(s_.get("title"))}</a> — {esc(s_.get("venue_or_author"))}, {esc(s_.get("year"))}{" · 中文" if s_.get("lang") == "zh" else ""}</li>' for s_ in items)
        idx.append(f'<details><summary>{PL[tp].capitalize()} ({len(items)})</summary><ol class="sources">{lis}</ol></details>')
    def clean_note(n): return re.sub(r'\s*/Users/\S+', ' (local file)', str(n or ''))
    notes = ''.join(f'<li><b>{esc(os.path.basename(f)[:-5])}</b> — <span class="muted">{esc(clean_note(json.load(open(f)).get("notes")))[:380]}</span></li>' for f in sorted(glob.glob(os.path.join(CN, 'sweep', '*.json'))))
    body = f'''
{{NAV}}<header class="masthead"><div class="wrap">
  <p class="eyebrow">Research report · 2026-08-24 · {len(all_src)} sources ({zh} Chinese-language) · part of the <a href="index.html">context research series</a></p>
  <h1>China Context Brief</h1>
  <p class="dek">How China builds and sells context management — the open-weight stack that solved long context as an economics problem (DeepSeek, Qwen, Kimi, MiniMax, GLM, MemOS), the funded memory-startup category living inside a platform squeeze and a token price war, and what Chinese competition means for a US builder.</p>
  <div class="tiles">{''.join(tiles)}</div>
</div></header>
<nav class="toc"><div class="wide"><ul>{''.join(nav_items)}</ul></div></nav>
<main>
{''.join(f'<div class="wrap">{f_}</div>' for f_ in frags)}
<section class="part wrap" id="method">
  <h2>Method &amp; sources</h2>
  <p>Two bounded sweeps ran on 2026-08-24 — the Chinese technology stack and the Chinese context/memory market — using Google News RSS in English and Chinese, Mojeek and direct page fetches (the session had no web-search quota), followed by two writers, an accuracy critic and one gap-fill round. Facts sourced only to a headline are labelled "per headline" in the text; Chinese-language sources are cited with outlet and date.</p>
  <ul>{notes}</ul>
  <h3>Source index</h3>
  {''.join(idx)}
</section>
</main>
<footer class="wrap"><p class="muted">Compiled 2026-08-24, split into a standalone report 2026-08-26, by Claude Code.</p></footer>
'''
    css = open(os.path.join(SRC, 'style.css'), encoding='utf-8').read()
    fonts = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=Source+Sans+3:ital,wght@0,400;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;600&display=swap">'
    title = '<title>China Context Brief</title>'
    art = f'{title}\n{fonts}\n<style>{css}</style>\n' + body.replace('{NAV}', series_nav('china-report.html', 'artifact'))
    fbody = body.replace('{NAV}', series_nav('china-report.html', 'file'))
    full = f'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n{title}\n{fonts}\n<style>{css}</style>\n</head>\n<body>\n{fbody}\n</body>\n</html>\n'
    open(os.path.join(SRC, 'china-report.html'), 'w').write(full); open(os.path.join(SRC, 'china-report.artifact.html'), 'w').write(art)
    print(f'wrote china-report.html ({len(full)//1024} KB), sources={len(all_src)}, zh={zh}')

if __name__ == '__main__': main()
