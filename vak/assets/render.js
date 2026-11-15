// Browser-side renders for the engine. usage:
//   node render.js card   <outDir> <seed>           -> painted watercolour card frames (p5.brush)
//   node render.js title  <out.png> <json>          -> transparent title text {kicker,chapter,title,sub}
//   node render.js captions <states.json> <outDir>  -> one transparent caption PNG per state
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const A = __dirname, F = 'file://' + path.join(A, 'node_modules/@fontsource');
const FONTS = `<meta charset="utf-8"><link rel=stylesheet href="${F}/tiro-devanagari-sanskrit/index.css"><link rel=stylesheet href="${F}/tiro-devanagari-sanskrit/400-italic.css"><link rel=stylesheet href="${F}/cormorant-garamond/500.css"><link rel=stylesheet href="${F}/cormorant-garamond/600.css">`;
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');

async function page(b, w, h) { return b.newPage({ viewport: { width: w, height: h } }); }
async function shot(p, html, out) {
  const f = out + '.html'; fs.writeFileSync(f, html);
  await p.goto('file://' + f, { waitUntil: 'networkidle' }); await p.evaluate(() => document.fonts.ready);
  await p.screenshot({ path: out, omitBackground: true }); fs.unlinkSync(f);
}

(async () => {
  const [mode, a1, a2] = process.argv.slice(2);
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--allow-file-access-from-files'] });
  if (mode === 'card') {
    fs.mkdirSync(a1, { recursive: true });
    const p = await page(b, 1280, 720);
    await p.goto('file://' + path.join(A, 'card.html') + '?seed=' + (a2 || 11));
    await p.waitForFunction('window.ready === true', null, { timeout: 60000 });
    const total = await p.evaluate('window.total'), c = await p.$('canvas');
    await c.screenshot({ path: path.join(a1, 'f000.png') });
    for (let i = 0; i < total; i++) {
      await p.evaluate(i => window.paintStep(i), i);
      await c.screenshot({ path: path.join(a1, `f${String(i + 1).padStart(3, '0')}.png`) });
    }
  } else if (mode === 'title') {
    const t = JSON.parse(a2), p = await page(b, 1920, 1080);
    await shot(p, `<!doctype html><html><head>${FONTS}<style>html,body{margin:0;width:1920px;height:1080px;background:transparent}
.w{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding-bottom:40px}
.a{font-family:'Tiro Devanagari Sanskrit';font-size:64px;color:#9E2B3A}.b{font-family:'Cormorant Garamond';font-weight:600;font-size:30px;letter-spacing:12px;color:#5A4A6E;text-transform:uppercase;margin-top:6px}
.c{font-family:'Cormorant Garamond';font-weight:600;font-size:104px;color:#2B2560;line-height:1.05}.d{font-family:'Tiro Devanagari Sanskrit';font-style:italic;font-size:30px;color:#6B5A3A;margin-top:150px}</style></head>
<body><div class=w><div class=a>${esc(t.kicker)}</div><div class=b>${esc(t.chapter)}</div><div class=c>${esc(t.title)}</div><div class=d>${esc(t.sub)}</div></div></body></html>`, a1);
  } else if (mode === 'subs') {           // narration subtitles: one transparent PNG per line
    const lines = JSON.parse(fs.readFileSync(a1, 'utf8')); fs.mkdirSync(a2, { recursive: true });
    const p = await page(b, 1920, 440);
    for (let i = 0; i < lines.length; i++) {
      await shot(p, `<!doctype html><html><head>${FONTS}<style>html,body{margin:0;width:1920px;height:440px;background:transparent;overflow:hidden}
.band{position:absolute;inset:0;background:linear-gradient(to top,rgba(6,4,12,.82) 0%,rgba(6,4,12,.55) 50%,rgba(6,4,12,0) 100%)}
.t{position:absolute;left:210px;right:210px;bottom:70px;text-align:center;font-family:'Cormorant Garamond';font-weight:600;font-size:52px;line-height:1.25;color:#F7EFDF;text-shadow:0 2px 14px rgba(0,0,0,.9)}</style></head>
<body><div class=band></div><div class=t>${esc(lines[i])}</div></body></html>`, path.join(a2, `sub${String(i).padStart(3, '0')}.png`));
    }
  } else if (mode === 'captions') {
    const data = JSON.parse(fs.readFileSync(a1, 'utf8')); fs.mkdirSync(a2, { recursive: true });
    const p = await page(b, 1920, 440);
    const cls = (k, lit) => (k < lit ? 'sung' : k === lit ? 'lit' : 'dim');
    for (let i = 0; i < data.states.length; i++) {
      const st = data.states[i], u = data.units[st.unit];
      const dev = u.words.map((w, k) => `<span class="${cls(k, st.lit)}">${esc(w.dev)}</span>`).join('');
      const ia = u.words.map((w, k) => `<span class="${cls(k, st.lit)}">${esc(w.iast)}</span>`).join('');
      await shot(p, `<!doctype html><html><head>${FONTS}<style>html,body{margin:0;width:1920px;height:440px;background:transparent;overflow:hidden}
.band{position:absolute;inset:0;background:linear-gradient(to top,rgba(10,6,20,.86) 0%,rgba(10,6,20,.62) 55%,rgba(10,6,20,0) 100%)}
.wrap{position:absolute;left:0;right:0;bottom:52px;display:flex;flex-direction:column;align-items:center;text-align:center}
.who{font-family:'Cormorant Garamond';font-weight:600;font-size:26px;letter-spacing:7px;text-transform:uppercase;color:#E8B95A;margin-bottom:10px;text-shadow:0 2px 8px #000}
.dev{font-family:'Tiro Devanagari Sanskrit';font-size:84px;line-height:1.2;display:flex;gap:26px}
.iast{font-family:'Tiro Devanagari Sanskrit';font-style:italic;font-size:38px;display:flex;gap:16px;margin-top:4px}
.en{font-family:'Cormorant Garamond';font-weight:500;font-size:46px;color:#fff;margin-top:12px;text-shadow:0 2px 10px #000}
.sung{color:#F4EDE1;text-shadow:0 2px 12px rgba(0,0,0,.9)}.lit{color:#FFD98A;text-shadow:0 0 24px rgba(255,190,80,.85),0 0 6px rgba(255,210,120,.9),0 2px 10px #000}
.dim{color:rgba(244,237,225,.38);text-shadow:0 2px 10px rgba(0,0,0,.7)}.iast .lit{color:#FFE2A6}.iast .sung{color:#EADFC8}.iast .dim{color:rgba(234,223,200,.4)}</style></head>
<body><div class=band></div><div class=wrap>${u.label ? `<div class=who>${esc(u.label)}</div>` : ''}<div class=dev>${dev}</div><div class=iast>${ia}</div><div class=en>${esc(u.english)}</div></div></body></html>`,
        path.join(a2, `st${String(i).padStart(3, '0')}.png`));
    }
  }
  await b.close();
})();
