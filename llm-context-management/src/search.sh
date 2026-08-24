#!/bin/bash
# search.sh <engine> <query terms...> — discovery when WebSearch is unavailable.
# Engines: gnews (Google News RSS, EN) | gnews-zh (Google News RSS, Chinese) | mojeek (general web) | ddg (backup; trips bot detection if called fast)
# Output: URL<TAB>TITLE<TAB>DATE(if any). Sleep ≥2s between calls; for ddg ≥20s.
eng="$1"; shift
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 Chrome/126 Safari/537.36"
q=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(' '.join(sys.argv[1:])))" "$@")
case "$eng" in
  gnews|gnews-zh)
    loc="hl=en-US&gl=US&ceid=US:en"; [ "$eng" = gnews-zh ] && loc="hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
    curl -sS --max-time 20 -A "$UA" "https://news.google.com/rss/search?q=$q&$loc" | python3 -c '
import sys,re,html
t=sys.stdin.read()
for it in re.findall(r"<item>(.*?)</item>", t, re.S)[:12]:
    ti=re.search(r"<title>(.*?)</title>", it); li=re.search(r"<link>(.*?)</link>", it); da=re.search(r"<pubDate>(.*?)</pubDate>", it)
    print((li.group(1) if li else "")+"\t"+html.unescape(ti.group(1) if ti else "")+"\t"+(da.group(1)[:16] if da else ""))' ;;
  mojeek)
    curl -sS --max-time 20 -A "$UA" "https://www.mojeek.com/search?q=$q" | python3 -c '
import sys,re,html
t=sys.stdin.read()
for m in re.findall(r"class=\"title\"[^>]*href=\"(http[^\"]+)\"[^>]*>(.*?)</a>", t)[:12]:
    print(m[0]+"\t"+html.unescape(re.sub(r"<[^>]+>","",m[1])))' ;;
  ddg)
    curl -sS --max-time 20 -A "$UA" "https://html.duckduckgo.com/html/?q=$q" | python3 -c '
import sys,re,html,urllib.parse
t=sys.stdin.read()
for m in re.findall(r"result__a\"[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", t)[:12]:
    u=m[0]; g=re.search(r"uddg=([^&]+)", u)
    if g: u=urllib.parse.unquote(g.group(1))
    print(u+"\t"+html.unescape(re.sub(r"<[^>]+>","",m[1])))' ;;
  *) echo "usage: search.sh gnews|gnews-zh|mojeek|ddg <query>" >&2; exit 2 ;;
esac
