// Style: Pattachitra painted cut-outs. Extends the silhouette renderer: same plans, same light effects
// (shield, arrows, rays, mandala, yantra, words, beam), but skies, ground and every object or figure are the
// GPU-painted Pattachitra pieces from art/pattachitra (python -m vak art), moved as cut-out layers.
// Faces are never redrawn: poses are separate paintings that cross-fade; life comes from bob, sway and light.
window.STYLE_BASE = 'silhouette';
window.STYLE_ART = 'pattachitra';
window.STYLE_EXT = function () {
  const { W, H, clamp, lerp, rng } = VAK;
  const base = window.STYLE, B = base.el;
  let ART = {};                 // filled in init(): setup() delivers the data after this file runs
  const IMG = {};
  const has = id => !!IMG[id];

  // ---------- colour ----------
  const hex = c => { const n = parseInt(c.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; };
  const rgb = a => `rgb(${a.map(v => Math.round(v)).join(',')})`;
  const mixA = (a, b, u) => a.map((v, i) => lerp(v, b[i], u));
  // flat Pattachitra grounds: [sky, horizon band, ground]; mineral palette, no gradients
  const MOODS = {
    sunset: ['#b4412b', '#e3a33a', '#5d7a35'], gold: ['#d4952a', '#f1cf72', '#62813a'],
    storm: ['#2b2440', '#5c3a4f', '#33402a'], dusk: ['#3a2d66', '#a3566b', '#3f5530'],
    night: ['#121d49', '#24346b', '#26361f'], dawn: ['#7b3e6c', '#ee9f63', '#557537'],
    forest: ['#3e6a46', '#cdb768', '#4f7232'], cosmos: ['#0d0a22', '#261b55', '#14102a'],
    noon: ['#3f7db3', '#f1dcaa', '#6a8a3c'],
  };
  function pal(p) {
    const a = MOODS[p.mood || 'sunset'].map(hex), b = MOODS[p.moodTo || p.mood || 'sunset'].map(hex), u = p.moodMix ?? (p.moodTo ? 1 : 0);
    return a.map((c, i) => mixA(c, b[i], clamp(u, 0, 1)));
  }
  function glow(ctx, x, y, r, col, a) {
    if (a <= 0) return; const g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, col.replace(/[\d.]+\)$/, `${a})`)); g.addColorStop(1, col.replace(/[\d.]+\)$/, '0)'));
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = g; ctx.fillRect(x - r, y - r, 2 * r, 2 * r); ctx.restore();
  }

  // ---------- pieces ----------
  // draw piece `id` with its height h (px), anchored at (x, y) by anchor [ax, ay] of the piece; dir -1 mirrors it
  function piece(ctx, id, x, y, h, o = {}) {
    const im = IMG[id]; if (!im) return false; const e = ART[id];
    const w = h * e.w / e.h, [ax, ay] = o.anchor || [0.5, 1];
    ctx.save(); ctx.translate(x, y); if (o.rot) ctx.rotate(o.rot); ctx.scale((o.dir ?? 1) * (o.sx ?? 1), o.sy ?? 1);
    if (o.alpha != null) ctx.globalAlpha *= clamp(o.alpha, 0, 1);
    ctx.drawImage(im, -ax * w, -ay * h, w, h); ctx.restore(); return true;
  }

  // figure role + pose -> painting; h = height of that painting relative to a standing figure
  const POSE_ART = {
    king: { stand: ['king_stand', 1], point: ['king_point', 1], kneel: ['king_kneel', 0.74], lay_down: ['king_lay', 0.8], walk: ['king_bare', 1], ride: ['horse_king', 1] },
    vasishtha: { stand: ['vasishtha_stand', 1.06], bow: ['vasishtha_bow', 0.9], raise_staff: ['vasishtha_staff', 1.18] },
    ascetic: { meditate: ['ascetic_young', 0.62], look_back: ['ascetic_look', 0.62], meditate_up: ['ascetic_up', 0.64] },
    dancer: { dance: ['dancer_a', 1.02], dance2: ['dancer_b', 1.0] },
    soldier: { stand: ['soldier', 1.12] },
  };
  // while the cast is not painted yet, borrow the library's sage
  const FALLBACK = { vasishtha_stand: 'sage_stand', vasishtha_bow: 'sage_stand', vasishtha_staff: 'sage_offer',
    ascetic_young: 'sage_sit', ascetic_old: 'sage_sit', ascetic_look: 'sage_sit', ascetic_up: 'sage_sit' };
  const pick = id => has(id) ? id : (FALLBACK[id] && has(FALLBACK[id]) ? FALLBACK[id] : null);
  const STAND_H = 470;          // a standing person at s = 1 (as tall as the silhouette figures)

  function poseArt(p, pose) {
    const role = p.role || 'sage', set = POSE_ART[role] || {};
    if (role === 'king' && p.crown !== undefined && !p.crown) return ['king_bare', 1];
    if (role === 'king' && p.walk && !set[pose]) return ['king_stand', 1];
    if (role === 'ascetic' && (pose === 'meditate')) return [(p.beard ?? 0.3) > 0.65 ? 'ascetic_old' : 'ascetic_young', 0.62];
    return set[pose] || set.stand || [null, 1];
  }
  function drawPose(ctx, p, t, pose, alpha) {
    let [id, k] = poseArt(p, pose); id = id && pick(id);
    if (!id) { ctx.save(); ctx.globalAlpha *= alpha; B.figure(ctx, p, t, {}); ctx.restore(); return; }
    const s = p.s ?? 1, seed = (p.x || 0) * 37 + (p.role || '').length;
    const ph = t * (p.pace || 1.5) * Math.PI * 2, w = p.walk || 0;
    const bob = Math.abs(Math.sin(ph)) * 9 * w * s, rock = Math.sin(ph) * 0.025 * w;
    const sway = (1 - w) * 0.008 * Math.sin(t * 0.8 + seed), breath = 1 + (1 - w) * 0.012 * Math.sin(t * 1.5 + seed);
    piece(ctx, id, p.x * W, p.y * H - bob, STAND_H * s * k, { dir: p.dir ?? 1, rot: rock + sway, sy: breath, alpha });
    // ascetic's beard grows: cross-fade young -> old over the painted pair
    if ((p.role === 'ascetic') && pose === 'meditate' && has('ascetic_old') && has('ascetic_young')) {
      const u = clamp(((p.beard ?? 0.3) - 0.45) / 0.4, 0, 1), other = id === 'ascetic_old' ? 'ascetic_young' : 'ascetic_old';
      const a2 = id === 'ascetic_old' ? 1 - u : u;
      if (a2 > 0.01) piece(ctx, other, p.x * W, p.y * H, STAND_H * s * k, { dir: p.dir ?? 1, rot: sway, sy: breath, alpha: alpha * a2 });
    }
  }
  const el = Object.assign({}, B);
  el.figure = (ctx, p, t, env) => {
    const s = p.s ?? 1;
    if ((p.headGlow || 0) > 0) {            // halo behind the head: light, not a redrawn face
      const k = (POSE_ART[p.role] || {})[p.pose] ? POSE_ART[p.role][p.pose][1] : 1;
      glow(ctx, p.x * W + (p.dir ?? 1) * 20 * s, p.y * H - STAND_H * s * k * 0.86, 230 * s * p.headGlow + 70, 'rgba(255,226,150,0.95)', p.headGlow);
    }
    const u = clamp(p.poseMix ?? (p.poseTo ? 1 : 0), 0, 1);
    const a = p.pose || 'stand', b = p.poseTo || a;
    if (a === b || u <= 0) drawPose(ctx, p, t, a, 1);
    else if (u >= 1) drawPose(ctx, p, t, b, 1);
    else { drawPose(ctx, p, t, a, 1 - u); drawPose(ctx, p, t, b, u); }
  };

  el.sky = (ctx, p, t, env) => {
    const P = pal(p), hz = (p.horizon ?? 0.68) * H; env.sky = P;
    { const o = ctx.getTransform().transformPoint(new DOMPoint(W / 2, hz * 0.85)); env.light = { x: o.x, y: o.y }; }
    ctx.fillStyle = rgb(P[0]); ctx.fillRect(-W, -H, 3 * W, hz + H);
    // painted horizon: a flat lighter band with a dotted edge, as in Pattachitra skies
    ctx.fillStyle = rgb(mixA(P[0], P[1], 0.55)); ctx.fillRect(-W, hz - H * 0.2, 3 * W, H * 0.2);
    ctx.fillStyle = rgb(P[1]); ctx.fillRect(-W, hz - H * 0.09, 3 * W, H * 0.09);
    ctx.fillStyle = 'rgba(255,248,225,0.55)';
    for (let x = -W; x < 2 * W; x += 22) { ctx.beginPath(); ctx.arc(x, hz - H * 0.2, 2.6, 0, Math.PI * 2); ctx.fill(); }
    ctx.fillStyle = rgb(P[2]); ctx.fillRect(-W, hz, 3 * W, 2 * H);
    // a few painted clouds drifting (not at night or in the cosmos)
    const night = ['night', 'cosmos', 'storm'].includes(p.moodTo && (p.moodMix ?? 1) > 0.5 ? p.moodTo : p.mood);
    if (has('cloud') && !night) { const R = rng(p.seed || 41); for (let i = 0; i < 3; i++) piece(ctx, 'cloud', ((R() * 1.3 - 0.15) * W + t * (8 + i * 4)) % (W * 1.4) - W * 0.1, H * (0.12 + R() * 0.2), 90 + R() * 50, { anchor: [0.5, 0.5], alpha: 0.9 }); }
    if ((p.dark || 0) > 0) { ctx.save(); ctx.globalAlpha = clamp(p.dark, 0, 0.92); ctx.fillStyle = '#05061a'; ctx.fillRect(-W, -H, 3 * W, 3 * H); ctx.restore(); }
    if ((p.flash || 0) > 0) { ctx.save(); ctx.globalAlpha = clamp(p.flash, 0, 1); ctx.fillStyle = '#fff4dc'; ctx.fillRect(-W, -H, 3 * W, 3 * H); ctx.restore(); }
  };
  el.ground = (ctx, p, t, env) => {          // flat painted ground with a dotted edge and leaf tufts
    const y0 = p.y * H, P = env.sky || MOODS.forest.map(hex), col = P[2];
    ctx.fillStyle = rgb(col); ctx.fillRect(-W, y0, 3 * W, 2 * H);
    ctx.fillStyle = '#1a120c'; ctx.fillRect(-W, y0 - 3, 3 * W, 5);
    ctx.fillStyle = 'rgba(255,246,220,0.7)'; for (let x = -W; x < 2 * W; x += 18) { ctx.beginPath(); ctx.arc(x, y0 + 12, 2.4, 0, Math.PI * 2); ctx.fill(); }
    if (p.grass !== false) {
      const R = rng(p.seed || 7), dk = rgb(mixA(col, [20, 30, 10], 0.55)), lt = rgb(mixA(col, [240, 230, 160], 0.35));
      for (let i = 0; i < 70; i++) {
        const x = R() * W * 1.4 - W * 0.2, y = y0 + 30 + R() * H * 0.1, h = 16 + R() * 18, sw = Math.sin(t * 1.4 + x / 150) * 3;
        for (const [dx, c] of [[-7, dk], [0, lt], [7, dk]]) { ctx.beginPath(); ctx.moveTo(x + dx * 0.4, y); ctx.quadraticCurveTo(x + dx, y - h * 0.6, x + dx * 1.4 + sw, y - h); ctx.quadraticCurveTo(x + dx * 0.8, y - h * 0.4, x + dx * 0.4 + 3, y); ctx.fillStyle = c; ctx.fill(); }
      }
    }
  };
  el.sun = (ctx, p, t, env) => {
    const x = p.x * W, y = p.y * H, r = (p.r ?? 70) * (p.s ?? 1), a = p.a ?? 1; if (a <= 0) return;
    { const o = ctx.getTransform().transformPoint(new DOMPoint(x, y)); env.light = { x: o.x, y: o.y }; }
    glow(ctx, x, y, r * 5, 'rgba(255,220,150,0.8)', 0.6 * a * (p.glow ?? 1));
    if (!has('sun')) return B.sun(ctx, p, t, env);
    if (has('sun_rays')) piece(ctx, 'sun_rays', x, y, r * 3.3, { anchor: [0.5, 0.5], rot: t * 0.08, alpha: a });
    piece(ctx, 'sun', x, y, r * 2.2, { anchor: [0.5, 0.5], rot: -t * 0.03, alpha: a });
  };
  el.moon = (ctx, p, t, env) => {
    const a = p.a ?? 1; if (a <= 0) return; if (!has('moon')) return B.moon(ctx, p, t, env);
    glow(ctx, p.x * W, p.y * H, 180 * (p.s ?? 1), 'rgba(230,236,255,0.6)', 0.5 * a);
    piece(ctx, 'moon', p.x * W, p.y * H, 130 * (p.s ?? 1), { anchor: [0.5, 0.5], alpha: a, rot: -0.3 });
  };
  el.stars = (ctx, p, t) => {
    const R = rng(p.seed || 3), a = p.a ?? 1; if (a <= 0) return; if (!has('star')) return B.stars(ctx, p, t);
    for (let i = 0; i < Math.min(p.n || 160, 70); i++) {   // fewer, bigger painted stars
      const x = R() * W * 1.4 - W * 0.2, y = R() * H * (p.band ?? 0.6) - H * 0.1, sz = 10 + R() * 18, tw = 0.55 + 0.45 * Math.sin(t * (1 + R() * 2) + R() * 6);
      piece(ctx, 'star', x, y, sz, { anchor: [0.5, 0.5], alpha: a * tw, rot: R() * 6 });
    }
  };
  el.mountains = (ctx, p, t, env) => {       // painted hills repeated along the horizon
    if (!has('hills')) return B.mountains(ctx, p, t, env);
    const R = rng(p.seed || 5), h = (p.h ?? 160) * 1.25, e = ART.hills, w = h * e.w / e.h, y0 = p.y * H + h * 0.06;
    ctx.save(); ctx.globalAlpha = 1 - clamp(p.depth ?? 0.6, 0, 1) * 0.25;
    for (let x = -W * 0.4 - R() * w; x < W * 1.4; x += w * 0.78) piece(ctx, 'hills', x, y0, h * (0.85 + R() * 0.3), { anchor: [0, 1], dir: 1 });
    ctx.restore();
  };
  el.tree = (ctx, p, t, env) => {
    const id = has('banyan') ? 'banyan' : null; if (!id) return B.tree(ctx, p, t, env);
    piece(ctx, id, p.x * W, p.y * H + 6, 540 * (p.s ?? 1), { dir: (p.seed || 1) % 2 ? 1 : -1, rot: Math.sin(t * 0.7 + (p.seed || 1)) * 0.008 });
  };
  el.palm = (ctx, p, t, env) => has('palm') ? piece(ctx, 'palm', p.x * W, p.y * H + 4, 430 * (p.s ?? 1), { dir: p.dir ?? 1, rot: Math.sin(t * 0.8) * 0.01 }) : B.palm(ctx, p, t, env);
  el.palace = (ctx, p, t, env) => {
    const id = has('palace') ? 'palace' : has('temple') ? 'temple' : null; if (!id) return B.palace(ctx, p, t, env);
    piece(ctx, id, p.x * W, p.y * H + 4, (id === 'palace' ? 430 : 470) * (p.s ?? 1));
  };
  el.hut = (ctx, p, t, env) => {
    if (!has('hut')) return B.hut(ctx, p, t, env);
    const s = p.s ?? 1, x = p.x * W, y = p.y * H;
    if ((p.smoke ?? 1) > 0) for (let i = 0; i < 6; i++) { const u = ((t * 0.15 + i / 6) % 1); ctx.save(); ctx.globalAlpha = 0.3 * (1 - u); ctx.fillStyle = '#efe6d4'; ctx.beginPath(); ctx.arc(x + (60 + Math.sin(u * 6 + i) * 20) * s, y - (260 + u * 240) * s, (14 + u * 36) * s, 0, Math.PI * 2); ctx.fill(); ctx.restore(); }
    piece(ctx, 'hut', x, y + 4, 290 * s);
  };
  el.cow = (ctx, p, t, env) => {
    if (!has('cow')) return B.cow(ctx, p, t, env);
    const s = p.s ?? 1, w = p.walk || 0, ph = t * 1.4 * Math.PI * 2, g = p.glow || 0;
    if (g > 0) { glow(ctx, p.x * W, p.y * H - 150 * s, 420 * s, 'rgba(255,236,190,0.95)', g); B.rays(ctx, { x: p.x, y: p.y - 150 * s / H, n: 24, len: 520 * s, a: g * 0.5, spin: 0.15 }, t); }
    piece(ctx, 'cow', p.x * W, p.y * H - Math.abs(Math.sin(ph)) * 5 * w * s, 300 * s, { dir: p.dir ?? 1, rot: Math.sin(ph) * 0.015 * w + Math.sin(t * 0.9) * 0.004 });
  };
  el.horse = (ctx, p, t, env) => {
    if (!has('horse_king')) return B.horse(ctx, p, t, env);
    const s = p.s ?? 1, w = p.walk ?? 1, ph = t * 1.6 * Math.PI * 2;
    piece(ctx, 'horse_king', p.x * W, p.y * H - Math.abs(Math.sin(ph)) * 8 * w * s, 640 * s, { dir: p.dir ?? 1, rot: Math.sin(ph) * 0.02 * w });
  };
  el.army = (ctx, p, t, env) => {
    if (!has('soldier')) return B.army(ctx, p, t, env);
    const n = p.n || 8;
    for (let i = n - 1; i >= 0; i--) {       // back row first
      const row = i % 2, x = (p.x ?? 0.5) - i * (p.gap ?? 0.07) * (p.dir ?? 1), y = (p.y ?? 0.8) - row * 0.03;
      el.figure(ctx, { role: 'soldier', pose: 'stand', x, y, s: (p.s ?? 0.5) * (1 - row * 0.12), dir: p.dir ?? 1, walk: p.walk ?? 1, pace: 1.5 }, t + i * 0.23, env);
      if (i % 3 === 1) {                     // painted banner: red with a yellow border and white dots
        const s = p.s ?? 0.5, bx = x * W + 18 * s, by = y * H - 560 * s, fl = 8 * Math.sin(t * 5 + i);
        ctx.fillStyle = '#3a2412'; ctx.fillRect(bx, by, 6, 560 * s);
        ctx.beginPath(); ctx.moveTo(bx + 6, by); ctx.lineTo(bx + 120 * s + fl, by + 30 * s); ctx.lineTo(bx + 6, by + 70 * s); ctx.closePath();
        ctx.fillStyle = '#b8342a'; ctx.fill(); ctx.lineWidth = 5; ctx.strokeStyle = '#e7b53c'; ctx.stroke();
      }
    }
  };
  el.crown = (ctx, p, t, env) => {
    if (!has('crown')) return B.crown(ctx, p, t, env);
    const s = p.s ?? 1; piece(ctx, 'crown', p.x * W, p.y * H, 190 * s, { alpha: p.a ?? 1 });
    if ((p.gleam || 0) > 0) glow(ctx, p.x * W, p.y * H - 120 * s, 140 * s, 'rgba(255,224,150,0.9)', p.gleam);
  };
  el.birds = (ctx, p, t, env) => {
    const f = p.fly ?? 0, n = p.n || 7; if (f <= 0) return; if (!has('egret_up')) return B.birds(ctx, p, t, env);
    for (let i = 0; i < n; i++) {
      const u = clamp(f * 1.3 - i * 0.04, 0, 1), x = lerp(p.x0 ?? -0.1, p.x1 ?? 1.1, u) * W + (i % 3) * 60, y = (p.y ?? 0.3) * H + Math.sin(u * 5 + i) * 30 + (i % 4) * 34;
      const up = Math.sin(t * 7 + i * 1.7) > 0;
      piece(ctx, up || !has('egret_down') ? 'egret_up' : 'egret_down', x, y, 80 * (p.s ?? 1), { anchor: [0.5, 0.5], dir: (p.x1 ?? 1.1) >= (p.x0 ?? -0.1) ? 1 : -1 });
    }
  };
  el.leaves = (ctx, p, t, env) => {
    const a = p.a ?? 0; if (a <= 0) return; const R = rng(19);
    ctx.save(); ctx.globalAlpha = a;
    for (let i = 0; i < 34; i++) {
      const x = (R() * W * 1.2 + Math.sin(t + i) * 60) - W * 0.1, y = ((R() * H + t * (60 + R() * 60)) % H), c = i % 3 ? '#5d8a35' : '#d79a2a';
      ctx.save(); ctx.translate(x, y); ctx.rotate(t * 2 + i);
      ctx.beginPath(); ctx.moveTo(0, -14); ctx.quadraticCurveTo(10, 0, 0, 14); ctx.quadraticCurveTo(-10, 0, 0, -14); ctx.fillStyle = c; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = '#1a120c'; ctx.stroke();
      ctx.restore();
    }
    ctx.restore();
  };

  // cloth texture, made once
  let TEX = null;
  function texture() {
    TEX = document.createElement('canvas'); TEX.width = W; TEX.height = H;
    const c = TEX.getContext('2d'), R = rng(23), img = c.createImageData(W, H);
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const i = (y * W + x) * 4, weave = ((x % 4 < 2) ^ (y % 4 < 2)) ? 10 : -10, v = 128 + weave + (R() - 0.5) * 40;
      img.data[i] = img.data[i + 1] = img.data[i + 2] = v; img.data[i + 3] = 255;
    }
    c.putImageData(img, 0, 0);
  }
  function border(ctx) {                     // Pattachitra frame: black rule, red band with white dots, yellow rule
    const b = 22;
    ctx.fillStyle = '#16100b'; ctx.fillRect(0, 0, W, 6); ctx.fillRect(0, H - 6, W, 6); ctx.fillRect(0, 0, 6, H); ctx.fillRect(W - 6, 0, 6, H);
    ctx.fillStyle = '#a8322a'; ctx.fillRect(6, 6, W - 12, b - 6); ctx.fillRect(6, H - b, W - 12, b - 6); ctx.fillRect(6, 6, b - 6, H - 12); ctx.fillRect(W - b, 6, b - 6, H - 12);
    ctx.fillStyle = '#e8b53a'; ctx.fillRect(b, b, W - 2 * b, 4); ctx.fillRect(b, H - b - 4, W - 2 * b, 4); ctx.fillRect(b, b, 4, H - 2 * b); ctx.fillRect(W - b - 4, b, 4, H - 2 * b);
    ctx.fillStyle = '#fbf1da';
    for (let x = 18; x < W - 10; x += 16) { ctx.beginPath(); ctx.arc(x, 14, 2.4, 0, 6.3); ctx.arc(x, H - 14, 2.4, 0, 6.3); ctx.fill(); }
    for (let y = 18; y < H - 10; y += 16) { ctx.beginPath(); ctx.arc(14, y, 2.4, 0, 6.3); ctx.arc(W - 14, y, 2.4, 0, 6.3); ctx.fill(); }
  }

  window.STYLE = {
    name: 'pattachitra_anim', el, fadeColor: '#1a0f0a',
    init(ctx, plan) {
      if (base.init) base.init(ctx, plan);
      ART = (window.VAK_DATA && VAK_DATA.art) || {};
      for (const [id, e] of Object.entries(ART)) { const im = new Image(); im.src = e.src; IMG[id] = im; }
    },
    ready() { return Promise.all(Object.values(IMG).map(im => im.decode())); },
    post(ctx, t) {
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      if (!TEX) texture();
      ctx.save(); ctx.globalCompositeOperation = 'overlay'; ctx.globalAlpha = 0.16; ctx.drawImage(TEX, 0, 0); ctx.restore();
      border(ctx);
    },
  };
};
