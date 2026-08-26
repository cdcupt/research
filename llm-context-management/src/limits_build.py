#!/usr/bin/env python3
"""Build the standalone Context Ceiling report from the deep-dive data."""
import json, re, os, sys, glob
from collections import OrderedDict, Counter
SRC = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(SRC))
sys.path.insert(0, SRC)
import build as base
from build import esc, clean_fragment, series_nav, svg_context_dumbbell, svg_kv_memory, svg_approach_map, svg_causes
DD = os.path.join(SRC, 'deepdive')

def main():
    dd = json.load(open(os.path.join(DD, 'result.json'))); w = dd.get('writer') or {}
    frag = clean_fragment(open(os.path.join(DD, 'sections', 'context-limits.html'), encoding='utf-8').read())
    def fig(svg, num, cap): return f'<figure class="breakout"><div class="scroll">{svg}</div><figcaption><span class="swipe">Swipe sideways to see the whole figure. </span><b>Figure {num}.</b> {cap}</figcaption></figure>'
    inj = {}
    if w.get('models'): inj['What the frontier actually offers'] = fig(svg_context_dumbbell(w['models']), 1, 'Nominal context windows (hollow) against independently measured effective length (filled) on a log scale; the diamond marks a lower default or main-tier window. Hover a marker for the source.')
    if w.get('causes') or w.get('kv_models'):
        inj['Why the window is capped'] = (fig(svg_causes(w['causes']), 2, 'Where the ceiling comes from: each mechanical cause produces an engineering or quality consequence; together they explain why vendors stop near 1M tokens and tier their pricing.') if w.get('causes') else '') + (fig(svg_kv_memory(w['kv_models']), 3, 'Memory is the hard wall: the KV cache grows linearly with context — compared with single-GPU capacity (orange lines). Multi-head latent attention (DeepSeek) shrinks it by an order of magnitude.') if w.get('kv_models') else '')
    if w.get('approaches'): inj['How labs extend context'] = fig(svg_approach_map(w['approaches']), 4, 'The ways to push past the ceiling, by layer; dot colour shows maturity. Hover a chip for what it fixes and who uses it.')
    for key, html_ in inj.items():
        m = re.search(r'<h3>[^<]*' + re.escape(key) + r'[^<]*</h3>', frag)
        frag = (frag[:m.start()] + html_ + frag[m.start():]) if m else re.sub(r'(<h3>)', html_ + r'\1', frag, count=1)
    add_p = os.path.join(DD, 'sections', 'addendum-context-limits.html')
    addendum = clean_fragment(open(add_p, encoding='utf-8').read()) if os.path.exists(add_p) else ''
    all_src = OrderedDict()
    for f in sorted(glob.glob(os.path.join(DD, 'sweep', '*.json'))):
        d = json.load(open(f))
        for s_ in d.get('sources', []):
            k = base.norm_url(s_.get('url'))
            if k and k not in all_src: all_src[k] = dict(s_, modality=os.path.basename(f)[:-5])
    by_type = Counter((s_.get('type') or 'other') for s_ in all_src.values())
    PL = dict(paper='papers', blog='blog posts', docs='doc pages', news='news articles', repo='repos', thread='threads', talk='talks', report='reports', other='other')
    tiles = [f'<div class="tile"><b>{len(all_src)}</b><span>sources</span></div>'] + [f'<div class="tile"><b>{by_type[tp]}</b><span>{PL[tp]}</span></div>' for tp in PL if by_type.get(tp)]
    idx = []
    for tp in PL:
        items = sorted([s_ for s_ in all_src.values() if (s_.get('type') or 'other') == tp], key=lambda s_: (-(s_.get('year') or 0), (s_.get('title') or '').lower()))
        if not items: continue
        lis = ''.join(f'<li><a href="{esc(s_.get("url"))}" target="_blank" rel="noopener">{esc(s_.get("title"))}</a> — {esc(s_.get("venue_or_author"))}, {esc(s_.get("year"))}</li>' for s_ in items)
        idx.append(f'<details><summary>{PL[tp].capitalize()} ({len(items)})</summary><ol class="sources">{lis}</ol></details>')
    def clean_note(n): return re.sub(r'\s*/Users/\S+', ' (local file)', str(n or ''))
    stats_lis = ''.join(f'<li><b>{esc(k)}</b>: {v.get("unique_kept", v.get("returned", 0))} unique sources — <span class="muted">{esc(clean_note(v.get("note")))[:360]}</span></li>' for k, v in (dd.get('stats') or {}).items())
    critic = dd.get('critic') or {}
    body = f'''
{{NAV}}<header class="masthead"><div class="wrap">
  <p class="eyebrow">Deep dive · researched 2026-08-21 · {len(all_src)} sources · part of the <a href="index.html">context research series</a></p>
  <h1>The Context Ceiling</h1>
  <p class="dek">Why today's best models stop near one million tokens of context — and GPT-5 exposes just 272K of input — what the real bottlenecks are, how labs push past them, and what a distributed system can and cannot fix.</p>
  <div class="tiles">{''.join(tiles)}</div>
</div></header>
<nav class="toc"><div class="wide"><ul><li><a href="#context-limits">The deep dive</a></li>{'<li><a href="#context-limits-addendum">Addendum</a></li>' if addendum else ''}<li><a href="#method">Method &amp; sources</a></li></ul></div></nav>
<main>
<div class="wrap">{frag}</div>
{f'<div class="wrap">{addendum}</div>' if addendum else ''}
<section class="part wrap" id="method">
  <h2>Method &amp; sources</h2>
  <p>Four bounded research sweeps ran on 2026-08-21 (vendor windows and policies; research limits and extension methods; serving and distributed systems; effective-context benchmarks and pricing), followed by one writer with verification fetches and an accuracy critic with one gap-fill round. The session had no web-search quota, so sources were verified through the arXiv export API, the Semantic Scholar API and direct page fetches; the sweep notes below record what could not be confirmed.</p>
  <ul>{stats_lis}</ul>
  <p><b>Critic verdict:</b> <i>{esc(critic.get("verdict", "n/a"))}</i> — {len(critic.get("fixes") or [])} consistency fixes applied.</p>
  <h3>Source index</h3>
  {''.join(idx)}
</section>
</main>
<footer class="wrap"><p class="muted">Compiled 2026-08-21, split into a standalone report 2026-08-26, by Claude Code. Verify against the linked primary sources; windows and prices change often.</p></footer>
'''
    css = open(os.path.join(SRC, 'style.css'), encoding='utf-8').read()
    fonts = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=Source+Sans+3:ital,wght@0,400;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;600&display=swap">'
    title = '<title>The Context Ceiling</title>'
    art = f'{title}\n{fonts}\n<style>{css}</style>\n' + body.replace('{NAV}', series_nav('context-limits.html', 'artifact'))
    fbody = body.replace('{NAV}', series_nav('context-limits.html', 'file'))
    full = f'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n{title}\n{fonts}\n<style>{css}</style>\n</head>\n<body>\n{fbody}\n</body>\n</html>\n'
    open(os.path.join(SRC, 'context-limits.html'), 'w').write(full); open(os.path.join(SRC, 'context-limits.artifact.html'), 'w').write(art)
    print(f'wrote context-limits.html ({len(full)//1024} KB), sources={len(all_src)}')

if __name__ == '__main__': main()
