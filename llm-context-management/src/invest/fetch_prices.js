// fetch_prices.js — US via Yahoo (browser context), HK/SH via Tencent ifzq → prices.json
const { chromium } = require("playwright");
const fs = require("fs");
const US = { NVDA: "Nvidia", MSFT: "Microsoft", GOOGL: "Alphabet", META: "Meta", AMZN: "Amazon", CRWV: "CoreWeave", MDB: "MongoDB", SNOW: "Snowflake", DDOG: "Datadog", SMCI: "Super Micro", BABA: "Alibaba (ADR)" };
const CN = { "hk00700": ["0700.HK", "Tencent"], "hk02513": ["2513.HK", "Zhipu (Z.ai)"], "hk00100": ["0100.HK", "MiniMax"], "sh688256": ["688256.SS", "Cambricon"] };
(async () => {
  const out = { fetched: new Date().toISOString().slice(0, 10), series: {} };
  const b = await chromium.launch(); const ctx = await b.newContext(); const p = await ctx.newPage();
  await p.goto("https://finance.yahoo.com", { waitUntil: "domcontentloaded", timeout: 30000 }).catch(() => {});
  for (const [t, name] of Object.entries(US)) {
    try {
      const r = await ctx.request.get(`https://query1.finance.yahoo.com/v8/finance/chart/${t}?period1=1767225600&period2=9999999999&interval=1d`);
      if (!r.ok()) { console.log(t, "HTTP", r.status()); continue; }
      const d = (await r.json()).chart.result[0];
      const ts = d.timestamp || []; const cl = d.indicators.quote[0].close || [];
      const pts = ts.map((s, i) => [new Date(s * 1000).toISOString().slice(0, 10), cl[i]]).filter(x => x[1] != null);
      out.series[t] = { name, currency: d.meta.currency, source: "Yahoo Finance", points: pts };
      console.log(t, pts.length, "pts", pts[0][0], "→", pts[pts.length - 1][0], pts[pts.length - 1][1].toFixed(2));
    } catch (e) { console.log(t, "ERR", String(e).slice(0, 80)); }
    await p.waitForTimeout(400);
  }
  await b.close();
  // Tencent for CN/HK via fetch (node18+ global fetch)
  for (const [sym, [t, name]] of Object.entries(CN)) {
    try {
      const r = await fetch(`https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=${sym},day,2026-01-01,2026-08-26,320,qfq`);
      const d = await r.json(); const rec = d.data[sym] || {}; const days = rec.qfqday || rec.day || [];
      const pts = days.map(x => [x[0], parseFloat(x[2])]).filter(x => isFinite(x[1]));
      if (!pts.length) { console.log(t, "no points"); continue; }
      out.series[t] = { name, currency: sym.startsWith("hk") ? "HKD" : "CNY", source: "Tencent ifzq", points: pts };
      console.log(t, pts.length, "pts", pts[0][0], "→", pts[pts.length - 1][0], pts[pts.length - 1][1]);
    } catch (e) { console.log(t, "ERR", String(e).slice(0, 80)); }
  }
  fs.writeFileSync("prices.json", JSON.stringify(out));
  console.log("wrote prices.json:", Object.keys(out.series).length, "series");
})();
