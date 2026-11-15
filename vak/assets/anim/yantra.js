// Style: Yantra + Akshara (figure-free, for chants without a story).
// Sacred geometry draws itself and breathes with the voice (every sung word sends a pulse and a ripple),
// the deity's own symbols sit around it as line-art in light, and each sung word is written in light at the
// centre: its outline draws stroke by stroke, then it fills and glows. No people, no faces, no deity images.
(function () {
  const { W, H, clamp, lerp, rng, noise1 } = VAK;
  const TAU = Math.PI * 2, D2R = Math.PI / 180;
  const hex = c => { const n = parseInt(c.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; };
  const mix = (a, b, u) => a.map((v, i) => Math.round(lerp(v, b[i], u)));
  const rgba = (a, al = 1) => `rgba(${a[0]},${a[1]},${a[2]},${al})`;

  // palettes: centre, edge, centre at the end of the chant (light grows), line colour, accent
  const PAL = {
    shiva:   { c0: '#1b2350', e: '#04050d', c1: '#2f3f80', line: '#d8e6ff', acc: '#8fb4ff' },
    vishnu:  { c0: '#0f2a5a', e: '#02050d', c1: '#1d4f8f', line: '#ffd98a', acc: '#62d4ff' },
    devi:    { c0: '#4a0e2a', e: '#0c0206', c1: '#7a1c3e', line: '#ffcf8a', acc: '#ff6a95' },
    ganesha: { c0: '#561b0b', e: '#0d0402', c1: '#8a3410', line: '#ffd57a', acc: '#ff8a3a' },
    surya:   { c0: '#5a2a0a', e: '#100503', c1: '#a8521a', line: '#ffe6a8', acc: '#ffb43a' },
    peace:   { c0: '#0f3a3a', e: '#020a0c', c1: '#1f6a5e', line: '#f8ead0', acc: '#86e3c8' },
  };
  const pal = p => PAL[p.pal || 'peace'] || PAL.peace;

  function glow(ctx, x, y, r, col, a) {
    if (a <= 0) return;
    const g = ctx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, col); g.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = clamp(a, 0, 1); ctx.fillStyle = g; ctx.fillRect(x - r, y - r, 2 * r, 2 * r); ctx.restore();
  }

  // ---------- voice pulse: every sung word starts a pulse ----------
  function words() { const out = []; for (const u of VAK.units()) for (const w of u.words || []) if (w.start != null) out.push(w); return out; }
  let WORDS = null;
  function pulse(t) {
    WORDS = WORDS || words(); let p = 0;
    for (const w of WORDS) { const d = t - w.start; if (d >= 0 && d < 2.5) p += Math.exp(-d * 2.4); }
    return Math.min(p, 1.4);
  }
  function currentWord(t) {
    WORDS = WORDS || words(); let cur = null;
    for (const w of WORDS) if (t >= w.start - 0.12 && t < w.end + 0.35) cur = w;
    return cur;
  }

  // ---------- progressive line drawing ----------
  function strokePart(ctx, pts, u, closed) {        // draw the first u (0..1) of a polyline
    if (u <= 0) return;
    const P = closed ? pts.concat([pts[0]]) : pts;
    const n = (P.length - 1) * clamp(u, 0, 1), k = Math.floor(n);
    ctx.beginPath(); ctx.moveTo(P[0][0], P[0][1]);
    for (let i = 1; i <= k; i++) ctx.lineTo(P[i][0], P[i][1]);
    if (k < P.length - 1) { const f = n - k, a = P[k], b = P[k + 1]; ctx.lineTo(lerp(a[0], b[0], f), lerp(a[1], b[1], f)); }
    ctx.stroke();
  }
  const circ = (r, n = 120, rot = 0) => Array.from({ length: n }, (_, i) => [Math.cos(rot + i * TAU / n) * r, Math.sin(rot + i * TAU / n) * r]);
  const tri = (r, rot) => [0, 1, 2].map(i => [Math.cos(rot + i * TAU / 3) * r, Math.sin(rot + i * TAU / 3) * r]);
  function bhupura(h, g) {                          // the square outer gate of a yantra, with a T-shaped door on each side
    const pts = [];
    for (let side = 0; side < 4; side++) {
      const rot = side * Math.PI / 2, P = (x, y) => [x * Math.cos(rot) - y * Math.sin(rot), x * Math.sin(rot) + y * Math.cos(rot)];
      pts.push(P(-h, -h), P(-g, -h), P(-g, -h - g * 0.5), P(-g * 1.6, -h - g * 0.5), P(-g * 1.6, -h - g * 1.05), P(g * 1.6, -h - g * 1.05),
               P(g * 1.6, -h - g * 0.5), P(g, -h - g * 0.5), P(g, -h));
    }
    return pts;
  }
  function petals(n, r0, r1, w, rot) {               // one closed outline of n pointed petals
    const pts = [];
    for (let i = 0; i < n; i++) {
      const a = rot + i * TAU / n;
      for (let k = 0; k <= 12; k++) {
        const s = k / 12, ang = a + (s - 0.5) * (TAU / n) * w, tip = 1 - Math.abs(2 * s - 1), rr = lerp(r0, r1, tip ** 1.35);   // pointed lotus petal
        pts.push([Math.cos(ang) * rr, Math.sin(ang) * rr]);
      }
    }
    return pts;
  }

  // ---------- elements ----------
  const el = {};
  el.field = (ctx, p, t) => {                      // deep radial ground, drifting soft light, stars
    const P = pal(p), c = mix(hex(P.c0), hex(P.c1), clamp(p.mix ?? 0, 0, 1)), e = hex(P.e);
    const g = ctx.createRadialGradient(W / 2, H * 0.42, 40, W / 2, H * 0.45, W * 0.75);
    g.addColorStop(0, rgba(c)); g.addColorStop(0.55, rgba(mix(c, e, 0.6))); g.addColorStop(1, rgba(e));
    ctx.fillStyle = g; ctx.fillRect(-W, -H, 3 * W, 3 * H);
    const A = hex(P.acc);
    for (let i = 0; i < 4; i++) {                    // slow nebula
      const x = W * (0.2 + 0.6 * noise1(t * 0.03 + i * 7, 3)), y = H * (0.2 + 0.5 * noise1(t * 0.025 + i * 11, 5));
      glow(ctx, x, y, 420 + 120 * i, rgba(A, 0.5), 0.08 + 0.04 * (p.mix ?? 0));
    }
    const R = rng(p.seed || 9);
    for (let i = 0; i < (p.stars ?? 140); i++) {
      const x = R() * W, y = R() * H, tw = 0.4 + 0.6 * Math.sin(t * (0.6 + R() * 1.6) + R() * 6);
      ctx.globalAlpha = 0.25 + 0.5 * tw * (1 - 0.6 * (p.mix ?? 0)); ctx.fillStyle = '#fff6e0'; ctx.fillRect(x, y, 1.6, 1.6);
    }
    ctx.globalAlpha = 1;
  };

  el.geometry = (ctx, p, t) => {                   // the yantra: rings, petals, triangles; draws itself, breathes with the voice
    const P = pal(p), L = hex(P.line), A = hex(P.acc), x = (p.x ?? 0.5) * W, y = (p.y ?? 0.4) * H, R = p.r ?? 300;
    const dr = clamp(p.draw ?? 1, 0, 1), pu = pulse(t), a = p.a ?? 1; if (a <= 0) return;
    const breathe = 1 + 0.012 * pu, rot = t * (p.spin ?? 0.02);
    const parts = [];
    const kind = p.kind || 'hex';
    parts.push([bhupura(R * 1.2, R * 0.16), true, 0.32], [circ(R * 1.08), true, 0.45], [circ(R * 1.03), true, 0.3]);
    parts.push([petals(16, R * 0.84, R * 1.02, 0.96, rot * 0.5), true, 0.6], [petals(16, R * 0.84, R * 0.96, 0.96, rot * 0.5 + Math.PI / 16), true, 0.3]);
    parts.push([petals(8, R * 0.66, R * 0.86, 0.98, -rot), true, 0.75], [circ(R * 0.66), true, 0.55], [circ(R * 0.62), true, 0.3]);
    if (kind === 'shri') {
      for (let k = 0; k < 4; k++) parts.push([tri(R * (0.66 - k * 0.12), -Math.PI / 2 + rot * 0.2).map(([u, v]) => [u, v + R * 0.05 * k]), true, 0.85]);
      for (let k = 0; k < 5; k++) parts.push([tri(R * (0.66 - k * 0.1), Math.PI / 2 - rot * 0.2).map(([u, v]) => [u, v - R * 0.04 * k]), true, 0.85]);
    } else if (kind === 'sun') {
      const st = []; for (let i = 0; i < 24; i++) { const r = i % 2 ? R * 0.4 : R * 0.66, an = rot + i * TAU / 24; st.push([Math.cos(an) * r, Math.sin(an) * r]); }
      parts.push([st, true, 0.9]);
    } else if (kind === 'lotus') {
      parts.push([petals(12, R * 0.3, R * 0.66, 0.85, rot), true, 0.85]);
      const sp = []; for (let i = 0; i < 12; i++) { const an = -rot + i * TAU / 12; sp.push([0, 0], [Math.cos(an) * R * 0.3, Math.sin(an) * R * 0.3]); }
      parts.push([sp, false, 0.5]);
    } else {                                        // hexagram (two triangles) inside the lotus
      parts.push([tri(R * 0.66, -Math.PI / 2 + rot * 0.3), true, 0.9], [tri(R * 0.66, Math.PI / 2 + rot * 0.3), true, 0.9]);
    }
    parts.push([circ(R * 0.22), true, 0.7]);
    ctx.save(); ctx.translate(x, y); ctx.scale(breathe, breathe); ctx.globalCompositeOperation = 'lighter'; ctx.lineJoin = 'round';
    glow(ctx, 0, 0, R * 1.3, rgba(A, 0.6), 0.14 + 0.18 * pu);
    parts.forEach(([pts, closed, al], i) => {
      const u = clamp(dr * parts.length - i, 0, 1); if (u <= 0) return;
      ctx.strokeStyle = rgba(L, a * al * (0.55 + 0.35 * Math.min(pu, 1))); ctx.lineWidth = 2 + 1.2 * pu;
      strokePart(ctx, pts, u, closed);
    });
    const dots = clamp(dr * parts.length - parts.length + 2, 0, 1);
    if (dots > 0) { ctx.fillStyle = rgba(L, a * 0.7 * dots); for (let i = 0; i < 72; i++) { const an = i * TAU / 72 - rot * 0.8; ctx.beginPath(); ctx.arc(Math.cos(an) * R * 1.055, Math.sin(an) * R * 1.055, i % 6 ? 1.6 : 3, 0, TAU); ctx.fill(); } }
    if (dr >= 1) { glow(ctx, 0, 0, 90 + 50 * pu, rgba(L, 1), a * (0.35 + 0.4 * pu)); }
    ctx.restore();
  };

  el.ripples = (ctx, p, t) => {                    // a ring leaves the centre on every sung word
    const P = pal(p), A = hex(P.acc), x = (p.x ?? 0.5) * W, y = (p.y ?? 0.4) * H, a = p.a ?? 1;
    WORDS = WORDS || words();
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    for (const w of WORDS) {
      const d = t - w.start; if (d < 0 || d > 3) continue;
      const r = 80 + d * 220, al = a * 0.45 * (1 - d / 3) ** 1.5;
      ctx.strokeStyle = rgba(A, al); ctx.lineWidth = 3 * (1 - d / 3) + 0.5; ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.stroke();
    }
    ctx.restore();
  };

  // symbols: line-art in light, centred at 0,0, size s
  const SYM = {
    crescent(ctx, s) { ctx.beginPath(); ctx.arc(0, 0, s, 0.35 * Math.PI, 1.65 * Math.PI, false); ctx.arc(s * 0.42, -s * 0.1, s * 0.8, 1.55 * Math.PI, 0.45 * Math.PI, true); ctx.closePath(); ctx.stroke(); },
    trishula(ctx, s) {
      ctx.beginPath(); ctx.moveTo(0, s * 1.2); ctx.lineTo(0, -s * 0.9); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0, -s * 1.25); ctx.lineTo(-s * 0.12, -s * 0.9); ctx.lineTo(s * 0.12, -s * 0.9); ctx.closePath(); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(-s * 0.7, -s * 0.95); ctx.quadraticCurveTo(-s * 0.7, -s * 0.2, 0, -s * 0.15); ctx.quadraticCurveTo(s * 0.7, -s * 0.2, s * 0.7, -s * 0.95); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(-s * 0.7, -s * 0.95); ctx.lineTo(-s * 0.82, -s * 0.72); ctx.moveTo(s * 0.7, -s * 0.95); ctx.lineTo(s * 0.82, -s * 0.72); ctx.stroke();
      ctx.beginPath(); ctx.ellipse(0, s * 0.25, s * 0.18, s * 0.1, 0, 0, TAU); ctx.stroke();
    },
    bilva(ctx, s) { for (const a of [-55, 0, 55]) { ctx.save(); ctx.rotate(a * D2R); ctx.beginPath(); ctx.ellipse(0, -s * 0.55, s * 0.3, s * 0.6, 0, 0, TAU); ctx.moveTo(0, 0); ctx.lineTo(0, -s * 1.05); ctx.stroke(); ctx.restore(); } ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(0, s * 0.8); ctx.stroke(); },
    shankha(ctx, s) {
      ctx.beginPath(); for (let i = 0; i <= 90; i++) { const a = i / 90 * TAU * 2.2, r = s * 0.08 + s * 0.5 * i / 90; const px = Math.cos(a) * r * 0.9, py = Math.sin(a) * r * 0.6 - s * 0.2; i ? ctx.lineTo(px, py) : ctx.moveTo(px, py); } ctx.stroke();
      ctx.beginPath(); ctx.moveTo(s * 0.45, -s * 0.1); ctx.quadraticCurveTo(s * 0.4, s * 0.9, 0, s * 1.2); ctx.quadraticCurveTo(-s * 0.5, s * 0.7, -s * 0.5, s * 0.1); ctx.stroke();
    },
    chakra(ctx, s, t) {
      ctx.save(); ctx.rotate(t * 0.4);
      ctx.beginPath(); ctx.arc(0, 0, s, 0, TAU); ctx.stroke(); ctx.beginPath(); ctx.arc(0, 0, s * 0.25, 0, TAU); ctx.stroke();
      for (let i = 0; i < 12; i++) { const a = i * TAU / 12; ctx.beginPath(); ctx.moveTo(Math.cos(a) * s * 0.25, Math.sin(a) * s * 0.25); ctx.lineTo(Math.cos(a) * s, Math.sin(a) * s); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(Math.cos(a - 0.12) * s, Math.sin(a - 0.12) * s); ctx.lineTo(Math.cos(a) * s * 1.22, Math.sin(a) * s * 1.22); ctx.lineTo(Math.cos(a + 0.12) * s, Math.sin(a + 0.12) * s); ctx.stroke(); }
      ctx.restore();
    },
    lotus(ctx, s) {
      for (const [a, k] of [[0, 1.15], [-34, 0.95], [34, 0.95], [-64, 0.7], [64, 0.7]]) { ctx.save(); ctx.rotate(a * D2R); ctx.beginPath(); ctx.moveTo(0, s * 0.45); ctx.quadraticCurveTo(-s * 0.32, -s * 0.2 * k, 0, -s * k); ctx.quadraticCurveTo(s * 0.32, -s * 0.2 * k, 0, s * 0.45); ctx.stroke(); ctx.restore(); }
      ctx.beginPath(); ctx.moveTo(-s * 0.9, s * 0.55); ctx.quadraticCurveTo(0, s * 0.8, s * 0.9, s * 0.55); ctx.stroke();
    },
    flame(ctx, s, t) {
      const f = 1 + 0.08 * Math.sin(t * 9) + 0.05 * noise1(t * 4, 2);
      ctx.beginPath(); ctx.moveTo(-s * 0.7, s * 0.35); ctx.quadraticCurveTo(0, s * 0.95, s * 0.7, s * 0.35); ctx.lineTo(-s * 0.7, s * 0.35); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(-s * 0.18, s * 0.3); ctx.quadraticCurveTo(-s * 0.3, -s * 0.3 * f, 0, -s * 0.95 * f); ctx.quadraticCurveTo(s * 0.3, -s * 0.3 * f, s * 0.18, s * 0.3); ctx.stroke();
    },
    sun(ctx, s, t) { ctx.beginPath(); ctx.arc(0, 0, s * 0.5, 0, TAU); ctx.stroke(); for (let i = 0; i < 12; i++) { const a = i * TAU / 12 + t * 0.1; ctx.beginPath(); ctx.moveTo(Math.cos(a) * s * 0.68, Math.sin(a) * s * 0.68); ctx.lineTo(Math.cos(a) * s * (i % 2 ? 0.95 : 1.15), Math.sin(a) * s * (i % 2 ? 0.95 : 1.15)); ctx.stroke(); } },
  };
  function glyph(ctx, txt, s, col) { ctx.font = `${s * 1.7}px "Tiro Devanagari Sanskrit"`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.lineWidth = 2.4; ctx.strokeStyle = col; ctx.strokeText(txt, 0, s * 0.1); }

  el.symbols = (ctx, p, t) => {                    // the deity's symbols around the yantra; the focused one glows
    const P = pal(p), L = hex(P.line), A = hex(P.acc), cx = (p.x ?? 0.5) * W, cy = (p.y ?? 0.4) * H, R = (p.r ?? 300) * 1.62;
    const set = p.set || ['om', 'lotus', 'flame', 'sun'], show = clamp(p.show ?? 1, 0, 1); if (show <= 0) return;
    const angs = p.angles || [-166, -128, -52, -14], focus = p.focus ?? -1, pu = pulse(t);
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    set.forEach((name, i) => {
      const a = angs[i % angs.length] * D2R, x = cx + Math.cos(a) * R, y = cy + Math.sin(a) * R * 0.86, on = i === focus;
      const s = (p.s ?? 46) * (on ? 1.18 + 0.05 * pu : 1), al = show * (on ? 0.95 : 0.4);
      glow(ctx, x, y, s * (on ? 3.2 : 2), rgba(A, 0.7), al * (on ? 0.45 + 0.25 * pu : 0.15));
      ctx.save(); ctx.translate(x, y + Math.sin(t * 0.7 + i) * 4); ctx.strokeStyle = rgba(L, al); ctx.lineWidth = on ? 3 : 2.2;
      if (name === 'om') glyph(ctx, 'ॐ', s, rgba(L, al));
      else if (name.startsWith('bija:')) glyph(ctx, name.slice(5), s, rgba(L, al));
      else (SYM[name] || SYM.lotus)(ctx, s, t);
      ctx.restore();
    });
    ctx.restore();
  };

  el.word = (ctx, p, t) => {                       // the sung word, written in light at the centre
    const w = currentWord(t); if (!w) return;
    const P = pal(p), L = hex(P.line), A = hex(P.acc), x = (p.x ?? 0.5) * W, y = (p.y ?? 0.4) * H;
    const age = t - (w.start - 0.12), draw = clamp(age / 0.55, 0, 1), fill = clamp((age - 0.3) / 0.45, 0, 1), out = clamp((w.end + 0.35 - t) / 0.35, 0, 1);
    let size = p.size ?? 150;
    ctx.save(); ctx.font = `${size}px "Tiro Devanagari Sanskrit"`;
    const tw = ctx.measureText(w.dev).width, maxW = (p.maxw ?? 0.46) * W; if (tw > maxW) { size *= maxW / tw; ctx.font = `${size}px "Tiro Devanagari Sanskrit"`; }
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.globalAlpha = out;
    glow(ctx, x, y, size * 2.2, rgba(A, 0.8), 0.35 * fill * out);
    ctx.globalCompositeOperation = 'lighter';
    ctx.setLineDash([900, 900]); ctx.lineDashOffset = 900 * (1 - draw); ctx.lineWidth = 2.6; ctx.strokeStyle = rgba(L, 0.95);
    ctx.strokeText(w.dev, x, y);
    ctx.setLineDash([]);
    if (fill > 0) { ctx.globalAlpha = out * fill; ctx.fillStyle = rgba(mix(L, [255, 255, 255], 0.35)); ctx.fillText(w.dev, x, y); }
    ctx.restore();
    // a few sparks leave the word as it's sung
    const R = rng(Math.round(w.start * 100)); ctx.save(); ctx.globalCompositeOperation = 'lighter';
    for (let i = 0; i < 24; i++) { const an = R() * TAU, sp = 60 + R() * 220, d = Math.max(0, age) * sp, al = out * (1 - clamp(age / 1.6, 0, 1)) * R();
      ctx.fillStyle = rgba(L, al); ctx.fillRect(x + Math.cos(an) * (size * 0.4 + d), y + Math.sin(an) * (size * 0.25 + d * 0.6), 2.2, 2.2); }
    ctx.restore();
  };

  el.embers = (ctx, p, t) => {                     // slow motes rising, brighter on each word
    const P = pal(p), L = hex(P.line), R = rng(p.seed || 4), pu = pulse(t), n = p.n || 70;
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    for (let i = 0; i < n; i++) {
      const sp = 14 + R() * 30, x = R() * W + Math.sin(t * 0.3 + i) * 30, y = H * 1.05 - ((R() * H * 1.3 + t * sp) % (H * 1.3)), r = 1 + R() * 2.4;
      ctx.fillStyle = rgba(L, (0.12 + 0.3 * R()) * (0.7 + 0.5 * pu) * (p.a ?? 1)); ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill();
    }
    ctx.restore();
  };

  el.bindu = (ctx, p) => { const P = pal(p), a = p.a ?? 0; if (a <= 0) return; const x = (p.x ?? 0.5) * W, y = (p.y ?? 0.4) * H;
    glow(ctx, x, y, (p.r ?? 380), rgba(hex(P.line), 1), a); glow(ctx, x, y, (p.r ?? 380) * 0.25, 'rgba(255,255,255,1)', a); };

  window.STYLE = {
    name: 'yantra', el, fadeColor: '#020205',
    post(ctx) {                                     // soft vignette
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      const g = ctx.createRadialGradient(W / 2, H * 0.45, H * 0.45, W / 2, H / 2, W * 0.75);
      g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,0.55)'); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    },
  };
})();
