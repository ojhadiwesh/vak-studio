// Render an animation plan in one style to video (or a few still frames for checking).
//   node anim.js <style> <data.json> <out.mp4> <t_start> <seconds> [fps=24]
//   node anim.js <style> <data.json> <outDir> --stills t1,t2,...
// data.json = {plan, units}; times are on the audio timeline (seconds).
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), { spawn } = require('child_process');

(async () => {
  const [style, dataPath, out, a4, a5, a6] = process.argv.slice(2);
  const data = JSON.parse(fs.readFileSync(dataPath, 'utf8'));
  const b = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  const errors = []; p.on('pageerror', e => errors.push(e.message)); p.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  await p.goto('file://' + path.join(__dirname, 'anim', 'stage.html') + '?style=' + style);
  await p.waitForFunction('window.styleReady === true', null, { timeout: 30000 });
  await p.evaluate(d => window.setup(d), data);
  await p.evaluate(() => (window.STYLE && STYLE.ready) ? STYLE.ready() : null);   // e.g. painted art pieces decoding
  await p.evaluate(() => document.fonts.load('120px "Tiro Devanagari Sanskrit"', 'ॐ भर्गो देवस्य').then(() => document.fonts.ready));
  if (errors.length) throw new Error(errors.join('\n'));
  const grab = async t => {
    const url = await p.evaluate(t => { window.draw(t); return document.getElementById('c').toDataURL('image/jpeg', 0.93); }, t);
    return Buffer.from(url.slice(url.indexOf(',') + 1), 'base64');
  };
  if (a4 === '--stills') {
    fs.mkdirSync(out, { recursive: true });
    for (const t of a5.split(',').map(Number)) fs.writeFileSync(path.join(out, `t${t.toFixed(2)}.jpg`), await grab(t));
  } else {
    const t0 = Number(a4), secs = Number(a5), fps = Number(a6 || 24), n = Math.round(secs * fps);
    const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
      '-vf', 'scale=in_range=full:out_range=limited,format=yuv420p', '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-color_range', 'tv', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    const started = Date.now();
    for (let i = 0; i < n; i++) {
      const buf = await grab(t0 + i / fps);
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if (errors.length) throw new Error(errors.join('\n'));
      if (i % 240 === 0) process.stderr.write(`[anim] frame ${i}/${n} (${((Date.now() - started) / 1000).toFixed(0)}s)\n`);
    }
    ff.stdin.end(); await new Promise((r, j) => ff.on('close', c => c ? j(new Error('ffmpeg exit ' + c)) : r()));
  }
  await b.close();
})().catch(e => { console.error(e.stack || e); process.exit(1); });
