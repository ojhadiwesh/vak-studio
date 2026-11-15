// Style: shadow puppets (tholu bommalata). Backlit cloth screen, translucent coloured leather
// figures with dark outlines and punched holes, jointed limbs on rivets, rods to the bottom edge.
(function () {
  const { W, H, clamp, lerp, rng, noise1 } = VAK;
  const OUT = '#1a0a03';
  const HOLE = 'rgba(255,238,196,0.9)';
  let TEX = null;

  // ---------- drawing helpers ----------
  function smooth(ctx, pts, closed = true) {
    ctx.beginPath();
    if (!closed) { ctx.moveTo(pts[0][0], pts[0][1]); }
    const n = pts.length, m = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
    if (closed) { const s = m(pts[n - 1], pts[0]); ctx.moveTo(s[0], s[1]); }
    for (let i = closed ? 0 : 1; i < (closed ? n : n - 1); i++) {
      const p = pts[i], q = m(p, pts[(i + 1) % n]); ctx.quadraticCurveTo(p[0], p[1], q[0], q[1]);
    }
    if (!closed) ctx.lineTo(pts[n - 1][0], pts[n - 1][1]); else ctx.closePath();
  }
  function poly(ctx, pts) { ctx.beginPath(); pts.forEach((p, i) => i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])); ctx.closePath(); }
  // fill a leather piece: colour, punched holes along an inset outline, dark edge
  function leather(ctx, pts, color, o = {}) {
    const lw = (o.lw ?? 3) / (o.scale || 1);
    (o.sharp ? poly : smooth)(ctx, pts);
    ctx.save(); ctx.shadowColor = 'rgba(10,3,0,0.55)'; ctx.shadowBlur = 6; ctx.globalAlpha *= o.alpha ?? 0.9; ctx.fillStyle = color; ctx.fill(); ctx.restore();
    if (o.holes !== false) holes(ctx, pts, o.gap ?? 16, o.inset ?? 0.18, (o.r ?? 2.2) / (o.scale || 1) * (o.scale || 1));
    if (o.pattern) o.pattern(ctx);
    ctx.lineWidth = lw; ctx.strokeStyle = OUT; ctx.lineJoin = 'round'; (o.sharp ? poly : smooth)(ctx, pts); ctx.stroke();
  }
  function holes(ctx, pts, gap, inset, r) {
    const cx = pts.reduce((s, p) => s + p[0], 0) / pts.length, cy = pts.reduce((s, p) => s + p[1], 0) / pts.length;
    ctx.save(); ctx.fillStyle = HOLE;
    for (let i = 0; i < pts.length; i++) {
      const a = pts[i], b = pts[(i + 1) % pts.length], L = Math.hypot(b[0] - a[0], b[1] - a[1]), n = Math.max(1, Math.floor(L / gap));
      for (let k = 0; k < n; k++) {
        const u = k / n, x = lerp(a[0], b[0], u), y = lerp(a[1], b[1], u);
        ctx.beginPath(); ctx.arc(lerp(x, cx, inset), lerp(y, cy, inset), r, 0, Math.PI * 2); ctx.fill();
      }
    }
    ctx.restore();
  }
  function rosette(ctx, x, y, r) { for (let i = 0; i < 8; i++) { const a = i * Math.PI / 4; dot(ctx, x + Math.cos(a) * r, y + Math.sin(a) * r, Math.max(1.6, r * 0.18), HOLE); } dot(ctx, x, y, Math.max(1.8, r * 0.22), HOLE); }
  function dot(ctx, x, y, r, c) { ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fillStyle = c; ctx.fill(); }
  function rivet(ctx, x, y, r = 4) { dot(ctx, x, y, r + 1.5, OUT); dot(ctx, x, y, r * 0.6, '#e8c27a'); }
  function glow(ctx, x, y, r, color, a) {
    if (a <= 0) return;
    const g = ctx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, color); g.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = a; ctx.fillStyle = g; ctx.fillRect(x - r, y - r, 2 * r, 2 * r); ctx.restore();
  }
  function rod(ctx, x, y) {          // puppeteer's stick, from a hand down past the screen edge (device space)
    const m = ctx.getTransform(), p = m.transformPoint(new DOMPoint(x, y));
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.strokeStyle = 'rgba(20,8,2,0.55)'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(p.x + (p.x - W / 2) * 0.08, H + 40); ctx.stroke(); ctx.restore();
  }
  const mix = (c1, c2, u) => {      // hex colours
    const a = parseInt(c1.slice(1), 16), b = parseInt(c2.slice(1), 16);
    const ch = s => Math.round(lerp((a >> s) & 255, (b >> s) & 255, u));
    return `rgb(${ch(16)},${ch(8)},${ch(0)})`;
  };
  const stops3 = (v, A, B, C) => v < 0.5 ? mix(A, B, v * 2) : mix(B, C, (v - 0.5) * 2);
  function flicker(t) { return 0.93 + 0.07 * noise1(t * 3.1, 7); }

  // ---------- the jointed sage ----------
  const POSES = {   // degrees from straight down; + = forward (the way he faces)
    stand:    { uA: 8,   fA: 6,   uB: -6,  fB: 4,   th: 0, sh: 0, tB: 0, sB: 0, seated: 0, head: 0 },
    raise:    { uA: 158, fA: 8,   uB: 148, fB: 12,  th: 0, sh: 0, tB: 0, sB: 0, seated: 0, head: -12 },
    offer:    { uA: 112, fA: 38,  uB: 104, fB: 44,  th: 0, sh: 0, tB: 0, sB: 0, seated: 0, head: -6 },
    pray:     { uA: 28,  fA: 132, uB: 22,  fB: 128, th: 0, sh: 0, tB: 0, sB: 0, seated: 0, head: 4 },
    meditate: { uA: 18,  fA: 72,  uB: 12,  fB: 70,  th: 0, sh: 0, tB: 0, sB: 0, seated: 1, head: 6 },
  };
  function pose(p, t) {
    const a = POSES[p.pose || 'stand'], b = POSES[p.poseTo || p.pose || 'stand'], u = p.poseMix ?? (p.poseTo ? 1 : 0);
    const q = {}; for (const k in a) q[k] = lerp(a[k], b[k], u);
    if (p.walk) {                                  // walk cycle layered on top
      const ph = t * (p.pace || 1.6) * Math.PI * 2, w = p.walk;
      q.th += 24 * Math.sin(ph) * w; q.tB += -24 * Math.sin(ph) * w;
      q.sh += Math.max(0, 30 * Math.sin(ph - 1.2)) * w; q.sB += Math.max(0, -30 * Math.sin(ph - 1.2)) * w;
      if ((p.poseTo || p.pose || 'stand') === 'stand') { q.uA += 16 * Math.sin(ph) * w; q.uB -= 16 * Math.sin(ph) * w; }
      q.bob = Math.abs(Math.sin(ph)) * 5 * w;
    }
    return q;
  }
  function limb(ctx, ang1, ang2, L1, L2, w, color, sc, hand) {
    ctx.save(); ctx.rotate(-ang1 * Math.PI / 180);
    leather(ctx, [[-w, -4], [w, -4], [w * 0.8, L1], [-w * 0.8, L1]], color, { gap: 14, scale: sc });
    ctx.translate(0, L1); rivet(ctx, 0, 0, 3.5);
    ctx.rotate(-ang2 * Math.PI / 180);
    leather(ctx, [[-w * 0.8, -3], [w * 0.8, -3], [w * 0.6, L2], [-w * 0.6, L2]], color, { gap: 14, scale: sc });
    rivet(ctx, 0, 0, 3.5);
    if (hand) { ctx.translate(0, L2 + 9); leather(ctx, [[-9, -9], [9, -8], [10, 8], [0, 14], [-9, 7]], color, { holes: false, scale: sc }); }
    const m = ctx.getTransform(); ctx.restore(); return m;
  }
  function sage(ctx, p, t, env) {
    const q = pose(p, t), d = p.dir ?? 1, s = (p.s ?? 1) * 1.55;   // puppets are big and bold
    const SKIN = '#b45f2b', SKIN2 = '#7d3b17', DHOTI = '#d8891d', SASH = '#b8322a', HAIR = '#efe2c4';
    ctx.translate(p.x * W, p.y * H - (q.bob || 0)); ctx.scale(d * s, s);
    const seated = q.seated, hipY = lerp(-205, -70, seated);
    ctx.translate(0, hipY);
    // far arm (behind the body, from the far shoulder)
    ctx.save(); ctx.translate(-6, -168); limb(ctx, q.uB, q.fB, 76, 70, 16, SKIN2, s, true); ctx.restore();
    // legs
    if (seated < 0.5) {
      ctx.save(); ctx.rotate(-q.tB * Math.PI / 180); leather(ctx, [[-19, 0], [19, 0], [15, 104], [-14, 104]], SKIN2, { scale: s });
      ctx.translate(0, 104); ctx.rotate(q.sB * Math.PI / 180); leather(ctx, [[-15, 0], [15, 0], [12, 100], [-12, 100]], SKIN2, { scale: s });
      ctx.translate(0, 100); leather(ctx, [[-10, -4], [8, -4], [30, 4], [30, 10], [-10, 10]], SKIN2, { holes: false, scale: s }); ctx.restore();
      ctx.save(); ctx.rotate(-q.th * Math.PI / 180); leather(ctx, [[-20, 0], [20, 0], [16, 104], [-15, 104]], SKIN, { scale: s });
      ctx.translate(0, 104); rivet(ctx, 0, 0); ctx.rotate(q.sh * Math.PI / 180); leather(ctx, [[-16, 0], [16, 0], [13, 100], [-13, 100]], SKIN, { scale: s });
      ctx.translate(0, 100); leather(ctx, [[-11, -4], [9, -4], [32, 4], [32, 11], [-11, 11]], SKIN, { holes: false, scale: s }); ctx.restore();
    } else {                                       // cross-legged lap seen in profile
      leather(ctx, [[-40, -10], [20, -16], [95, 8], [110, 38], [70, 62], [-30, 62], [-46, 30]], DHOTI, { scale: s, gap: 18 });
      leather(ctx, [[60, 30], [112, 30], [118, 50], [64, 56]], SKIN, { holes: false, scale: s });
    }
    // dhoti over the hips (standing)
    if (seated < 0.5) leather(ctx, [[-50, -18], [48, -18], [54, 60], [34, 100], [-36, 100], [-54, 60]], DHOTI, { scale: s, gap: 16, pattern: c => { c.strokeStyle = SASH; c.lineWidth = 7; for (const yy of [8, 70]) { c.beginPath(); c.moveTo(-50, yy); c.lineTo(52, yy); c.stroke(); } c.strokeStyle = '#2f6b3a'; c.lineWidth = 4; c.beginPath(); c.moveTo(-48, 20); c.lineTo(50, 20); c.stroke(); for (let k = 0; k < 6; k++) rosette(c, -34 + k * 14, 44, 5); } });
    // torso
    leather(ctx, [[-46, 0], [44, 0], [42, -90], [38, -168], [8, -188], [-38, -178], [-50, -92]], SKIN, { scale: s, gap: 15, pattern: c => { rosette(c, 4, -110, 16); for (let k = 0; k < 7; k++) dot(c, -26 + k * 9, -150 + Math.abs(k - 3) * 5, 2.6, HOLE); } });
    // sash (uttarīya) across the chest, and the mala
    leather(ctx, [[-34, -178], [-12, -184], [36, -70], [30, -46], [-6, -100]], SASH, { scale: s, gap: 12, alpha: 0.85 });
    ctx.save(); ctx.strokeStyle = '#2a120a'; ctx.setLineDash([2, 7]); ctx.lineWidth = 6; ctx.beginPath(); ctx.ellipse(10, -150, 22, 38, -0.2, 0.3, Math.PI - 0.1); ctx.stroke(); ctx.restore();
    // head: profile, beard, topknot
    ctx.save(); ctx.translate(6, -188); ctx.rotate(q.head * Math.PI / 180);
    leather(ctx, [[-18, 4], [16, 2], [20, -16], [34, -26], [30, -32], [32, -44], [22, -64], [-2, -72], [-22, -60], [-26, -30]], SKIN, { scale: s, gap: 12 });
    leather(ctx, [[-22, -52], [-2, -76], [22, -66], [8, -60], [-14, -40]], HAIR, { scale: s, gap: 10, alpha: 0.95 });
    leather(ctx, [[-14, -78], [0, -96], [12, -84], [4, -72]], HAIR, { scale: s, holes: false });
    leather(ctx, [[2, -22], [30, -28], [28, 6], [18, 40], [2, 58], [-8, 30], [-6, -2]], HAIR, { scale: s, gap: 9, alpha: 0.95 });
    dot(ctx, 18, -44, 2.6, HOLE);                  // the eye: a punched hole
    ctx.strokeStyle = '#f3e6c7'; ctx.lineWidth = 2.2; for (let k = 0; k < 3; k++) { ctx.beginPath(); ctx.moveTo(0, -60 + k * 5); ctx.lineTo(20, -60 + k * 5); ctx.stroke(); }   // tripuṇḍra
    ctx.restore();
    // near arm (+ pot, pour)
    ctx.save(); ctx.translate(4, -170);
    const mNear = limb(ctx, q.uA, q.fA, 78, 72, 17, SKIN, s, true);
    ctx.restore();
    if (p.rods !== false) { const a = mNear.transformPoint(new DOMPoint(0, 0)); ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.strokeStyle = 'rgba(20,8,2,0.5)'; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(a.x + 60, H + 40); ctx.stroke(); ctx.restore(); }
    if (p.pot) {
      const h = mNear.transformPoint(new DOMPoint(0, -2)), sc = Math.hypot(mNear.a, mNear.b);
      ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.translate(h.x, h.y); ctx.scale(sc, sc);
      leather(ctx, [[-20, -8], [20, -8], [26, 10], [16, 28], [-16, 28], [-26, 10]], '#c98b2b', { scale: sc, gap: 9 });
      leather(ctx, [[-10, -20], [10, -20], [12, -8], [-12, -8]], '#c98b2b', { holes: false, scale: sc });
      if ((p.pour || 0) > 0) {                     // water stream catching the light
        const len = 330 * p.pour, R = rng(5);
        ctx.save(); ctx.globalCompositeOperation = 'lighter';
        const g = ctx.createLinearGradient(0, 0, 0, len); g.addColorStop(0, 'rgba(210,240,255,0.85)'); g.addColorStop(1, 'rgba(210,240,255,0.15)');
        ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(-5, -14); ctx.quadraticCurveTo(24 * d, len * 0.3, 10 * d, len); ctx.lineTo(18 * d, len); ctx.quadraticCurveTo(30 * d, len * 0.3, 6, -14); ctx.fill();
        for (let k = 0; k < 26; k++) { const yy = ((R() + t * 1.4) % 1) * len, xx = 12 * d + (R() - 0.5) * 34; dot(ctx, xx, yy, 2 + R() * 2.5, 'rgba(255,248,220,0.9)'); }
        ctx.restore();
      }
      ctx.restore();
    }
  }

  // ---------- elements ----------
  const el = {};
  el.screen = (ctx, p, t) => {             // the backlit cloth: day 0 = night (blue gel), 0.5 = dawn, 1 = day
    const v = clamp(p.day ?? 1, 0, 1), f = flicker(t);
    const c0 = stops3(v, '#3d6487', '#f0b878', '#fff1c8'), c1 = stops3(v, '#16283c', '#a8503a', '#e7a24c'), c2 = stops3(v, '#03060b', '#1e0b07', '#4a2309');
    const g = ctx.createRadialGradient(W * 0.5, H * 0.46, 40, W * 0.5, H * 0.5, W * 0.72);
    g.addColorStop(0, c0); g.addColorStop(0.45, c1); g.addColorStop(1, c2);
    ctx.fillStyle = g; ctx.fillRect(-W, -H, 3 * W, 3 * H);
    ctx.globalAlpha = 1 - f; ctx.fillStyle = '#000'; ctx.fillRect(-W, -H, 3 * W, 3 * H);
  };
  el.stars = (ctx, p, t) => {
    const R = rng(p.seed || 3), n = p.n || 150, a = p.a ?? 1; if (a <= 0) return;
    for (let i = 0; i < n; i++) {
      const x = R() * W * 1.3 - W * 0.15, y = R() * H * (p.band ?? 0.55), tw = 0.5 + 0.5 * Math.sin(t * (1 + R() * 2.5) + R() * 6);
      ctx.globalAlpha = a * (0.35 + 0.65 * tw); dot(ctx, x, y, 1.2 + R() * 2.4, HOLE);
    }
    ctx.globalAlpha = 1;
  };
  el.moon = (ctx, p) => {
    ctx.translate(p.x * W, p.y * H); const r = 60 * (p.s ?? 1);
    ctx.save(); ctx.beginPath(); ctx.arc(0, 0, r, 0, Math.PI * 2); ctx.arc(r * 0.42, -r * 0.12, r * 0.86, 0, Math.PI * 2, true);
    ctx.fillStyle = 'rgba(255,240,205,0.95)'; ctx.fill('evenodd'); ctx.lineWidth = 3; ctx.strokeStyle = OUT; ctx.stroke(); ctx.restore();
    glow(ctx, 0, 0, r * 3, 'rgba(255,240,200,0.5)', 0.6);
  };
  el.sun = (ctx, p, t) => {
    const s = p.s ?? 1, r = 120 * s, rays = p.rays ?? 1, rot = (p.rot ?? 0) + t * 4 * Math.PI / 180;
    ctx.translate(p.x * W, p.y * H);
    glow(ctx, 0, 0, r * (4 + 2 * (p.glow ?? 0.6)), 'rgba(255,214,120,0.9)', 0.55 * (p.glow ?? 0.6) * (p.a ?? 1));
    ctx.globalAlpha = p.a ?? 1;
    if (rays > 0) {
      ctx.save(); ctx.rotate(rot);
      for (let i = 0; i < 16; i++) {
        const L = r * (i % 2 ? 0.7 : 1.15) * rays + r, wd = (i % 2 ? 0.1 : 0.16);
        ctx.save(); ctx.rotate(i * Math.PI / 8);
        leather(ctx, [[r * 0.9, -r * wd], [L, 0], [r * 0.9, r * wd]], i % 2 ? '#e88a27' : '#f5b738', { sharp: true, holes: false });
        ctx.restore();
      }
      ctx.restore();
    }
    const disc = []; for (let i = 0; i < 40; i++) { const a = i / 40 * Math.PI * 2; disc.push([Math.cos(a) * r, Math.sin(a) * r]); }
    leather(ctx, disc, '#f7c548', { gap: 20, inset: 0.12, r: 3 });
    // punched lotus mandala in the disc
    ctx.save(); ctx.fillStyle = HOLE;
    for (let ring = 1; ring <= 3; ring++) for (let i = 0; i < 8 * ring; i++) { const a = i / (8 * ring) * Math.PI * 2 + ring; dot(ctx, Math.cos(a) * r * 0.22 * ring, Math.sin(a) * r * 0.22 * ring, 3.2, HOLE); }
    ctx.restore(); dot(ctx, 0, 0, r * 0.12, HOLE);
  };
  el.river = (ctx, p, t) => {
    const y0 = p.y * H, day = p.day ?? 0.5;
    const cols = [stops3(day, '#1f4a63', '#3f7f88', '#4f9fa4'), stops3(day, '#18394f', '#2f6672', '#3f8890'), stops3(day, '#102838', '#22505c', '#2f6f78')];
    for (let k = 0; k < 3; k++) {
      const yy = y0 + k * 70, sp = (k + 1) * 22 * (k % 2 ? -1 : 1), pts = [];
      for (let x = -W * 0.3; x <= W * 1.3; x += 60) pts.push([x, yy + Math.sin((x + t * sp) / 90 + k) * 10]);
      pts.push([W * 1.3, H * 2], [-W * 0.3, H * 2]);
      ctx.save(); ctx.globalAlpha = 0.88; poly(ctx, pts); ctx.fillStyle = cols[k]; ctx.fill(); ctx.restore();
      ctx.save(); ctx.fillStyle = HOLE; for (let i = 0; i < pts.length - 2; i++) if (i % 2 === k % 2) dot(ctx, pts[i][0], pts[i][1] + 14, 2.4, HOLE); ctx.restore();
      ctx.lineWidth = 3; ctx.strokeStyle = OUT; ctx.beginPath(); for (let i = 0; i < pts.length - 2; i++) i ? ctx.lineTo(...pts[i]) : ctx.moveTo(...pts[i]); ctx.stroke();
    }
    if ((p.glitter || 0) > 0) {                       // sun path on the water
      const R = rng(9); ctx.save(); ctx.globalCompositeOperation = 'lighter';
      for (let i = 0; i < 70; i++) { const x = (p.gx ?? 0.5) * W + (R() - 0.5) * 260 * (1 + R()), y = y0 + R() * 240, a = p.glitter * (0.4 + 0.6 * Math.sin(t * 5 + i)); ctx.globalAlpha = Math.max(0, a); ctx.fillStyle = '#fff3c4'; ctx.fillRect(x - 14, y, 28, 3); }
      ctx.restore();
    }
  };
  el.ghat = (ctx, p) => {
    ctx.translate(p.x * W, p.y * H); ctx.scale(p.s ?? 1, p.s ?? 1);
    for (let k = 0; k < 5; k++) leather(ctx, [[-800 + k * 30, k * 34], [140 - k * 12, k * 34], [140 - k * 12, k * 34 + 36], [-800 + k * 30, k * 34 + 36]], k % 2 ? '#a57b45' : '#b88c52', { sharp: true, gap: 22 });
    leather(ctx, [[-400, 0], [-400, -170], [-370, -230], [-340, -170], [-340, 0]], '#9c6b3a', { sharp: true, gap: 16 });   // small shrine
    leather(ctx, [[-382, -230], [-370, -275], [-358, -230]], '#d0a24a', { sharp: true, holes: false });
  };
  el.temple = (ctx, p) => {                // far-bank temple spire, darker (further from the lamp)
    ctx.translate(p.x * W, p.y * H); ctx.scale(p.s ?? 1, p.s ?? 1);
    leather(ctx, [[-90, 0], [-90, -60], [-60, -70], [-40, -170], [0, -260], [40, -170], [60, -70], [90, -60], [90, 0]], '#5a3a26', { gap: 18, alpha: 0.8 });
    leather(ctx, [[-8, -260], [0, -300], [8, -260]], '#c79a3c', { holes: false });
  };
  el.palm = (ctx, p, t) => {
    ctx.translate(p.x * W, p.y * H); ctx.scale((p.dir ?? 1) * (p.s ?? 1), p.s ?? 1);
    leather(ctx, [[-12, 0], [12, 0], [26, -150], [40, -300], [26, -302], [8, -150]], '#6b4423', { gap: 20 });
    const sw = Math.sin(t * 0.9) * 0.05;
    for (let i = 0; i < 7; i++) {
      ctx.save(); ctx.translate(34, -300); ctx.rotate(-1.4 + i * 0.45 + sw);
      leather(ctx, [[0, -10], [90, -26], [190, 10], [90, 6], [0, 10]], i % 2 ? '#3f6b2a' : '#4f7d31', { gap: 18 }); ctx.restore();
    }
  };
  el.hills = (ctx, p) => {
    const y0 = p.y * H; ctx.globalAlpha = p.a ?? 1;
    leather(ctx, [[-W * 0.3, y0 + 40], [W * 0.05, y0 - 90], [W * 0.3, y0 - 30], [W * 0.55, y0 - 140], [W * 0.85, y0 - 40], [W * 1.3, y0 - 110], [W * 1.3, y0 + 200], [-W * 0.3, y0 + 200]], p.color || '#4d6b2b', { gap: 26 });
  };
  el.clouds = (ctx, p, t) => {
    const R = rng(p.seed || 4); ctx.globalAlpha = p.a ?? 1;
    for (let i = 0; i < (p.n || 4); i++) {
      const cx = ((R() * 1.4 - 0.2) * W + t * 12 * (0.5 + R())) % (W * 1.4) - W * 0.2, cy = (p.y ?? 0.3) * H + (R() - 0.5) * 120, sc = 0.7 + R() * 0.7;
      ctx.save(); ctx.translate(cx, cy); ctx.scale(sc, sc);
      leather(ctx, [[-150, 30], [-120, -20], [-60, -40], [-10, -80], [60, -60], [110, -30], [160, 20], [100, 40], [-80, 44]], p.color || '#e7e0d2', { gap: 18, alpha: 0.85 });
      ctx.restore();
    }
  };
  el.worlds = (ctx, p, t) => {             // bhūr, bhuvaḥ, svaḥ: earth, middle air, heaven light up in turn
    const band = (v, y0, y1, color) => { const a = 0.12 + 0.88 * clamp(v, 0, 1); ctx.save(); ctx.globalAlpha = a; ctx.fillStyle = color; ctx.fillRect(-W, y0 * H, 3 * W, (y1 - y0) * H); ctx.restore(); };
    const earth = p.earth ?? 0, sky = p.sky ?? 0, heaven = p.heaven ?? 0;
    band(heaven, -0.5, 0.33, '#2b2f6b'); el.stars(ctx, { a: heaven, band: 0.33, n: 110, seed: 8 }, t);
    if (heaven > 0) glow(ctx, W / 2, 0, W * 0.5, 'rgba(255,225,150,0.8)', 0.5 * heaven);
    band(sky, 0.33, 0.6, '#5d86a6'); el.clouds(ctx, { y: 0.47, n: 5, a: 0.15 + 0.85 * sky, seed: 2 }, t);
    band(earth, 0.6, 1.5, '#3b4d22'); el.hills(ctx, { y: 0.66, a: 0.2 + 0.8 * earth, color: '#5b7a2c' });
    for (const [v, y] of [[earth, 0.8], [sky, 0.47], [heaven, 0.16]]) { const flash = clamp(v * (1 - v) * 4, 0, 1); glow(ctx, W / 2, y * H, W * 0.45, 'rgba(255,230,170,0.9)', 0.35 * flash); }
  };
  el.diya = (ctx, p, t) => {
    ctx.translate(p.x * W, p.y * H); ctx.scale(p.s ?? 1, p.s ?? 1);
    leather(ctx, [[-40, 0], [40, 0], [30, 22], [-30, 22]], '#a2512a', { gap: 12 });
    const lit = p.lit ?? 1, fl = 1 + 0.15 * Math.sin(t * 13) + 0.1 * noise1(t * 6, 2);
    if (lit > 0) {
      glow(ctx, 0, -20, 160 * lit, 'rgba(255,200,110,0.95)', 0.7 * lit);
      ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = lit;
      ctx.fillStyle = '#ffe9a6'; ctx.beginPath(); ctx.moveTo(-9, -2); ctx.quadraticCurveTo(-8, -26 * fl, 0, -46 * fl); ctx.quadraticCurveTo(8, -26 * fl, 9, -2); ctx.fill(); ctx.restore();
    }
  };
  el.lotus = (ctx, p, t) => {
    const o = clamp(p.open ?? 1, 0, 1), s = p.s ?? 1, rise = p.rise ?? 1;
    ctx.translate(p.x * W, p.y * H + (1 - rise) * 120); ctx.scale(s, s);
    leather(ctx, [[-130, 20], [-40, -6], [10, 10], [-20, 30], [-110, 36]], '#3f6b2a', { gap: 18 });
    leather(ctx, [[130, 20], [40, -6], [-10, 10], [20, 30], [110, 36]], '#4a7a30', { gap: 18 });
    for (const [n, R, col] of [[8, 1, '#e9849a'], [6, 0.72, '#f3a6b8']]) for (let i = 0; i < n; i++) {
      const base = (i - (n - 1) / 2) / ((n - 1) / 2), ang = base * lerp(0.15, 1.25, o) * R;
      ctx.save(); ctx.rotate(ang); ctx.scale(R, R);
      leather(ctx, [[0, 4], [-24, -40], [0, -110], [24, -40]], col, { gap: 14, alpha: 0.88 }); ctx.restore();
    }
    if (o > 0.6) dot(ctx, 0, -24, 14 * (o - 0.6) / 0.4, '#f9d65c');
  };
  el.egrets = (ctx, p, t) => {
    const f = p.fly ?? 0, n = p.n || 5; if (f <= 0) return;
    for (let i = 0; i < n; i++) {
      const u = clamp(f * 1.25 - i * 0.06, 0, 1); if (u <= 0 || u >= 1) continue;
      const x = lerp(-0.15, 1.15, u) * W, y = (p.y ?? 0.28) * H + Math.sin(u * 6 + i) * 30 + (i % 3) * 46 - u * 120;
      const flap = Math.sin(t * 7 + i * 1.3), sc = (p.s ?? 1) * (1.15 + 0.1 * (i % 3));
      ctx.save(); ctx.translate(x, y); ctx.scale(sc, sc);
      ctx.save(); ctx.rotate(0.15 - flap * 0.55); leather(ctx, [[-30, -4], [-80, -100], [-60, -92], [-46, -96], [-30, -84], [-14, -84], [30, -10]], '#e9e0cc', { gap: 12, sharp: true }); ctx.restore();   // far wing
      ctx.strokeStyle = OUT; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(-50, 6); ctx.lineTo(-105, 18); ctx.moveTo(-50, 8); ctx.lineTo(-100, 26); ctx.stroke();                     // trailing legs
      leather(ctx, [[-60, 0], [-20, -10], [30, -8], [52, -26], [70, -40], [86, -40], [118, -36], [88, -30], [74, -24], [56, -2], [24, 12], [-30, 12]], '#f4eee0', { gap: 12 });        // body, S-neck, beak
      dot(ctx, 80, -36, 2.2, OUT);
      ctx.save(); ctx.rotate(-0.1 + flap * 0.6); leather(ctx, [[-36, 0], [-72, 100], [-52, 92], [-38, 98], [-22, 86], [-4, 84], [34, 4]], '#f7f2e6', { gap: 12, sharp: true, pattern: c => { for (let k = 1; k < 4; k++) dot(c, -20 - k * 8, k * 20, 2.4, HOLE); } }); ctx.restore();  // near wing
      ctx.restore();
    }
  };
  el.sage = sage;

  window.STYLE = {
    name: 'shadow_puppet', el, fadeColor: '#0a0402',
    init() {                                   // cloth weave + grain, made once
      TEX = document.createElement('canvas'); TEX.width = W; TEX.height = H;
      const c = TEX.getContext('2d'), R = rng(21), img = c.createImageData(W, H);
      for (let i = 0; i < W * H; i++) { const x = i % W, y = (i / W) | 0, v = 128 + (R() - 0.5) * 34 + ((x % 3 === 0) ? 6 : 0) + ((y % 3 === 0) ? 5 : 0); img.data[i * 4] = img.data[i * 4 + 1] = img.data[i * 4 + 2] = v; img.data[i * 4 + 3] = 255; }
      c.putImageData(img, 0, 0);
    },
    post(ctx, t) {
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.save(); ctx.globalCompositeOperation = 'overlay'; ctx.globalAlpha = 0.22; ctx.drawImage(TEX, 0, 0); ctx.restore();
      const g = ctx.createRadialGradient(W / 2, H * 0.48, H * 0.35, W / 2, H / 2, W * 0.7);
      g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(8,3,0,0.7)'); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    },
  };
})();
