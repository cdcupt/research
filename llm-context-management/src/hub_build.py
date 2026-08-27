#!/usr/bin/env python3
import json, os, sys, glob
SRC = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, SRC); sys.path.insert(0, os.path.dirname(SRC))
from build import esc, series_nav
def n_sources(*globs):
    seen=set()
    for g in globs:
        for f in glob.glob(os.path.join(SRC, g)):
            try:
                for s in json.load(open(f)).get('sources', []): seen.add(str(s.get('url','')).lower().rstrip('/'))
            except Exception: pass
    return len(seen)
CARDS = [
 ('report.html', 'Context Window Playbook', 'The techniques: 8 ranked ways to manage an LLM\'s context window, each with an implementation recipe and code, plus the open-source landscape (30 repos) and a decision flow.', f'{n_sources("sweep/*.json")} sources · researched Aug 20', '🧠'),
 ('context-limits.html', 'The Context Ceiling', 'Why context windows stop near 1M tokens (and GPT-5 exposes 272K of input), the four bottlenecks, how labs extend context, and what distributed systems can and cannot fix.', f'{n_sources("deepdive/sweep/*.json")} sources · researched Aug 21', '⛰️'),
 ('china-report.html', 'China Context Brief', 'The Chinese open-weight stack (DeepSeek, Qwen, Kimi, MiniMax, GLM, MemOS), the funded Chinese memory-startup category, the token price war, and what it means for US builders.', f'{n_sources("china/sweep/*.json")} sources · researched Aug 24', '🇨🇳'),
 ('market-report.html', 'Context Market Map', 'The market: 14 scored problems worth solving, 24 startup profiles with funding, incumbent-platform moves, six case studies, and a go-to-market playbook for a new entrant.', f'{n_sources("market/sweep/*.json")} sources · researched Aug 21', '🗺️'),
 ('investment-report.html', 'AI Investment Outlook', 'Where investors stand: the stock situation with real price trends, private funding at record scale, named investor expectations, and the US-versus-China capital picture.', f'{n_sources("invest/sweep/*.json")} sources · researched Aug 24 · prices {json.load(open(os.path.join(SRC, "invest", "prices.json")))["fetched"]}', '📈'),
]
def main():
    urls = json.load(open(os.path.join(SRC, 'artifacts.json'))) if os.path.exists(os.path.join(SRC, 'artifacts.json')) else {}
    total = sum(int(c[3].split(' ')[0]) for c in CARDS)
    def cards(mode):
        out=''
        for f, name, desc, stats, emo in CARDS:
            href = urls.get(f) if mode == 'artifact' else f
            if not href: href = f
            out += (f'<a class="hubcard" href="{esc(href)}"><div class="emo">{emo}</div><h2>{esc(name)}</h2><p>{esc(desc)}</p><div class="stats">{esc(stats)}</div></a>')
        return out
    def body(mode):
        return f'''
{series_nav('index.html', mode)}<header class="masthead"><div class="wrap">
  <p class="eyebrow">Research series · August 2026 · ~{total} unique sources across five reports</p>
  <h1>Context Research Series</h1>
  <p class="dek">Five linked reports on how LLM applications manage context — the techniques, the hard model limits, the Chinese ecosystem, the market to build in, and the money behind it. Each report is self-contained, dated, and fully sourced.</p>
</div></header>
<main><section class="part wide"><div class="hubgrid">{cards(mode)}</div>
<p class="muted" style="margin-top:24px">Built with multi-agent research workflows in Claude Code; sources, generators and raw agent outputs live in <a href="https://github.com/cdcupt/research">cdcupt/research</a>.</p></section></main>
'''
    css = open(os.path.join(SRC, 'style.css'), encoding='utf-8').read() + '''
.hubgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:18px;margin-top:10px}
.hubcard{display:block;background:var(--surface);border:1px solid var(--hair);border-radius:10px;padding:22px 22px 18px;text-decoration:none;color:var(--ink);transition:border-color .15s}
.hubcard:hover{border-color:var(--accent)}
.hubcard .emo{font-size:28px;margin-bottom:10px}
.hubcard h2{font-size:21px;margin-bottom:8px}
.hubcard p{color:var(--ink2);font-size:14.5px;margin:0 0 12px}
.hubcard .stats{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}
'''
    fonts = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=Source+Sans+3:ital,wght@0,400;0,600;0,700;1,400&display=swap">'
    title = '<title>Context Research Series</title>'
    full = f'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n{title}\n{fonts}\n<style>{css}</style>\n</head>\n<body>\n{body("file")}\n</body>\n</html>\n'
    open(os.path.join(SRC, 'index.html'), 'w').write(full)
    open(os.path.join(SRC, 'index.artifact.html'), 'w').write(f'{title}\n{fonts}\n<style>{css}</style>\n{body("artifact")}')
    print(f'wrote index.html ({len(full)//1024} KB), total sources ~{total}')
if __name__ == '__main__': main()
