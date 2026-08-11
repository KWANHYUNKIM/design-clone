# Extraction snippets

Run each with `javascript_tool{action:"javascript_exec", tabId, text:<snippet>}`. The tool uses REPL semantics — the last expression is the return value, so no `return` at top level. Save each result to `02-extract/<label>-<name>.json`, where `<label>` is the recon agent's assigned label (`desktop`, `mobile`, …).

Run these at **each viewport width** you care about (1440, 768, 375) — the values change.

---

## 1. Design tokens — `02-extract/tokens.json`

The frequency ranking is the point: the top 3 font sizes, the top 5 colors, the top 2 radii *are* the design system. Everything below that is noise.

```js
(() => {
  const tally = {};
  const bump = (k, v) => { if (!v || v === 'none' || v === 'normal') return; (tally[k] ||= {}); tally[k][v] = (tally[k][v] || 0) + 1; };
  for (const e of document.querySelectorAll('body, body *')) {
    const r = e.getBoundingClientRect();
    if (!r.width && !r.height) continue;              // skip hidden
    const s = getComputedStyle(e);
    if (s.visibility === 'hidden' || s.display === 'none') continue;
    const hasText = [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (hasText) {
      bump('fontFamily', s.fontFamily);
      bump('fontSize', s.fontSize);
      bump('fontWeight', s.fontWeight);
      bump('lineHeight', s.lineHeight);
      bump('letterSpacing', s.letterSpacing);
      bump('textColor', s.color);
    }
    if (s.backgroundColor !== 'rgba(0, 0, 0, 0)') bump('bgColor', s.backgroundColor);
    if (s.borderRadius !== '0px') bump('radius', s.borderRadius);
    if (s.boxShadow !== 'none') bump('shadow', s.boxShadow);
    if (s.borderTopWidth !== '0px' || s.borderBottomWidth !== '0px') bump('border', `${s.borderTopWidth} ${s.borderTopStyle} ${s.borderTopColor}`);
    if (s.display === 'flex' || s.display === 'grid') bump('gap', s.gap);
  }
  const top = o => Object.entries(o).sort((a, b) => b[1] - a[1]).slice(0, 14).map(([v, n]) => `${v}  (${n})`);
  return JSON.stringify(Object.fromEntries(Object.entries(tally).map(([k, v]) => [k, top(v)])), null, 1);
})()
```

## 2. CSS custom properties — `02-extract/vars.json`

If this comes back populated, the site handed you its palette. Reuse the same variable names in the clone so the mapping stays obvious.

```js
(() => {
  const out = {};
  const rs = getComputedStyle(document.documentElement);
  for (const sheet of document.styleSheets) {
    let rules; try { rules = sheet.cssRules } catch { continue }   // cross-origin sheets throw
    const scan = list => { for (const r of list || []) {
      if (r.cssRules) scan(r.cssRules);                            // @media / @supports
      if (r.style) for (const p of r.style) if (p.startsWith('--')) out[p] = rs.getPropertyValue(p).trim() || r.style.getPropertyValue(p).trim();
    }};
    scan(rules);
  }
  return JSON.stringify(out, null, 1);
})()
```

## 3. Fonts — `02-extract/fonts.json`

`status:"loaded"` entries are the ones actually rendering. Note the `@font-face` src to tell a Google Font from a self-hosted licensed one.

```js
(() => {
  const faces = [];
  for (const sheet of document.styleSheets) {
    let rules; try { rules = sheet.cssRules } catch { continue }
    for (const r of rules || []) if (r.constructor.name === 'CSSFontFaceRule')
      faces.push({ family: r.style.fontFamily, weight: r.style.fontWeight, src: (r.style.src || '').slice(0, 200) });
  }
  return JSON.stringify({
    loaded: [...document.fonts].map(f => `${f.family} | ${f.weight} | ${f.style} | ${f.status}`),
    fontFaceRules: faces,
    stylesheetLinks: [...document.querySelectorAll('link[rel="stylesheet"], link[rel="preload"][as="font"]')].map(l => l.href),
    bodyStack: getComputedStyle(document.body).fontFamily
  }, null, 1);
})()
```

## 4. Layout skeleton — `02-extract/layout.txt`

The blueprint, and the file the architect leans on hardest. `@x,y` is document-absolute, so
it survives scrolling.

**Do not cap the depth at a small number.** Modern sites bury content under four or five
pass-through wrappers (`#wrap > #container > .content > .conbox > section`), so a depth-4
walk stops exactly *at* the sections and emits nothing inside them — a file that looks
plausible, lists every section, and is useless for building. The walk below instead spends
its budget on **structure**, by not counting a wrapper that is the same size as its only
child. Depth is generous (14) because the size filter, not the depth, is what keeps the
output bounded.

Sanity-check the result before trusting it: it should contain headings, buttons and images,
not just `<section>` lines. If the deepest line is a section wrapper, the walk never reached
the content — raise `MAX` and re-run.

```js
(() => {
  const MAX = 14, LIMIT = 5000;
  const lines = [];
  const walk = (el, d) => {
    if (d > MAX || lines.length > LIMIT) return;
    for (const c of el.children) {
      if (['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE', 'SVG', 'PATH'].includes(c.tagName)) continue;
      const r = c.getBoundingClientRect();
      if (r.width < 24 || r.height < 12) continue;
      const s = getComputedStyle(c);
      // a wrapper that adds no geometry of its own does not deserve a depth level
      const passThrough = c.children.length === 1
        && Math.abs(c.children[0].getBoundingClientRect().height - r.height) < 2
        && Math.abs(c.children[0].getBoundingClientRect().width - r.width) < 2;
      const cls = typeof c.className === 'string' && c.className.trim()
        ? '.' + c.className.trim().split(/\s+/).slice(0, 3).join('.') : '';
      const flex = /flex|grid/.test(s.display)
        ? ` ${s.flexDirection || s.gridTemplateColumns} gap:${s.gap} just:${s.justifyContent} align:${s.alignItems}` : '';
      const own = [...c.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim())
        .map(n => n.textContent.trim()).join(' ').slice(0, 40);
      const txt = own ? ` "${own}"` : '';
      const type = /^(H1|H2|H3|H4|P|SPAN|A|BUTTON|LI)$/.test(c.tagName)
        ? ` ${s.fontSize}/${s.lineHeight} ${s.fontWeight} ${s.color}` : '';
      const img = c.tagName === 'IMG' ? ` src:${(c.currentSrc || c.src || '').split('/').pop().slice(0, 40)}` : '';
      lines.push(`${'  '.repeat(d)}<${c.tagName.toLowerCase()}${c.id ? '#' + c.id : ''}${cls}> `
        + `${Math.round(r.width)}x${Math.round(r.height)} @${Math.round(r.x)},${Math.round(r.y + scrollY)} `
        + `${s.display}${flex} pad:${s.padding} mar:${s.margin}${type}${img}${txt}`);
      walk(c, passThrough ? d : d + 1);
    }
  };
  walk(document.body, 0);
  return `lines:${lines.length}${lines.length > LIMIT ? ' (TRUNCATED — raise LIMIT)' : ''}\n` + lines.join('\n');
})()
```

## 5. Assets — `02-extract/assets.json`

Scroll the full page before running this, or lazy-loaded images report `0x0`.

```js
JSON.stringify({
  images: [...document.images].map(i => ({ src: i.currentSrc || i.src, natural: `${i.naturalWidth}x${i.naturalHeight}`, rendered: `${Math.round(i.getBoundingClientRect().width)}x${Math.round(i.getBoundingClientRect().height)}`, alt: i.alt })),
  inlineSvgCount: document.querySelectorAll('svg').length,
  backgroundImages: [...new Set([...document.querySelectorAll('body *')].map(e => getComputedStyle(e).backgroundImage).filter(v => v && v !== 'none'))].slice(0, 40),
  videos: [...document.querySelectorAll('video')].map(v => v.currentSrc || v.src),
  favicon: [...document.querySelectorAll('link[rel*="icon"]')].map(l => l.href)
}, null, 1)
```

## 6. Page geometry — `02-extract/geometry.json`

`containerWidths` is the money value: the most-repeated wide number is the site's max content width.

```js
(() => {
  const w = {};
  for (const e of document.querySelectorAll('body *')) {
    const r = e.getBoundingClientRect();
    if (r.width > 500) { const k = Math.round(r.width); w[k] = (w[k] || 0) + 1; }
  }
  return JSON.stringify({
    scrollHeight: document.documentElement.scrollHeight,
    viewport: [innerWidth, innerHeight],
    devicePixelRatio,
    bodyBg: getComputedStyle(document.body).backgroundColor,
    containerWidths: Object.entries(w).sort((a, b) => b[1] - a[1]).slice(0, 10).map(([px, n]) => `${px}px (${n}x)`),
    sections: [...document.querySelectorAll('body > *, main > *, body > div > *')].map(e => {
      const r = e.getBoundingClientRect();
      return r.height > 40 ? `${e.tagName.toLowerCase()}${e.className && typeof e.className === 'string' ? '.' + e.className.trim().split(/\s+/)[0] : ''} h:${Math.round(r.height)} top:${Math.round(r.y + scrollY)}` : null;
    }).filter(Boolean)
  }, null, 1);
})()
```

## 7. Breakpoints — `02-extract/breakpoints.json`

Tells you which widths to actually test instead of guessing 768/1024.

```js
(() => {
  const bps = new Set();
  for (const sheet of document.styleSheets) {
    let rules; try { rules = sheet.cssRules } catch { continue }
    const scan = list => { for (const r of list || []) {
      if (r.media) { for (const m of r.media) { const hit = m.match(/(min|max)-width:\s*([\d.]+)(px|em|rem)/); if (hit) bps.add(hit[0]); } }
      if (r.cssRules) scan(r.cssRules);
    }};
    scan(rules);
  }
  return JSON.stringify([...bps].sort(), null, 1);
})()
```

## 8. Clone verification diff

In Phase 6, run snippet 1 against **both** tabs at the same width and diff the JSON. Numbers don't lie about "looks close".

```js
(() => {
  const pick = sel => { const e = document.querySelector(sel); if (!e) return `NOT FOUND: ${sel}`;
    const s = getComputedStyle(e), r = e.getBoundingClientRect();
    return { sel, box: `${Math.round(r.width)}x${Math.round(r.height)} @${Math.round(r.x)},${Math.round(r.y + scrollY)}`,
      font: `${s.fontFamily.split(',')[0]} ${s.fontSize}/${s.lineHeight} ${s.fontWeight} ls:${s.letterSpacing}`,
      color: s.color, bg: s.backgroundColor, pad: s.padding, mar: s.margin, radius: s.borderRadius, shadow: s.boxShadow };
  };
  return JSON.stringify(['header', 'h1', 'nav a', 'main', 'button, .btn, a.button', 'footer'].map(pick), null, 1);
})()
```
