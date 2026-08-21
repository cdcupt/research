// Usage: node shoot.js <html-path> <out-dir>  — screenshots at 1440/768/390/320 and reports horizontal overflow
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [,, htmlPath, outDir] = process.argv;
  const browser = await chromium.launch();
  const widths = [1440, 768, 390, 320];
  for (const w of widths) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 }, deviceScaleFactor: 2 });
    const page = await ctx.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(String(e)));
    await page.goto('file://' + path.resolve(htmlPath), { waitUntil: 'load' });
    await page.waitForTimeout(600);
    const m = await page.evaluate(() => {
      const de = document.documentElement;
      const over = [];
      for (const el of document.querySelectorAll('body *')) {
        const r = el.getBoundingClientRect();
        if (r.right > de.clientWidth + 1 && r.width > 0) over.push(el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.className && typeof el.className === 'string' ? '.' + el.className.split(' ').slice(0,2).join('.') : ''));
      }
      return { scrollWidth: de.scrollWidth, clientWidth: de.clientWidth, pageHeight: de.scrollHeight, overflowing: [...new Set(over)].slice(0, 12) };
    });
    const full = path.join(outDir, `w${w}-full.png`);
    const top = path.join(outDir, `w${w}-top.png`);
    await page.screenshot({ path: top, fullPage: false });
    if (w === 1440 || w === 390) {
      const figs = await page.$$('figure');
      for (let i = 0; i < figs.length; i++) {
        try { await figs[i].scrollIntoViewIfNeeded(); await figs[i].screenshot({ path: path.join(outDir, `w${w}-fig${String(i+1).padStart(2,'0')}.png`) }); } catch (e) { console.log('   fig', i+1, 'screenshot failed:', String(e).slice(0,80)); }
      }
      console.log(`   captured ${figs.length} figure screenshots`);
      const secs = await page.$$('section.technique');
      for (const i of [0, 1, secs.length - 1].filter((v, k, a) => v >= 0 && a.indexOf(v) === k)) {
        try { await secs[i].scrollIntoViewIfNeeded(); await secs[i].screenshot({ path: path.join(outDir, `w${w}-sec${i+1}.png`) }); } catch (e) { console.log('   sec', i+1, 'failed:', String(e).slice(0,80)); }
      }
    }
    await page.screenshot({ path: full, fullPage: true });
    console.log(`${w}px: scrollWidth=${m.scrollWidth} clientWidth=${m.clientWidth} ${m.scrollWidth > m.clientWidth ? 'OVERFLOW ❌' : 'ok ✅'} height=${m.pageHeight} errors=${errors.length}`);
    if (m.overflowing.length) console.log('   overflowing:', m.overflowing.join(', '));
    if (errors.length) console.log('   js errors:', errors.slice(0,3).join(' | '));
    await ctx.close();
  }
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
