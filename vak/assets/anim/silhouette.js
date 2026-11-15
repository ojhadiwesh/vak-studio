// Style: silhouette paper-cut (story) + sacred-geometry light (mantra finale).
// Figures are solid cut-outs read by outline alone; skies are painted gradients that carry the mood;
// distant layers are tinted toward the horizon for depth. The finale draws geometry and Devanagari in light.
(function () {
  const { W, H, clamp, lerp, rng, noise1 } = VAK;
  const SIL = '#0a0605';
  const D2R = Math.PI / 180;

  // ---------- colour ----------
  const hex = c => { const n = parseInt(c.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; };
  const rgb = a => `rgb(${a.map(v => Math.round(v)).join(',')})`;
  const mixA = (a, b, u) => a.map((v, i) => lerp(v, b[i], u));
  const MOODS = {           // [top, middle, horizon]
    sunset: ['#2a1640', '#b4473a', '#f7b25a'], gold: ['#4b3566', '#d98b4e', '#ffe0a0'],
    storm: ['#120d12', '#4d2220', '#a43d2a'], dusk: ['#171433', '#5a3766', '#d3796a'],
    night: ['#04081a', '#0f1d42', '#26386a'], dawn: ['#18244d', '#a85e74', '#ffc58a'],
    forest: ['#1b2c2a', '#5d7a52', '#dccf92'], cosmos: ['#030209', '#130c30', '#2c1f5c'],
    noon: ['#3d6fa8', '#8fb6d6', '#f4e2b0'],
  };
  function skyPal(p) {
    const a = MOODS[p.mood || 'sunset'].map(hex), b = MOODS[p.moodTo || p.mood || 'sunset'].map(hex), u = p.moodMix ?? (p.moodTo ? 1 : 0);
    return a.map((c, i) => mixA(c, b[i], u));
  }
  // silhouette colour at a depth: 0 = nearest (black), 1 = melts into the horizon
  const depthCol = (env, d) => rgb(mixA(hex(SIL), env.sky ? env.sky[2] : [120, 80, 60], clamp(d || 0, 0, 1) * 0.85));

  // ---------- shape helpers ----------
  function smooth(ctx, pts) {
    const n = pts.length, m = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
    ctx.beginPath(); const s = m(pts[n - 1], pts[0]); ctx.moveTo(s[0], s[1]);
    for (let i = 0; i < n; i++) { const p = pts[i], q = m(p, pts[(i + 1) % n]); ctx.quadraticCurveTo(p[0], p[1], q[0], q[1]); }
    ctx.closePath();
  }
  function poly(ctx, pts) { ctx.beginPath(); pts.forEach((p, i) => i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])); ctx.closePath(); }
  function cut(ctx, pts, col, sharp) { (sharp ? poly : smooth)(ctx, pts); ctx.fillStyle = col; ctx.fill(); }
  function capsule(ctx, L, w1, w2, col) {      // limb from (0,0) down to (0,L)
    ctx.beginPath(); ctx.moveTo(-w1, 0); ctx.lineTo(-w2, L); ctx.arc(0, L, w2, Math.PI, 0, true); ctx.lineTo(w1, 0); ctx.arc(0, 0, w1, 0, Math.PI, true);
    ctx.fillStyle = col; ctx.fill();
  }
  function circle(ctx, x, y, r, col) { ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fillStyle = col; ctx.fill(); }
  function glow(ctx, x, y, r, col, a) {
    if (a <= 0) return;
    const g = ctx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, col); g.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = clamp(a, 0, 1); ctx.fillStyle = g; ctx.fillRect(x - r, y - r, 2 * r, 2 * r); ctx.restore();
  }
  function lacework(ctx, x, y, r, col) {        // paper-cut ornament: tiny cut holes showing the sky
    ctx.save(); ctx.fillStyle = col;
    for (let i = 0; i < 6; i++) { const a = i * Math.PI / 3; ctx.beginPath(); ctx.ellipse(x + Math.cos(a) * r, y + Math.sin(a) * r, r * 0.35, r * 0.16, a, 0, Math.PI * 2); ctx.fill(); }
    ctx.restore();
  }

  // ---------- figures (one rig, many roles) ----------
  const POSES = {   // degrees from straight down, + = forward
    stand:       { uA: 16, fA: 8, uB: -14, fB: 6, th: 0, sh: 0, tB: 0, sB: 0, seat: 0, kneel: 0, lean: 0, head: 0 },
    point:       { uA: 88, fA: 4, uB: -10, fB: 8, th: 6, sh: 0, tB: -6, sB: 0, seat: 0, kneel: 0, lean: 4, head: 0 },
    raise_staff: { uA: 140, fA: 20, uB: 20, fB: 30, th: 4, sh: 0, tB: -4, sB: 0, seat: 0, kneel: 0, lean: -4, head: -6 },
    shield:      { uA: 25, fA: 70, uB: 15, fB: 60, th: 0, sh: 0, tB: 0, sB: 0, seat: 0, kneel: 0, lean: -12, head: -10 },
    kneel:       { uA: 10, fA: 100, uB: 6, fB: 96, th: 90, sh: -90, tB: 4, sB: 96, seat: 0, kneel: 1, lean: 22, head: 18 },
    bow:         { uA: 40, fA: 120, uB: 34, fB: 118, th: 0, sh: 0, tB: 0, sB: 0, seat: 0, kneel: 0, lean: 34, head: 20 },
    meditate:    { uA: 18, fA: 72, uB: 12, fB: 70, th: 0, sh: 0, tB: 0, sB: 0, seat: 1, kneel: 0, lean: 0, head: 4 },
    meditate_up: { uA: 18, fA: 72, uB: 12, fB: 70, th: 0, sh: 0, tB: 0, sB: 0, seat: 1, kneel: 0, lean: -4, head: -16 },
    look_back:   { uA: 18, fA: 72, uB: 12, fB: 70, th: 0, sh: 0, tB: 0, sB: 0, seat: 1, kneel: 0, lean: -6, head: -34 },
    dance:       { uA: 125, fA: -50, uB: 60, fB: 80, th: 22, sh: 40, tB: -10, sB: 10, seat: 0, kneel: 0, lean: -8, head: -8 },
    dance2:      { uA: 70, fA: 90, uB: 140, fB: -40, th: -14, sh: 10, tB: 24, sB: 46, seat: 0, kneel: 0, lean: 8, head: 6 },
    ride:        { uA: 38, fA: 58, uB: 30, fB: 56, th: 38, sh: -34, tB: 32, sB: -30, seat: 0, kneel: 0, lean: 6, head: 0 },
    lay_down:    { uA: 70, fA: 30, uB: 60, fB: 30, th: 0, sh: 0, tB: 0, sB: 0, seat: 0, kneel: 0, lean: 40, head: 25 },
  };
  function poseAt(p, t) {
    const a = POSES[p.pose || 'stand'], b = POSES[p.poseTo || p.pose || 'stand'], u = p.poseMix ?? (p.poseTo ? 1 : 0), q = {};
    for (const k in a) q[k] = lerp(a[k], b[k], u);
    q.bob = 0;
    if (p.walk) {
      const ph = t * (p.pace || 1.5) * Math.PI * 2, w = p.walk;
      q.th += 26 * Math.sin(ph) * w; q.tB -= 26 * Math.sin(ph) * w;
      q.sh -= Math.max(0, 34 * Math.sin(ph - 1.2)) * w; q.sB -= Math.max(0, -34 * Math.sin(ph - 1.2)) * w;
      if (!p.spear && !p.staff) { q.uA += 18 * Math.sin(ph) * w; q.uB -= 18 * Math.sin(ph) * w; }
      q.bob = Math.abs(Math.sin(ph)) * 6 * w;
    }
    return q;
  }
  function scarf(ctx, x0, y0, L, w0, dirBack, t, ph, col) {   // a cloth strip rippling in the wind
    const pts = [], n = 10;
    for (let i = 0; i <= n; i++) { const u = i / n; pts.push([x0 + dirBack * (L * 0.32 * u + Math.sin(t * 3.0 + ph - u * 4) * 16 * u), y0 + L * u, w0 * (1 - u * 0.55)]); }
    ctx.beginPath(); pts.forEach(([x, y, w], i) => i ? ctx.lineTo(x - w / 2, y) : ctx.moveTo(x - w / 2, y));
    for (let i = n; i >= 0; i--) ctx.lineTo(pts[i][0] + pts[i][2] / 2, pts[i][1]); ctx.closePath(); ctx.fillStyle = col; ctx.fill(); return;
    ctx.beginPath(); pts.forEach(([x, y, w], i) => i ? ctx.lineTo(x, y - w / 2) : ctx.moveTo(x, y - w / 2));
    for (let i = n; i >= 0; i--) ctx.lineTo(pts[i][0], pts[i][1] + pts[i][2] / 2); ctx.closePath(); ctx.fillStyle = col; ctx.fill();
  }
  function hand(ctx, col) { cut(ctx, [[-9, -4], [9, -4], [11, 10], [5, 22], [-5, 21], [-10, 9]], col); cut(ctx, [[8, 0], [16, 6], [12, 12], [7, 8]], col); }
  function drawFigure(ctx, p, t, env, colOverride) {
    const q = poseAt(p, t), d = p.dir ?? 1, s = (p.s ?? 1), col = colOverride || depthCol(env, p.depth), role = p.role || 'sage';
    const cutCol = env.sky ? rgb(mixA(env.sky[2], [255, 240, 210], 0.3)) : '#f0c080';
    const seed = (p.x || 0) * 37 + role.length, idle = p.walk ? 0 : 1;
    q.lean += idle * 1.6 * Math.sin(t * 0.8 + seed); q.head += idle * 2.2 * Math.sin(t * 0.55 + seed * 2);   // life: sway, head
    const breath = 1 + 0.016 * Math.sin(t * 1.5 + seed);
    ctx.translate(p.x * W, p.y * H - q.bob * s); ctx.scale(d * s, s);
    const hipY = -200 + q.seat * 128 + q.kneel * 60;
    ctx.translate(0, hipY);
    const robed = role === 'vasishtha', sari = role === 'dancer';
    const limb = (a1, a2, L1, L2, w, foot) => {
      ctx.save(); ctx.rotate(-a1 * D2R); capsule(ctx, L1, w, w * 0.78, col); ctx.translate(0, L1); ctx.rotate(-a2 * D2R); capsule(ctx, L2, w * 0.78, w * 0.55, col);
      if (foot) { ctx.translate(0, L2); cut(ctx, [[-12, -8], [16, -6], [36, 4], [37, 11], [-12, 11]], col); }
      ctx.restore();
    };
    // shoulder scarf trailing behind (drawn first, so it sits behind the body)
    if (p.scarf) { ctx.save(); ctx.rotate(q.lean * D2R); scarf(ctx, -30, -160, role === 'dancer' ? 200 : 170, 26, -1, t, seed, col); ctx.restore(); }
    // legs (far, then near) or a seated lap with knees and a foot
    if (q.seat > 0.5) {
      cut(ctx, [[-52, -8], [30, -16], [92, -2], [116, 22], [118, 46], [84, 64], [-40, 64], [-58, 30]], col);
      cut(ctx, [[60, 50], [96, 44], [112, 54], [70, 62]], col);
    } else if (!robed) {
      limb(q.tB, q.sB, 102, 98, 14, true);
      limb(q.th, q.sh, 104, 100, 15, true);
    } else {
      limb(q.tB, q.sB, 102, 98, 12, true); limb(q.th, q.sh, 104, 100, 12, true);
    }
    // upper body (lean pivots at the hip)
    ctx.save(); ctx.rotate(q.lean * D2R);
    ctx.save(); ctx.translate(-10, -156); limb(q.uB, q.fB, 74, 70, 10, false); ctx.restore();   // far arm
    ctx.save(); ctx.scale(1, breath);
    cut(ctx, [[-30, 8], [30, 8], [25, -40], [34, -108], [44, -148], [26, -166], [10, -174], [-12, -174], [-30, -164], [-42, -146], [-35, -108], [-26, -40]], col);   // waist, chest, shoulders
    ctx.restore();
    ctx.save(); ctx.translate(2, -170); capsule(ctx, 18, 11, 11, col); ctx.restore();   // neck
    const hemY = 190 - q.seat * 120 - q.kneel * 60;
    if (robed) {                    // a sage's robe from chest to ankle, hem rippling
      const w1 = Math.sin(t * 2.4 + seed) * 6, w2 = Math.sin(t * 2.4 + seed + 1.6) * 6;
      cut(ctx, [[-40, -150], [38, -150], [44, -40], [56, 90], [64, hemY + w1], [20, hemY + 6 + w2], [-24, hemY + w1], [-58, hemY + w2], [-50, 90], [-44, -40]], col);
    }
    if (sari) {                     // flaring sari, swinging with the dance
      const sw = Math.sin(t * 5 + seed) * 14;
      cut(ctx, [[-34, -30], [36, -30], [58, 60], [90 + sw, 170], [-74 + sw * 0.6, 172], [-50, 60]], col);
    }
    if (role === 'king' || role === 'soldier') { cut(ctx, [[-32, -12], [34, -12], [46, 88], [-40, 88]], col); if (role === 'king') lacework(ctx, 2, 36, 8, cutCol); }   // dhoti
    if (role === 'soldier') { cut(ctx, [[-36, -150], [-2, -170], [42, -150], [32, -60], [-30, -60]], col); circle(ctx, -18, -100, 40, col); lacework(ctx, -18, -100, 12, cutCol); }   // breastplate + round shield
    // head
    ctx.save(); ctx.translate(6, -186); ctx.rotate(q.head * D2R); ctx.scale(1.12, 1.12);
    cut(ctx, [[-18, 4], [16, 2], [20, -16], [36, -26], [31, -32], [33, -44], [22, -64], [-2, -72], [-22, -60], [-26, -30]], col);
    const beard = p.beard ?? (role === 'king' ? 0.25 : role === 'soldier' || role === 'dancer' ? 0 : 1);
    if (beard > 0) {
      const bw = Math.sin(t * 1.3 + seed) * 3 * beard;
      cut(ctx, [[0, -24], [30, -28], [28 + 4 * beard + bw, 6 + 30 * beard], [16 + bw, 22 + 50 * beard], [10 + bw * 1.5, 30 + 72 * beard], [0, 22 + 56 * beard], [-6, 18 + 40 * beard], [-8, -2]], col);
    }
    if (role === 'king' && p.crown !== undefined && !p.crown) {   // crown laid down: bare head, hair tied back
      circle(ctx, -12, -64, 16, col); cut(ctx, [[18, -22], [44, -30], [50, -40], [40, -24]], col);
    } else if (role === 'king') {  // tall crown (mukuta) with cut ornaments, curled moustache, earring
      cut(ctx, [[-26, -62], [24, -62], [22, -84], [14, -90], [18, -104], [8, -100], [4, -146], [-4, -100], [-14, -104], [-12, -90], [-22, -84]], col, true);
      lacework(ctx, 0, -78, 6, cutCol); circle(ctx, 4, -150, 6, col);
      cut(ctx, [[18, -22], [46, -30], [52, -42], [40, -24]], col);
      circle(ctx, -6, -14, 7, col);
    } else if (role === 'soldier') {
      cut(ctx, [[-28, -56], [26, -56], [16, -86], [0, -112], [-16, -86]], col, true);
    } else if (role === 'dancer') {
      circle(ctx, -18, -66, 20, col); for (let k = 0; k < 4; k++) circle(ctx, -32 + k * 9, -84 + Math.abs(k - 1.5) * 5, 5, col);   // bun with flowers
      circle(ctx, -4, -12, 6, col);
    } else if (role === 'ascetic') {
      const jt = 0.6 + 0.5 * (p.jata ?? 0.5); circle(ctx, -6, -80, 18 * jt, col); circle(ctx, -20, -70, 15 * jt, col); circle(ctx, 8, -76, 12 * jt, col);
      cut(ctx, [[-24, -60], [-14, -40], [-30, 40 * jt], [-46, 30 * jt], [-40, -50]], col);   // jata bun + locks down the back
    } else {                       // sage / vasishtha: topknot
      circle(ctx, -6, -82, 14, col);
    }
    ctx.restore();
    // near arm with props
    ctx.save(); ctx.translate(14, -156);
    ctx.save(); ctx.rotate(-q.uA * D2R); capsule(ctx, 76, 11, 9, col); if (role === 'king') { ctx.fillStyle = cutCol; ctx.fillRect(-9, 26, 18, 3); } ctx.translate(0, 76); ctx.rotate(-q.fA * D2R); capsule(ctx, 72, 9, 7, col);
    ctx.translate(0, 72); hand(ctx, col); ctx.translate(0, 4);
    if (p.sword) { ctx.save(); ctx.rotate(-0.4); cut(ctx, [[-4, -8], [4, -8], [6, 150], [0, 168], [-6, 150]], col, true); cut(ctx, [[-20, -4], [20, -4], [20, 4], [-20, 4]], col, true); ctx.restore(); }
    if (p.spear) { ctx.save(); ctx.rotate(p.spearAng ?? 2.9); cut(ctx, [[-3, -60], [3, -60], [3, 260], [-3, 260]], col, true); cut(ctx, [[-10, 260], [10, 260], [0, 300]], col, true); ctx.restore(); }
    if (p.staff) {
      const m = ctx.getTransform(); ctx.save(); ctx.rotate(Math.PI); cut(ctx, [[-5, -120], [5, -120], [5, 220], [-5, 220]], col, true); circle(ctx, 0, 226, 12, col); ctx.restore();
      env.staff = m.transformPoint(new DOMPoint(0, -226));
    }
    env.hand = ctx.getTransform().transformPoint(new DOMPoint(0, 0));
    ctx.restore(); ctx.restore();
    ctx.restore();   // lean
    if (!colOverride && p.headGlow > 0) { const m = ctx.getTransform(); const h = m.transformPoint(new DOMPoint(20, -230)); ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); glow(ctx, h.x, h.y, 220 * s * p.headGlow + 60, 'rgba(255,225,150,0.95)', p.headGlow); ctx.restore(); }
  }

  function figure(ctx, p, t, env) {
    if ((p.depth ?? 0) < 0.35 && env.light) {
      const m = ctx.getTransform(), o = m.transformPoint(new DOMPoint(p.x * W, p.y * H - 200 * (p.s ?? 1))), dx = env.light.x - o.x, dy = env.light.y - o.y, L = Math.hypot(dx, dy) || 1;
      const rim = env.sky ? rgb(mixA(env.sky[2], [255, 238, 205], 0.6)) : '#ffdca8', k = 4 * (p.s ?? 1);
      ctx.save(); ctx.setTransform(1, 0, 0, 1, k * dx / L, k * dy / L); ctx.transform(m.a, m.b, m.c, m.d, m.e, m.f);
      drawFigure(ctx, p, t, env, rim); ctx.restore();   // no canvas blur: it is very slow without a GPU
    }
    ctx.save(); drawFigure(ctx, p, t, env); ctx.restore();
  }

  // ---------- elements ----------
  const el = {};
  el.sky = (ctx, p, t, env) => {
    const pal = skyPal(p); env.sky = pal; const hz = (p.horizon ?? 0.68) * H;
    { const m = ctx.getTransform(), o = m.transformPoint(new DOMPoint(W / 2, hz * 0.85)); env.light = { x: o.x, y: o.y }; }
    const g = ctx.createLinearGradient(0, -H * 0.3, 0, hz);
    g.addColorStop(0, rgb(pal[0])); g.addColorStop(0.55, rgb(pal[1])); g.addColorStop(1, rgb(pal[2]));
    ctx.fillStyle = g; ctx.fillRect(-W, -H, 3 * W, hz + H);
    ctx.fillStyle = rgb(mixA(pal[2], hex(SIL), 0.55)); ctx.fillRect(-W, hz, 3 * W, 2 * H);
    if ((p.dark || 0) > 0) { ctx.save(); ctx.globalAlpha = clamp(p.dark, 0, 0.92); ctx.fillStyle = '#02030a'; ctx.fillRect(-W, -H, 3 * W, 3 * H); ctx.restore(); }
    if ((p.flash || 0) > 0) { ctx.save(); ctx.globalAlpha = clamp(p.flash, 0, 1); ctx.fillStyle = '#f2ecff'; ctx.fillRect(-W, -H, 3 * W, 3 * H); ctx.restore(); }
  };
  el.sun = (ctx, p, t, env) => {
    const x = p.x * W, y = p.y * H, r = (p.r ?? 70) * (p.s ?? 1), a = p.a ?? 1; if (a <= 0) return;
    { const o = ctx.getTransform().transformPoint(new DOMPoint(x, y)); env.light = { x: o.x, y: o.y }; }
    glow(ctx, x, y, r * 7, 'rgba(255,214,140,0.85)', 0.75 * a * (p.glow ?? 1));
    ctx.save(); ctx.globalAlpha = a; circle(ctx, x, y, r, p.color || '#fff1c8'); ctx.restore();
  };
  el.moon = (ctx, p) => {
    const x = p.x * W, y = p.y * H, r = 46 * (p.s ?? 1); if ((p.a ?? 1) <= 0) return;
    glow(ctx, x, y, r * 4, 'rgba(220,230,255,0.6)', 0.6 * (p.a ?? 1));
    ctx.save(); ctx.globalAlpha = p.a ?? 1; ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.arc(x + r * 0.4, y - r * 0.1, r * 0.85, 0, Math.PI * 2, true); ctx.fillStyle = '#f2f0ff'; ctx.fill('evenodd'); ctx.restore();
  };
  el.stars = (ctx, p, t) => {
    const R = rng(p.seed || 3), a = p.a ?? 1; if (a <= 0) return;
    for (let i = 0; i < (p.n || 160); i++) {
      const x = R() * W * 1.4 - W * 0.2, y = R() * H * (p.band ?? 0.6) - H * 0.1, tw = 0.5 + 0.5 * Math.sin(t * (1 + R() * 2) + R() * 6);
      ctx.globalAlpha = a * (0.3 + 0.7 * tw); circle(ctx, x, y, 0.8 + R() * 1.8, '#fff8e8');
    }
    ctx.globalAlpha = 1;
  };
  el.mountains = (ctx, p, t, env) => {
    const R = rng(p.seed || 5), y0 = p.y * H, pts = [[-W * 0.4, H * 1.5]];
    for (let x = -W * 0.4; x <= W * 1.4; x += 90) pts.push([x, y0 - (p.h ?? 160) * (0.4 + 0.6 * Math.abs(Math.sin(x / (p.w ?? 380) + (p.seed || 5)))) - R() * 20]);
    pts.push([W * 1.4, H * 1.5]);
    cut(ctx, pts, depthCol(env, p.depth ?? 0.6), true);
  };
  el.ground = (ctx, p, t, env) => {          // near ground strip with grass blades swaying
    const y0 = p.y * H, col = depthCol(env, p.depth ?? 0), R = rng(p.seed || 7);
    ctx.fillStyle = col; ctx.beginPath(); ctx.moveTo(-W, H * 2); for (let x = -W; x <= 2 * W; x += 120) ctx.lineTo(x, y0 + Math.sin(x / 300 + (p.seed || 1)) * (p.wave ?? 14)); ctx.lineTo(2 * W, H * 2); ctx.fill();
    if (p.grass !== false) for (let i = 0; i < 160; i++) {
      const x = R() * W * 1.4 - W * 0.2, h = 20 + R() * 46, sw = Math.sin(t * 1.6 + x / 140) * 6;
      ctx.beginPath(); ctx.moveTo(x - 3, y0 + 6); ctx.quadraticCurveTo(x + sw * 0.5, y0 - h * 0.5, x + sw, y0 - h); ctx.quadraticCurveTo(x + sw * 0.5 + 2, y0 - h * 0.5, x + 3, y0 + 6); ctx.fill();
    }
  };
  el.river = (ctx, p, t, env) => {
    const y0 = p.y * H, pal = env.sky || [[0, 0, 0], [60, 60, 80], [200, 150, 100]];
    const g = ctx.createLinearGradient(0, y0, 0, y0 + H * 0.4); g.addColorStop(0, rgb(mixA(pal[2], hex(SIL), 0.25))); g.addColorStop(1, rgb(mixA(pal[1], hex(SIL), 0.7)));
    ctx.fillStyle = g; ctx.fillRect(-W, y0, 3 * W, H);
    ctx.save(); ctx.globalAlpha = 0.5; ctx.strokeStyle = rgb(mixA(pal[2], [255, 255, 255], 0.4)); ctx.lineWidth = 3;
    for (let k = 0; k < 9; k++) { const yy = y0 + 14 + k * k * 6, sp = 40 + k * 12; ctx.beginPath(); for (let x = -W * 0.2; x < W * 1.2; x += 30) { const v = yy + Math.sin((x + t * sp) / (60 + k * 10)) * (2 + k); x === -W * 0.2 ? ctx.moveTo(x, v) : ctx.lineTo(x, v); } ctx.globalAlpha = 0.45 - k * 0.04; ctx.stroke(); }
    ctx.restore();
  };
  el.tree = (ctx, p, t, env) => {            // banyan / forest tree with paper-cut leaf lace
    const col = depthCol(env, p.depth), s = p.s ?? 1, R = rng(p.seed || 11), sw = Math.sin(t * 0.7 + (p.seed || 1)) * 0.012;
    ctx.translate(p.x * W, p.y * H); ctx.scale((p.dir ?? 1) * s, s); ctx.rotate(sw);
    cut(ctx, [[-34, 0], [34, 0], [26, -120], [60, -230], [40, -236], [10, -150], [-10, -150], [-50, -250], [-66, -240], [-26, -120]], col);
    for (let i = 0; i < 14; i++) { const a = -Math.PI / 2 + (R() - 0.5) * 2.4, rr = 120 + R() * 110; circle(ctx, Math.cos(a) * rr * 1.25, -260 + Math.sin(a) * rr * 0.55, 70 + R() * 50, col); }
    for (let i = 0; i < (p.roots ?? 5); i++) { const x = -160 + i * 80 + R() * 20; ctx.fillRect(x, -300 + R() * 40, 4, 300); }   // aerial roots
    const lace = env.sky ? rgb(mixA(env.sky[2], [255, 240, 210], 0.2)) : '#d89a60';
    for (let i = 0; i < 9; i++) { ctx.globalAlpha = 0.7; lacework(ctx, (R() - 0.5) * 300, -300 + (R() - 0.5) * 120, 7 + R() * 5, lace); } ctx.globalAlpha = 1;
  };
  el.palm = (ctx, p, t, env) => {
    const col = depthCol(env, p.depth), s = p.s ?? 1;
    ctx.translate(p.x * W, p.y * H); ctx.scale((p.dir ?? 1) * s, s);
    cut(ctx, [[-10, 0], [10, 0], [24, -150], [40, -300], [28, -302], [6, -150]], col);
    for (let i = 0; i < 8; i++) { ctx.save(); ctx.translate(34, -300); ctx.rotate(-1.5 + i * 0.42 + Math.sin(t * 0.8) * 0.04); cut(ctx, [[0, -6], [90, -24], [200, 14], [90, 8], [0, 8]], col); ctx.restore(); }
  };
  el.palace = (ctx, p, t, env) => {
    const col = depthCol(env, p.depth), s = p.s ?? 1, lace = env.sky ? rgb(mixA(env.sky[2], [255, 230, 190], 0.25)) : '#f0b070';
    ctx.translate(p.x * W, p.y * H); ctx.scale(s, s);
    cut(ctx, [[-320, 0], [-320, -170], [320, -170], [320, 0]], col, true);
    for (const [x, h] of [[-260, 300], [-120, 250], [0, 380], [120, 250], [260, 300]]) {
      cut(ctx, [[x - 50, -160], [x - 50, -h + 80], [x - 36, -h + 40], [x, -h], [x + 36, -h + 40], [x + 50, -h + 80], [x + 50, -160]], col);
      ctx.fillRect(x - 2, -h - 70, 4, 72); cut(ctx, [[x + 2, -h - 70], [x + 52 + 10 * Math.sin(t * 4 + x), -h - 58], [x + 2, -h - 44]], col, true);   // flag
    }
    for (let i = 0; i < 9; i++) { ctx.fillStyle = lace; ctx.beginPath(); ctx.ellipse(-280 + i * 70, -90, 13, 26, 0, Math.PI, 0); ctx.rect(-293 + i * 70, -90, 26, 30); ctx.fill(); }   // lit arches
  };
  el.hut = (ctx, p, t, env) => {
    const col = depthCol(env, p.depth), s = p.s ?? 1;
    ctx.translate(p.x * W, p.y * H); ctx.scale(s, s);
    cut(ctx, [[-130, 0], [-130, -110], [130, -110], [130, 0]], col, true);
    cut(ctx, [[-170, -100], [0, -230], [170, -100]], col, true);
    ctx.fillStyle = env.sky ? rgb(mixA(env.sky[2], [255, 200, 120], 0.5)) : '#e8a050'; ctx.fillRect(-30, -90, 60, 90);   // lit door
    if ((p.smoke ?? 1) > 0) for (let i = 0; i < 6; i++) { const u = ((t * 0.15 + i / 6) % 1); ctx.globalAlpha = 0.25 * (1 - u); circle(ctx, 90 + Math.sin(u * 6 + i) * 20, -230 - u * 260, 16 + u * 40, col); } ctx.globalAlpha = 1;
  };
  el.cow = (ctx, p, t, env) => {             // Nandinī: a zebu cow with a hump, horns and a swishing tail
    const col = depthCol(env, p.depth), s = p.s ?? 1, d = p.dir ?? 1;
    if ((p.glow || 0) > 0) { glow(ctx, p.x * W, p.y * H - 150 * s, 420 * s, 'rgba(255,236,190,0.95)', p.glow); rays(ctx, p.x * W, p.y * H - 150 * s, 24, 520 * s, p.glow * 0.5, t * 0.15); }
    ctx.translate(p.x * W, p.y * H); ctx.scale(d * s, s);
    const ph = t * 1.4 * Math.PI * 2 * (p.walk || 0);
    for (const [x, o] of [[-118, 0], [-90, 1], [96, 1], [122, 0]]) { ctx.save(); ctx.translate(x, -140); ctx.rotate(Math.sin(ph + o * Math.PI) * 0.3 * (p.walk || 0)); capsule(ctx, 70, 11, 7, col); ctx.translate(0, 70); ctx.rotate(o ? 0.12 : -0.08); capsule(ctx, 66, 6, 5, col); cut(ctx, [[-8, 62], [9, 62], [10, 72], [-8, 72]], col, true); ctx.restore(); }
    cut(ctx, [[-178, -150], [-150, -205], [-40, -212], [40, -214], [62, -262], [96, -268], [118, -238], [150, -212], [170, -170], [140, -122], [60, -110], [-40, -112], [-150, -120]], col);   // body, hump, belly
    cut(ctx, [[140, -214], [186, -232], [222, -214], [252, -160], [262, -128], [240, -118], [214, -146], [170, -160]], col);   // neck + long head
    cut(ctx, [[200, -226], [186, -270], [176, -290], [192, -288], [212, -232]], col); cut(ctx, [[214, -222], [232, -262], [246, -276], [250, -262], [226, -216]], col);   // lyre horns
    cut(ctx, [[192, -214], [168, -204], [176, -196], [200, -204]], col);   // ear
    cut(ctx, [[150, -170], [196, -150], [190, -112], [164, -124]], col);   // dewlap
    ctx.save(); ctx.translate(-172, -190); ctx.rotate(0.25 + Math.sin(t * 2.2) * 0.25); capsule(ctx, 130, 4, 3, col); cut(ctx, [[-8, 124], [8, 124], [4, 150], [-4, 150]], col); ctx.restore();
  };
  el.horse = (ctx, p, t, env) => {           // horse with the king riding
    const col = depthCol(env, p.depth), s = p.s ?? 1, d = p.dir ?? 1, w = p.walk ?? 1, ph = t * 1.6 * Math.PI * 2;
    ctx.save(); ctx.translate(p.x * W, p.y * H - Math.abs(Math.sin(ph)) * 6 * w); ctx.scale(d * s, s);
    for (const [x, o] of [[-118, 0], [-92, 1], [104, 1], [128, 0]]) { ctx.save(); ctx.translate(x, -200); ctx.rotate(Math.sin(ph + o * Math.PI) * 0.42 * w); capsule(ctx, 100, 12, 8, col); ctx.translate(0, 100); ctx.rotate(-Math.max(0, Math.sin(ph + o * Math.PI - 1)) * 0.7 * w * (o ? 1 : -1)); capsule(ctx, 96, 7, 5, col); cut(ctx, [[-9, 92], [11, 92], [12, 104], [-9, 104]], col, true); ctx.restore(); }
    cut(ctx, [[-170, -230], [-130, -280], [-20, -288], [110, -290], [170, -262], [160, -205], [60, -190], [-60, -192], [-150, -200]], col);   // barrel
    cut(ctx, [[110, -280], [150, -350], [176, -400], [206, -420], [254, -398], [262, -372], [236, -366], [214, -370], [196, -330], [168, -262]], col);   // neck + head
    cut(ctx, [[196, -412], [194, -436], [206, -418]], col, true);   // ear
    for (let k = 0; k < 7; k++) cut(ctx, [[120 + k * 11, -300 - k * 15], [100 + k * 11 + Math.sin(t * 5 + k) * 7, -306 - k * 16], [128 + k * 11, -312 - k * 15]], col, true);   // mane
    ctx.save(); ctx.translate(-168, -260); ctx.rotate(0.5 + Math.sin(t * 3) * 0.12); cut(ctx, [[-8, 0], [10, 0], [26, 150], [0, 166], [-22, 150]], col); ctx.restore();   // tail
    ctx.restore();
    const rs = s * 0.8, bob = Math.abs(Math.sin(ph)) * 6 * w * s;
    figure(ctx, Object.assign({}, p, { role: p.rider || 'king', pose: 'ride', walk: 0, x: p.x - (10 * d * s) / W, y: p.y + (-276 * s + 200 * rs - bob) / H, s: rs }), t, env);
    ctx.save(); ctx.translate(p.x * W, p.y * H - bob); ctx.scale(d * s, s); const col2 = depthCol(env, p.depth);
    cut(ctx, [[-60, -292], [40, -292], [52, -250], [30, -214], [-50, -214], [-70, -250]], col2); ctx.restore();   // saddle cloth over the rider's far side
  };
  el.figure = figure;
  el.army = (ctx, p, t, env) => {            // a marching column of soldiers with spears and banners
    const n = p.n || 8;
    for (let i = 0; i < n; i++) {
      const row = i % 2, x = (p.x ?? 0.5) - i * (p.gap ?? 0.07) * (p.dir ?? 1);
      ctx.save(); figure(ctx, { role: 'soldier', x, y: (p.y ?? 0.8) - row * 0.03, s: (p.s ?? 0.5) * (1 - row * 0.12), dir: p.dir ?? 1, walk: p.walk ?? 1, pace: 1.5, spear: 1, spearAng: 2.95, depth: (p.depth ?? 0) + row * 0.25, pose: p.pose, poseTo: p.poseTo, poseMix: p.poseMix }, t + i * 0.23, env); ctx.restore();
      if (i % 3 === 1) { ctx.save(); const col = depthCol(env, (p.depth ?? 0) + row * 0.25), bx = x * W + 10, by = (p.y ?? 0.8) * H - 380 * (p.s ?? 0.5); ctx.fillStyle = col; ctx.fillRect(bx, by, 5, 300 * (p.s ?? 0.5) * 1.4); cut(ctx, [[bx + 5, by], [bx + 80 + 8 * Math.sin(t * 5 + i), by + 20], [bx + 5, by + 46]], col, true); ctx.restore(); }
    }
  };
  function rays(ctx, x, y, n, L, a, rot) {
    if (a <= 0) return;
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.translate(x, y); ctx.rotate(rot || 0);
    for (let i = 0; i < n; i++) { ctx.rotate(Math.PI * 2 / n); const g = ctx.createLinearGradient(0, 0, L, 0); g.addColorStop(0, `rgba(255,232,170,${0.55 * a})`); g.addColorStop(1, 'rgba(255,232,170,0)'); ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(0, -6); ctx.lineTo(L, -L * 0.05); ctx.lineTo(L, L * 0.05); ctx.lineTo(0, 6); ctx.fill(); }
    ctx.restore();
  }
  el.rays = (ctx, p, t) => rays(ctx, p.x * W, p.y * H, p.n || 18, (p.len ?? 700) * (p.s ?? 1), p.a ?? 1, (p.rot ?? 0) + t * (p.spin ?? 0.05));
  el.arrows = (ctx, p, t, env) => {          // a volley that vanishes into sparks at the target
    const v = p.v ?? 0, n = p.n || 14, R = rng(13), col = depthCol(env, 0); if (v <= 0) return;
    const tx = p.tx * W, ty = p.ty * H;
    for (let i = 0; i < n; i++) {
      const delay = R() * 0.45, u = clamp((v - delay) / 0.55, 0, 1), sx = (p.sx ?? -0.05) * W, sy = (p.sy ?? 0.5) * H + (R() - 0.5) * 260;
      if (u <= 0) continue;
      const x = lerp(sx, tx, u), y = lerp(sy, ty + (R() - 0.5) * 60, u) - Math.sin(u * Math.PI) * 120;
      if (u >= 1) { glow(ctx, tx + (R() - 0.5) * 80, ty + (R() - 0.5) * 80, 60, 'rgba(255,240,200,0.9)', clamp(1 - (v - delay - 0.55) * 4, 0, 1)); continue; }
      const ang = Math.atan2(ty - sy - Math.cos(u * Math.PI) * 120 * Math.PI * -0.5, tx - sx);
      ctx.save(); ctx.translate(x, y); ctx.rotate(ang); ctx.fillStyle = col; ctx.fillRect(-60, -2, 60, 4); cut(ctx, [[0, -7], [18, 0], [0, 7]], col, true); cut(ctx, [[-60, 0], [-72, -9], [-52, 0], [-72, 9]], col, true); ctx.restore();
    }
  };
  el.shield = (ctx, p, t) => {               // the sage's staff: a sphere of light that swallows the weapons
    const a = p.a ?? 0, x = p.x * W, y = p.y * H, r = (p.r ?? 220); if (a <= 0) return;
    glow(ctx, x, y, r * 1.8, 'rgba(255,246,214,0.95)', a);
    ctx.save(); ctx.globalAlpha = a * 0.8; ctx.strokeStyle = '#fff6d8'; ctx.lineWidth = 3;
    for (let k = 0; k < 3; k++) { ctx.beginPath(); ctx.arc(x, y, r * (0.6 + k * 0.22) + Math.sin(t * 3 + k) * 6, 0, Math.PI * 2); ctx.stroke(); } ctx.restore();
    rays(ctx, x, y, 28, r * 1.6, a * 0.8, t * 0.4);
  };
  el.crown = (ctx, p, t, env) => {
    const col = depthCol(env, 0), s = p.s ?? 1; ctx.translate(p.x * W, p.y * H); ctx.scale(s, s); ctx.globalAlpha = p.a ?? 1;
    cut(ctx, [[-90, 0], [90, 0], [70, -60], [-70, -60]], col);                       // rock
    cut(ctx, [[-30, -60], [30, -60], [26, -100], [12, -96], [4, -140], [-4, -96], [-16, -100]], col, true); circle(ctx, 4, -146, 7, col);
    if ((p.gleam || 0) > 0) glow(ctx, 0, -110, 120, 'rgba(255,220,150,0.9)', p.gleam);
  };
  el.rain = (ctx, p, t) => {
    const a = p.a ?? 0; if (a <= 0) return; const R = rng(17);
    ctx.save(); ctx.strokeStyle = 'rgba(210,220,240,0.55)'; ctx.lineWidth = 2; ctx.globalAlpha = a;
    for (let i = 0; i < 260; i++) { const x = R() * W * 1.3 - W * 0.15, y = ((R() * H * 1.4 + t * 900) % (H * 1.4)) - H * 0.2; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x - 10, y + 40); ctx.stroke(); }
    ctx.restore();
  };
  el.leaves = (ctx, p, t, env) => {          // falling leaves: time passing
    const a = p.a ?? 0; if (a <= 0) return; const R = rng(19), col = depthCol(env, 0);
    ctx.save(); ctx.globalAlpha = a;
    for (let i = 0; i < 40; i++) { const x = (R() * W * 1.2 + Math.sin(t + i) * 60) - W * 0.1, y = ((R() * H + t * (60 + R() * 60)) % H); ctx.save(); ctx.translate(x, y); ctx.rotate(t * 2 + i); cut(ctx, [[0, -10], [7, 0], [0, 10], [-7, 0]], col); ctx.restore(); }
    ctx.restore();
  };
  el.birds = (ctx, p, t, env) => {
    const f = p.fly ?? 0, n = p.n || 7, col = depthCol(env, p.depth ?? 0.2); if (f <= 0) return;
    for (let i = 0; i < n; i++) {
      const u = clamp(f * 1.3 - i * 0.04, 0, 1), x = lerp(p.x0 ?? -0.1, p.x1 ?? 1.1, u) * W + (i % 3) * 40, y = (p.y ?? 0.3) * H + Math.sin(u * 5 + i) * 30 + (i % 4) * 30, fl = Math.sin(t * 8 + i) * 18, s = p.s ?? 1;
      ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.fillStyle = col; ctx.beginPath(); ctx.moveTo(-36, -fl); ctx.quadraticCurveTo(-14, -6, 0, 4); ctx.quadraticCurveTo(14, -6, 36, -fl); ctx.quadraticCurveTo(14, 2, 0, 10); ctx.quadraticCurveTo(-14, 2, -36, -fl); ctx.fill(); ctx.restore();
    }
  };

  // ---------- geometry finale ----------
  const GOLD = '255,214,140';
  function ringPath(ctx, x, y, r, n, amp, rot) { ctx.beginPath(); for (let i = 0; i <= 360; i += 2) { const a = i * D2R, rr = r + amp * Math.cos(n * a + rot); const px = x + Math.cos(a) * rr, py = y + Math.sin(a) * rr; i ? ctx.lineTo(px, py) : ctx.moveTo(px, py); } ctx.closePath(); }
  el.mandala = (ctx, p, t) => {              // petals unfold ring by ring (draw 0..1), slow rotation
    const x = (p.x ?? 0.5) * W, y = (p.y ?? 0.5) * H, R = (p.r ?? 420) * (p.s ?? 1), a = p.a ?? 1, dr = p.draw ?? 1; if (a <= 0) return;
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    for (let ring = 0; ring < 5; ring++) {
      const u = clamp(dr * 5 - ring, 0, 1); if (u <= 0) continue;
      const rr = R * (0.25 + ring * 0.18), n = 8 + ring * 4, rot = t * (ring % 2 ? -0.06 : 0.05) + ring;
      ctx.strokeStyle = `rgba(${GOLD},${0.75 * a * u})`; ctx.lineWidth = 2.4;
      for (let i = 0; i < n * u; i++) {
        const ang = rot + i * Math.PI * 2 / n; ctx.save(); ctx.translate(x, y); ctx.rotate(ang);
        ctx.beginPath(); ctx.moveTo(rr * 0.82, 0); ctx.quadraticCurveTo(rr * 1.02, -rr * 0.18 * (6 / n), rr * 1.18, 0); ctx.quadraticCurveTo(rr * 1.02, rr * 0.18 * (6 / n), rr * 0.82, 0); ctx.stroke(); ctx.restore();
      }
      ctx.strokeStyle = `rgba(${GOLD},${0.35 * a * u})`; ctx.setLineDash([3, 9]); ringPath(ctx, x, y, rr * 0.8, n, 0, 0); ctx.stroke(); ctx.setLineDash([]);
    }
    ctx.restore();
    glow(ctx, x, y, R * 0.9, `rgba(${GOLD},0.8)`, 0.35 * a * (p.pulse ?? 1));
  };
  el.yantra = (ctx, p, t) => {               // hexagram of the sun inside circles; lines draw themselves
    const x = (p.x ?? 0.5) * W, y = (p.y ?? 0.5) * H, R = (p.r ?? 330) * (p.s ?? 1), dr = clamp(p.draw ?? 1, 0, 1), a = p.a ?? 1, pu = p.pulse ?? 0; if (a <= 0) return;
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.lineWidth = 3 + 3 * pu; ctx.strokeStyle = `rgba(255,226,160,${a})`; ctx.shadowColor = `rgba(${GOLD},0.9)`; ctx.shadowBlur = 18 + 30 * pu;
    const seg = (pts, from, to) => { const L = pts.length; ctx.beginPath(); for (let i = 0; i <= L; i++) { const k = i / L; if (k < from) continue; if (k > to) break; const q = pts[i % L]; ctx.lineTo(q[0], q[1]); } ctx.stroke(); };
    const tri = (r, rot) => [0, 1, 2].map(i => [x + Math.cos(rot + i * 2 * Math.PI / 3) * r, y + Math.sin(rot + i * 2 * Math.PI / 3) * r]);
    const circ = (r) => Array.from({ length: 72 }, (_, i) => [x + Math.cos(i * 5 * D2R) * r, y + Math.sin(i * 5 * D2R) * r]);
    const parts = [circ(R * 1.18), tri(R, -Math.PI / 2), tri(R, Math.PI / 2), circ(R * 0.5), tri(R * 0.5, -Math.PI / 2), tri(R * 0.5, Math.PI / 2), circ(R * 0.16)];
    parts.forEach((pts, i) => { const u = clamp(dr * parts.length - i, 0, 1); if (u > 0) seg(pts, 0, u); });
    ctx.restore();
    if (dr >= 1) glow(ctx, x, y, R * 0.6, 'rgba(255,240,200,0.9)', 0.4 + 0.6 * pu);
  };
  el.worlds = (ctx, p, t) => {               // bhūr, bhuvaḥ, svaḥ: three concentric rings light in turn
    const x = (p.x ?? 0.5) * W, y = (p.y ?? 0.46) * H, s = p.s ?? 1;
    const ring = (v, r, col, n) => { if (v <= 0) return; ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.strokeStyle = `rgba(${col},${0.85 * v})`; ctx.lineWidth = 4; ctx.shadowColor = `rgba(${col},1)`; ctx.shadowBlur = 26; ringPath(ctx, x, y, r * s, n, 7, t * 0.6); ctx.stroke(); ctx.restore(); glow(ctx, x, y, r * s * 1.2, `rgba(${col},0.6)`, 0.25 * v * clamp(v * (1 - v) * 4 + 0.4, 0, 1)); };
    ring(p.earth ?? 0, 170, '170,220,120', 9); ring(p.sky ?? 0, 290, '140,190,255', 13); ring(p.heaven ?? 0, 410, '255,236,180', 17);
  };
  el.word = (ctx, p, t) => {                 // the sung word of a unit, written in light, scaled to fit
    const U = VAK.units()[(p.unit || 1) - 1]; if (!U) return; const a0 = p.a ?? 1; if (a0 <= 0) return;
    let w = null, k = -1;
    U.words.forEach((x, i) => { if (t >= x.start - 0.15 && t < x.end + 0.25) { w = x; k = i; } });
    if (!w && p.text) w = { dev: p.text, start: VAK.at({ u: p.unit || 1 }), end: VAK.at({ u: p.unit || 1, e: 'end' }) };
    if (!w) return;
    const u = clamp((t - w.start + 0.15) / 0.5, 0, 1), out = clamp((w.end + 0.25 - t) / 0.35, 0, 1), a = a0 * Math.min(u, out);
    const x = (p.x ?? 0.5) * W, y = (p.y ?? 0.42) * H, size = (p.size ?? 150) * (0.9 + 0.1 * u);
    ctx.save(); ctx.font = `${size}px "Tiro Devanagari Sanskrit"`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = a; ctx.shadowColor = `rgba(${GOLD},1)`; ctx.shadowBlur = 40; ctx.fillStyle = '#fff1cc';
    ctx.fillText(w.dev, x, y); ctx.shadowBlur = 10; ctx.fillText(w.dev, x, y); ctx.restore();
    const R = rng(29 + k); for (let i = 0; i < 40; i++) { const ang = R() * Math.PI * 2, rr = size * (0.6 + R() * 1.4) * (1.2 - u * 0.4); glow(ctx, x + Math.cos(ang + t * 0.3) * rr, y + Math.sin(ang + t * 0.3) * rr * 0.6, 10, `rgba(${GOLD},0.9)`, a * 0.5 * R()); }
  };
  el.beam = (ctx, p, t) => {                 // light descending from above into the seer's mind
    const a = p.a ?? 0; if (a <= 0) return; const x = p.x * W, y0 = (p.y0 ?? -0.1) * H, y1 = p.y1 * H;
    const g = ctx.createLinearGradient(0, y0, 0, y1); g.addColorStop(0, 'rgba(255,240,200,0)'); g.addColorStop(1, `rgba(255,240,200,${0.8 * a})`);
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(x - 260, y0); ctx.lineTo(x + 260, y0); ctx.lineTo(x + 16, y1); ctx.lineTo(x - 16, y1); ctx.fill(); ctx.restore();
    glow(ctx, x, y1, 160, 'rgba(255,240,200,1)', a);
  };
  el.point = (ctx, p, t) => { const a = p.a ?? 0; glow(ctx, (p.x ?? 0.5) * W, (p.y ?? 0.5) * H, (p.r ?? 200), 'rgba(255,244,214,1)', a); };

  // ---------- cast: characters designed for this chant (vak/cast.py), drawn on the shared skeleton ----------
  // Each part is an SVG path in its own pivot frame (figure faces right, y down); poses, walk and sway come from POSES.
  const CAST_CACHE = {};
  function castParts(id) {
    if (CAST_CACHE[id]) return CAST_CACHE[id];
    const c = ((window.VAK_DATA && VAK_DATA.plan && VAK_DATA.plan.cast) || {})[id];
    if (!c) return null;
    const P = {};
    for (const k of ['back', 'torso', 'head', 'upper_arm', 'forearm', 'held', 'thigh', 'shin', 'lower', 'lap']) {
      const part = c[k] || {};
      try { P[k] = { d: part.d ? new Path2D(part.d) : null, cut: part.cut ? new Path2D(part.cut) : null }; } catch (e) { P[k] = { d: null, cut: null }; }
    }
    return (CAST_CACHE[id] = P);
  }
  function drawCast(ctx, p, t, env, colOverride) {
    const P = castParts(p.id); if (!P) return;
    const q = poseAt(p, t), d = p.dir ?? 1, s = (p.s ?? 1), col = colOverride || depthCol(env, p.depth);
    const cutCol = colOverride || (env.sky ? rgb(mixA(env.sky[2], [255, 240, 210], 0.3)) : '#f0c080');
    const seed = (p.x || 0) * 37 + (p.id || '').length, idle = p.walk ? 0 : 1;
    q.lean += idle * 1.6 * Math.sin(t * 0.8 + seed); q.head += idle * 2.2 * Math.sin(t * 0.55 + seed * 2);
    const breath = 1 + 0.016 * Math.sin(t * 1.5 + seed);
    const fill = part => { if (!part || !part.d) return false; ctx.fillStyle = col; ctx.fill(part.d); if (part.cut) { ctx.fillStyle = cutCol; ctx.fill(part.cut); } return true; };
    ctx.translate(p.x * W, p.y * H - q.bob * s); ctx.scale(d * s, s);
    ctx.translate(0, -200 + q.seat * 128 + q.kneel * 60);                       // hip
    const leg = (a1, a2) => { ctx.save(); ctx.rotate(-a1 * D2R); if (!fill(P.thigh)) capsule(ctx, 104, 15, 12, col);
      ctx.translate(0, 104); ctx.rotate(-a2 * D2R); if (!fill(P.shin)) capsule(ctx, 100, 12, 8, col); ctx.restore(); };
    const arm = (x, a1, a2, near) => { ctx.save(); ctx.translate(x, -156); ctx.rotate(-a1 * D2R); if (!fill(P.upper_arm)) capsule(ctx, 76, 11, 9, col);
      ctx.translate(0, 76); ctx.rotate(-a2 * D2R); if (!fill(P.forearm)) { capsule(ctx, 72, 9, 7, col); ctx.translate(0, 72); hand(ctx, col); ctx.translate(0, -72); }
      if (near) { ctx.translate(0, 76); fill(P.held); env.hand = ctx.getTransform().transformPoint(new DOMPoint(0, 0)); }
      ctx.restore(); };
    ctx.save(); ctx.rotate(q.lean * D2R); fill(P.back); ctx.restore();            // long hair, a trailing shawl
    if (q.seat > 0.5) { if (!fill(P.lap)) cut(ctx, [[-52, -8], [30, -16], [92, -2], [116, 22], [118, 46], [84, 64], [-40, 64], [-58, 30]], col); }
    else { leg(q.tB, q.sB); leg(q.th, q.sh); if (q.kneel < 0.5) fill(P.lower); }
    ctx.save(); ctx.rotate(q.lean * D2R);
    arm(-10, q.uB, q.fB, false);                                                   // far arm
    ctx.save(); ctx.scale(1, breath); fill(P.torso); ctx.restore();
    ctx.save(); ctx.translate(6, -186); ctx.rotate(q.head * D2R); fill(P.head); ctx.restore();
    arm(14, q.uA, q.fA, true);                                                     // near arm, holding its object
    ctx.restore();
    if (!colOverride && p.headGlow > 0) { const m = ctx.getTransform(); const h = m.transformPoint(new DOMPoint(20, -230)); ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); glow(ctx, h.x, h.y, 220 * s * p.headGlow + 60, 'rgba(255,225,150,0.9)', 0.55 * p.headGlow); ctx.restore(); }
  }
  el.cast = (ctx, p, t, env) => {
    if ((p.depth ?? 0) < 0.35 && env.light) {                                      // the same rim light as the built-in figures
      const m = ctx.getTransform(), o = m.transformPoint(new DOMPoint(p.x * W, p.y * H - 200 * (p.s ?? 1))), dx = env.light.x - o.x, dy = env.light.y - o.y, L = Math.hypot(dx, dy) || 1;
      const rim = env.sky ? rgb(mixA(env.sky[2], [255, 238, 205], 0.6)) : '#ffdca8', k = 4 * (p.s ?? 1);
      ctx.save(); ctx.setTransform(1, 0, 0, 1, k * dx / L, k * dy / L); ctx.transform(m.a, m.b, m.c, m.d, m.e, m.f); drawCast(ctx, p, t, env, rim); ctx.restore();
    }
    ctx.save(); drawCast(ctx, p, t, env); ctx.restore();
  };

  window.STYLE = {
    name: 'silhouette', el, fadeColor: '#030208',
    post(ctx, t) {                            // paper grain + soft vignette
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      const g = ctx.createRadialGradient(W / 2, H * 0.48, H * 0.4, W / 2, H / 2, W * 0.72);
      g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,0.55)'); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    },
  };
})();
