// Vāk web app: library, learning player, create flow, jobs. No build step; talks to web/server.py.
const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const api = async (path, opt = {}) => {
  const r = await fetch(path, Object.assign({ headers: opt.body && !(opt.body instanceof FormData) ? { 'content-type': 'application/json' } : {} }, opt));
  if (!r.ok) { let m = r.statusText; try { m = (await r.json()).detail || m; } catch (e) {} throw new Error(m); }
  return r.json();
};
const fmt = s => { s = Math.round(s || 0); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; };
const view = $('#view');
let cleanup = null;

// ---------------------------------------------------------------- router
async function route() {
  if (cleanup) { cleanup(); cleanup = null; }
  hidePop();
  const [, page, arg] = (location.hash || '#/library').split('/');
  document.querySelectorAll('nav a').forEach(a => a.classList.toggle('on', a.dataset.nav === (page === 'film' ? 'library' : page)));
  window.scrollTo(0, 0);
  try {
    if (page === 'film') await showFilm(decodeURIComponent(arg));
    else if (page === 'create') await showCreate();
    else if (page === 'jobs') await showJobs(arg);
    else await showLibrary();
  } catch (e) { view.innerHTML = `<p class="err">${esc(e.message)}</p>`; }
}
window.addEventListener('hashchange', route);

// ---------------------------------------------------------------- jobs badge
async function pollBadge() {
  try {
    const jobs = await api('/api/jobs'); const n = jobs.filter(j => j.status === 'running' || j.status === 'queued').length;
    const b = $('#jobBadge'); b.hidden = !n; b.textContent = n;
  } catch (e) {}
}
setInterval(pollBadge, 4000); pollBadge();

// ---------------------------------------------------------------- library
async function showLibrary() {
  view.innerHTML = `<h1>Library</h1><p class="lead">Chant films with a learning layer: every word synced to the recording, with its transliteration and meaning. Open one to play it, follow the words and tap any word for its meaning.</p><div id="running"></div><div id="lib" class="muted">Loading…</div>`;
  const [films, jobs] = await Promise.all([api('/api/films'), api('/api/jobs')]);
  const run = jobs.filter(j => j.status === 'running' || j.status === 'queued');
  $('#running').innerHTML = run.map(j => `<a class="job" style="display:block" href="#/jobs/${j.id}"><div class="hd"><b>${esc(j.title)}</b><span class="st running">${esc(j.stage)} · ${Math.round(j.progress)}%</span></div><div class="bar"><i style="width:${j.progress}%"></i></div></a>`).join('');
  const groups = [['studio', 'Made in the studio'], ['film', 'Films'], ['reel', 'Reels (vertical)']];
  $('#lib').outerHTML = groups.map(([k, label]) => {
    const fs = films.filter(f => f.kind === k); if (!fs.length) return '';
    return `<h2>${label}</h2><div class="grid">${fs.map(card).join('')}</div>`;
  }).join('') || `<div class="empty">No films yet. <a href="#/create">Create one</a>.</div>`;
}
function card(f) {
  return `<a class="film ${f.kind}" href="#/film/${encodeURIComponent(f.id)}">
    <div class="poster" style="background-image:url('${f.poster}')"><span class="dur">${fmt(f.duration)}</span></div>
    <div class="meta"><h3>${esc(f.title)}</h3><div class="chips">
      ${f.style_name ? `<span class="chip gold">${esc(f.style_name)}</span>` : ''}
      ${f.narrated ? '<span class="chip">Narrated story</span>' : ''}${f.kind === 'studio' ? '<span class="chip studio">Studio</span>' : ''}
      <span class="prov ${f.provenance.level}">${f.provenance.level}</span></div></div></a>`;
}

// ---------------------------------------------------------------- player
async function showFilm(id) {
  const f = await api('/api/films/' + encodeURIComponent(id));
  const sb = f.storyboard || {}, units = sb.units || [], tl = sb.timeline || {}, V = tl.voice_offset || 0, narr = sb.narration || [];
  view.innerHTML = `
    <p><a href="#/library">← Library</a></p>
    <div class="player ${f.kind === 'reel' ? 'reel' : ''}">
      <div><div class="vidwrap"><video id="vid" src="${f.video}" controls playsinline preload="metadata" poster="${f.poster}"></video></div>
        <div class="row"><h1 style="font-size:32px;margin:0">${esc(f.title)}</h1></div>
        <div class="chips" style="margin-top:8px">${f.style_name ? `<span class="chip gold">${esc(f.style_name)}</span>` : ''}
          ${f.narrated ? '<span class="chip">Narrated story, then the chant</span>' : ''}<span class="chip">${fmt(f.duration)}</span>
          <span class="prov ${f.provenance.level}">${f.provenance.level}</span></div>
        <p class="faint" style="margin-top:8px">${esc(f.provenance.note)}</p></div>
      <div class="panel">
        <div class="now" id="now"></div>
        <div class="lines" id="lines">${units.map((u, i) => `
          <div class="ln" data-i="${i}"><div class="n">${u.verse ?? (u.kind === 'invocation' ? '·' : '')}</div>
          <div><div class="d">${esc(u.devanagari)}</div><div class="i">${esc(u.iast)}</div>${u.english ? `<div class="e">${esc(u.english)}</div>` : ''}</div></div>`).join('')}</div>
        <div class="note">${f.synced ? 'Tap a word for its meaning · tap a line to jump there.' : 'Reels are cut from the film: the text is shown without timing.'}
          Word timing inside a line is estimated from syllables. Translations and meanings are drafts awaiting a teacher's review.</div>
      </div>
    </div>`;
  const vid = $('#vid'), now = $('#now');
  let last = '';
  const unitAt = r => {
    let k = -1;
    units.forEach((u, i) => { if (u.start != null && r >= u.start - 0.35) k = i; });
    if (k < 0) return -1;
    const u = units[k], nx = units[k + 1];
    const until = Math.min(nx && nx.start != null ? nx.start - 0.3 : Infinity, u.end + 1.6);
    return r <= until ? k : -1;
  };
  function render() {
    const t = vid.currentTime, r = t - V;
    let html, key;
    if (!f.synced) { key = 'static'; html = `<div class="label">The chant</div><div class="eng muted">Play the reel; the full text is below.</div>`; }
    else if (narr.length && tl.chant_start && t < tl.chant_start - 0.2) {
      const li = narr.findIndex(l => t >= l.start - 0.1 && t <= l.end + 0.4);
      key = 'n' + li;
      html = `<div class="label">The story · then the chant</div><div class="story">${narr.map((l, i) => i === li || (li < 0 && false) ? `<p class="cur">${esc(l.text)}</p>` : '').join('') || `<p class="cur muted">${t < (tl.narration_start || 0) ? 'The story begins…' : '…'}</p>`}</div>`;
    } else {
      const k = unitAt(r);
      if (k < 0) {
        key = 'idle' + (r < (units[0]?.start ?? 0) ? 'pre' : 'post');
        html = `<div class="label">${r < (units[0]?.start ?? 0) ? 'The chant begins soon' : 'The chant'}</div><div class="dev muted">${esc(units[0]?.devanagari.split(' ')[0] || '')}</div><div class="eng muted">${esc(sb.title || '')}</div>`;
      } else {
        const u = units[k], st = u.words.map(w => r >= w.end ? 'sung' : r >= w.start ? 'cur' : 'up');
        key = k + ':' + st.join();
        html = `<div class="label">${esc(u.label || (u.verse ? 'Verse ' + u.verse : u.kind))}</div>
          <div class="dev">${u.words.map((w, j) => `<span class="w ${st[j]}" data-u="${k}" data-w="${j}">${esc(w.dev)}</span>`).join(' ')}</div>
          <div class="iast">${u.words.map((w, j) => `<span class="iw ${st[j]}">${esc(w.iast)}</span>`).join(' ')}</div>
          <div class="eng">${esc(u.english || '')}</div>`;
        document.querySelectorAll('.ln').forEach(el => el.classList.toggle('on', +el.dataset.i === k));
        if (!last.startsWith(k + ':')) { const el = document.querySelector(`.ln[data-i="${k}"]`); el && el.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }
      }
    }
    if (key !== last) { now.innerHTML = html; last = key; }
  }
  let raf = 0; const loop = () => { render(); raf = requestAnimationFrame(loop); }; loop();
  cleanup = () => cancelAnimationFrame(raf);
  $('#lines').addEventListener('click', e => {
    const ln = e.target.closest('.ln'); if (!ln || !f.synced) return;
    const u = units[+ln.dataset.i]; if (u.start == null) return;
    vid.currentTime = Math.max(0, u.start + V - 0.4); vid.play();
  });
  now.addEventListener('click', e => {
    const w = e.target.closest('.w'); if (!w) return;
    const u = units[+w.dataset.u], wd = u.words[+w.dataset.w];
    showPop(w, wd, () => { vid.currentTime = Math.max(0, wd.start + V - 0.2); vid.play(); hidePop(); });
    vid.pause();
  });
}
function showPop(anchor, wd, onPlay) {
  const p = $('#pop');
  p.innerHTML = `<button class="x" title="Close">×</button><div class="pd">${esc(wd.dev)}</div><div class="pi">${esc(wd.iast)}</div>
    <div class="pm">${wd.meaning ? esc(wd.meaning) : '<span class="muted">Not in the glossary yet. A teacher can add its meaning.</span>'}</div>
    ${wd.split && wd.split !== wd.iast ? `<div class="ps">Words inside: <i>${esc(wd.split)}</i></div>` : ''}
    <div class="row" style="margin-top:10px"><button class="btn ghost" id="popPlay">▶ Hear it</button></div>`;
  p.hidden = false;
  const r = anchor.getBoundingClientRect();
  p.style.left = Math.min(window.innerWidth - 306, Math.max(8, r.left)) + 'px';
  p.style.top = Math.min(window.innerHeight - p.offsetHeight - 8, r.bottom + 8) + 'px';
  $('.x', p).onclick = hidePop; $('#popPlay').onclick = onPlay;
}
function hidePop() { $('#pop').hidden = true; }
document.addEventListener('click', e => { if (!e.target.closest('#pop') && !e.target.closest('.w')) hidePop(); });

// ---------------------------------------------------------------- create
const S = { preset: null, title: '', text: '', translations: {}, units: null, plans: null, audio: null, upload: null, style: 'shadow_puppet' };
async function showCreate() {
  const [presets, styles] = await Promise.all([api('/api/presets'), api('/api/styles')]);
  view.innerHTML = `<h1>Create a chant film</h1>
    <p class="lead">Paste a chant or pick one from the library. Vāk splits it into the lines you chant, adds transliteration and meanings, plans the scenes from what the words mean (never an invented story), and animates it on this laptop in a few minutes.</p>
    <div class="steps">
      <section class="step" id="s1"><h3><span class="k">1</span>The chant</h3>
        <div class="cards">${presets.map(p => `<button class="opt" data-preset="${p.id}"><b>${esc(p.name)}</b><span class="devt">${esc(p.text.split('\n')[0])}</span><span>${esc(p.source)}</span></button>`).join('')}
          <button class="opt" data-preset=""><b>Paste your own</b><span class="devt">ॐ …</span><span>Devanagari; end lines with । or ॥</span></button></div>
        <label class="f">Title</label><input type="text" id="title" placeholder="e.g. The Gāyatrī Mantra">
        <label class="f">Chant text (Devanagari)</label><textarea id="text" placeholder="ॐ भूर्भुवः स्वः ॥&#10;तत्सवितुर्वरेण्यं भर्गो देवस्य धीमहि ।&#10;धियो यो नः प्रचोदयात् ॥ १ ॥"></textarea>
        <div class="row"><button class="btn" id="read">Read the chant →</button><span class="err" id="e1"></span></div></section>
      <section class="step off" id="s2"><h3><span class="k">2</span>Review the text and meaning</h3><div id="review"></div></section>
      <section class="step off" id="s3"><h3><span class="k">3</span>Voice</h3><div class="cards" id="voices"></div>
        <div id="uploadBox" hidden><input type="file" id="file" accept="audio/*"> <span class="faint" id="upInfo"></span></div>
        <p class="faint">A clear recording with short pauses between lines aligns best. Music tracks need line timings (the Gāyatrī preset has them).</p></section>
      <section class="step off" id="s4"><h3><span class="k">4</span>Visual style</h3>
        <div class="cards" id="styles">${styles.map(s => `<button class="opt ${s.id === S.style ? 'on' : ''}" data-style="${s.id}" ${s.available ? '' : 'disabled'}><b>${esc(s.name)}<span class="tag ${s.tier === 'free' ? 'free' : 'prem'}">${s.tier === 'free' ? 'Free · now' : 'Premium · soon'}</span></b><span>${esc(s.eta)}</span></button>`).join('')}</div>
        <div id="scenes"></div>
        <div class="row"><button class="btn" id="go">Generate the film</button><span class="err" id="e4"></span></div></section>
    </div>`;
  // presets
  view.querySelectorAll('[data-preset]').forEach(b => b.onclick = () => {
    view.querySelectorAll('[data-preset]').forEach(x => x.classList.toggle('on', x === b));
    const p = presets.find(x => x.id === b.dataset.preset);
    S.preset = p ? p : null;
    $('#title').value = p ? p.title : ''; $('#text').value = p ? p.text : '';
    S.translations = p ? Object.assign({}, p.translations) : {};
    if (!p) $('#text').focus();
  });
  $('#text').oninput = () => { if (S.preset && $('#text').value.trim() !== S.preset.text.trim()) S.preset = null; };
  $('#read').onclick = async () => {
    $('#e1').textContent = ''; $('#read').disabled = true;
    try {
      const pv = await api('/api/preview', { method: 'POST', body: JSON.stringify({ text: $('#text').value, translations: S.translations }) });
      S.units = pv.units; S.plans = pv.plans; S.text = $('#text').value; S.title = $('#title').value.trim() || 'Untitled chant';
      renderReview(); renderVoices(presets); renderScenes();
      ['s2', 's3', 's4'].forEach(id => $('#' + id).classList.remove('off'));
      $('#s2').scrollIntoView({ behavior: 'smooth' });
    } catch (e) { $('#e1').textContent = e.message; } finally { $('#read').disabled = false; }
  };
  view.querySelectorAll('[data-style]').forEach(b => b.onclick = () => {
    S.style = b.dataset.style; view.querySelectorAll('[data-style]').forEach(x => x.classList.toggle('on', x === b)); renderScenes();
  });
  $('#file').onchange = async () => {
    const f = $('#file').files[0]; if (!f) return;
    $('#upInfo').textContent = 'Uploading…';
    const fd = new FormData(); fd.append('file', f);
    try { S.upload = await api('/api/upload', { method: 'POST', body: fd }); $('#upInfo').textContent = '✓ ' + S.upload.name; }
    catch (e) { $('#upInfo').textContent = e.message; S.upload = null; }
  };
  $('#go').onclick = async () => {
    $('#e4').textContent = '';
    if (!S.audio) { $('#e4').textContent = 'Choose a voice in step 3.'; return; }
    if (S.audio.kind === 'upload' && !S.upload) { $('#e4').textContent = 'Upload the recording first.'; return; }
    view.querySelectorAll('.eng-in').forEach(i => { S.translations[i.dataset.dev] = i.value.trim(); });
    $('#go').disabled = true;
    try {
      const job = await api('/api/jobs', { method: 'POST', body: JSON.stringify({ title: S.title, text: S.text, translations: S.translations, style: S.style,
        audio: S.audio.kind === 'upload' ? { kind: 'upload', id: S.upload.id } : S.audio, preset: S.preset ? S.preset.id : null }) });
      location.hash = '#/jobs/' + job.id; pollBadge();
    } catch (e) { $('#e4').textContent = e.message; $('#go').disabled = false; }
  };
}
function renderReview() {
  const miss = S.units.reduce((n, u) => n + u.words.filter(w => !w.meaning).length, 0);
  const level = S.preset ? 'Identified' : 'Interpreted';
  $('#review').innerHTML = `<div class="chips"><span class="prov ${level}">${level}</span><span class="chip">${S.units.length} chanted lines</span>
      <span class="chip">${miss ? miss + ' words without a glossary meaning' : 'all words have meanings'}</span></div>
    ${S.preset ? `<div class="callout">Matched the library entry <b>${esc(S.preset.name)}</b> (${esc(S.preset.source)}). Translation and meanings are our drafts, awaiting a teacher's review.</div>`
      : `<div class="callout">Context not identified: Vāk will show the practice and its symbols (dawn, light, the sung words) and will not invent a story. Add an English line for each verse below; this chant goes to human review before publishing.</div>`}
    <table class="units"><tr><th>Sanskrit</th><th>Words (hover for meaning)</th><th style="width:34%">English</th></tr>
    ${S.units.map(u => `<tr><td><div class="d">${esc(u.devanagari)}</div><div class="i">${esc(u.iast)}</div></td>
      <td>${u.words.map(w => `<span class="wchip ${w.meaning ? '' : 'miss'}" title="${esc(w.iast + (w.meaning ? ' — ' + w.meaning : ' — not in the glossary yet'))}">${esc(w.dev)}</span>`).join('')}</td>
      <td><input type="text" class="eng-in" data-dev="${esc(u.devanagari)}" value="${esc(u.english)}" placeholder="English meaning of this line"></td></tr>`).join('')}</table>`;
}
function renderVoices(presets) {
  const opts = [];
  if (S.preset && S.preset.recording) opts.push({ kind: 'preset', preset: S.preset.id, name: 'Library recording', desc: S.preset.recording });
  opts.push({ kind: 'upload', name: 'Upload a recording', desc: 'Your own chanting (wav, mp3, m4a…). Lines are found from the pauses.' });
  opts.push({ kind: 'recite', name: 'Neural recitation (draft)', desc: 'A Hindi neural voice recites each line (needs internet; the text is sent to Microsoft). Pronunciation is approximate.' });
  S.audio = null;
  $('#voices').innerHTML = opts.map((o, i) => `<button class="opt" data-v="${i}"><b>${esc(o.name)}</b><span>${esc(o.desc)}</span></button>`).join('');
  $('#voices').querySelectorAll('[data-v]').forEach(b => b.onclick = () => {
    const o = opts[+b.dataset.v]; S.audio = { kind: o.kind, preset: o.preset };
    $('#voices').querySelectorAll('[data-v]').forEach(x => x.classList.toggle('on', x === b));
    $('#uploadBox').hidden = o.kind !== 'upload';
  });
  $('#voices [data-v]').click();
}
function renderScenes() {
  if (!S.plans) return;
  const fam = S.style === 'silhouette' ? 'silhouette' : 'shadow_puppet';
  $('#scenes').innerHTML = `<label class="f">Planned scenes (rule-based planner; anchored to the words, so any recording re-times them)</label>
    <ol class="scenes">${(S.plans[fam] || []).map(s => `<li>${esc(s.title)}</li>`).join('')}</ol>`;
}

// ---------------------------------------------------------------- jobs
async function showJobs(id) {
  const draw = async () => {
    const jobs = id ? [await api('/api/jobs/' + id)] : await api('/api/jobs');
    view.innerHTML = `${id ? '<p><a href="#/jobs">← All jobs</a></p>' : ''}<h1>${id ? 'Making your film' : 'Jobs'}</h1>
      <p class="lead">${id ? 'The engine runs on this laptop: reading the chant, aligning the voice to every word, animating, captions, music and the final mix.' : 'Films being made, one at a time.'}</p>
      ${jobs.length ? jobs.map(j => `<div class="job"><div class="hd"><div><a href="#/jobs/${j.id}"><b style="font:600 21px var(--serif);color:var(--ink)">${esc(j.title)}</b></a>
          <span class="chip" style="margin-left:8px">${esc(j.style.replace('_', ' '))}</span></div>
          <span class="st ${j.status}">${j.status}${j.seconds ? ' · ' + fmt(j.seconds) : ''}</span></div>
        <div class="bar"><i style="width:${j.progress}%"></i></div>
        <div class="row" style="margin-top:4px;justify-content:space-between"><span class="muted">${esc(j.stage)}</span>
          ${j.status === 'done' && j.film ? `<a class="btn" href="#/film/${encodeURIComponent(j.film)}">▶ Watch</a>` : `<span class="faint">${Math.round(j.progress)}%</span>`}</div>
        ${id ? `<pre class="log">${esc((j.log || []).join('\n'))}</pre><p class="faint">Project folder: chants/${esc(j.dir.replace(/^chants\//, ''))}</p>` : ''}</div>`).join('')
        : '<div class="empty">No jobs yet. <a href="#/create">Create a film</a>.</div>'}`;
    return jobs;
  };
  const jobs = await draw();
  const active = () => jobs.some(j => j.status === 'running' || j.status === 'queued');
  let timer = setInterval(async () => { const js = await draw(); if (!js.some(j => j.status === 'running' || j.status === 'queued')) { clearInterval(timer); pollBadge(); } }, 1500);
  if (!active()) clearInterval(timer);
  cleanup = () => clearInterval(timer);
}

route();
