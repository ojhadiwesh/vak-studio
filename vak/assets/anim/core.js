// Style-agnostic animation core: plan timing, property animation, camera, scene fades.
// A style file registers draw functions for library elements: STYLE.el[name](ctx, props, t, env).
// The plan never mentions a style; the same plan.json renders in any style.
(function () {
  const W = 1920, H = 1080;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const lerp = (a, b, u) => a + (b - a) * u;
  const EASE = {
    linear: u => u,
    in: u => u * u,
    out: u => 1 - (1 - u) * (1 - u),
    inout: u => u * u * (3 - 2 * u),
    back: u => { const c1 = 1.4, c3 = c1 + 1; return 1 + c3 * Math.pow(u - 1, 3) + c1 * Math.pow(u - 1, 2); },   // slight overshoot: poses land with weight
  };
  function rng(seed) {             // mulberry32: deterministic noise for every style
    let a = seed >>> 0;
    return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  }
  function noise1(x, seed = 1) {   // smooth 1-D value noise in [0,1]
    const i = Math.floor(x), f = x - i, h = n => { const r = rng((n * 374761393 + seed * 668265263) >>> 0); return r(); };
    const u = f * f * (3 - 2 * f); return lerp(h(i), h(i + 1), u);
  }

  let PLAN = null, UNITS = [], NARR = [], T0 = 0;
  // Time anchors: a number (seconds on the film timeline), a chant word {u, w, e:"start"|"end", f:0..1, d:+seconds},
  // or a narration line {n, e, f, d}
  function at(a) {
    if (typeof a === 'number') return a;
    if (a == null) return 0;
    if (a.n != null) {
      const l = NARR[a.n]; if (!l) throw new Error('no narration line ' + a.n);
      return (a.f != null ? lerp(l.start, l.end, a.f) : (a.e === 'end' ? l.end : l.start)) + (a.d || 0);
    }
    const u = UNITS[(a.u || 1) - 1]; if (!u) throw new Error('no unit ' + a.u);
    let t;
    if (a.w == null) t = a.e === 'end' ? u.end : u.start;
    else {
      const w = u.words[a.w]; if (!w) throw new Error(`no word ${a.w} in unit ${a.u}`);
      t = a.f != null ? lerp(w.start, w.end, a.f) : (a.e === 'end' ? w.end : w.start);
    }
    return t + (a.d || 0);
  }

  // A layer's props at time t: static props, then each animation in order (later ones win).
  function propsAt(layer, t) {
    const p = Object.assign({}, layer);
    for (const an of layer.anim || []) {
      if (an.keys) {                                  // [[anchor, value], ...] piecewise
        const ks = an.keys.map(([k, v]) => [at(k), v]);
        let v = ks[0][1];
        for (let i = 0; i < ks.length - 1; i++) {
          const [ta, va] = ks[i], [tb, vb] = ks[i + 1];
          if (t >= tb) v = vb;
          else if (t >= ta) { v = lerp(va, vb, EASE[an.ease || 'inout'](clamp((t - ta) / Math.max(1e-3, tb - ta), 0, 1))); break; }
        }
        if (t < ks[0][0]) v = ks[0][1];
        p[an.prop] = v; continue;
      }
      const a0 = at(an.at), a1 = at(an.until);
      const u = EASE[an.ease || 'inout'](clamp((t - a0) / Math.max(1e-3, a1 - a0), 0, 1));
      if (typeof an.from === 'string' || typeof an.to === 'string') {   // pose blends: from/to are pose names
        const ub = EASE[an.ease || 'back'](clamp((t - a0) / Math.max(1e-3, a1 - a0), 0, 1));
        if (t >= a0) { p[an.prop] = an.from; p[an.prop + 'To'] = an.to; p[an.prop + 'Mix'] = ub; }
      } else if (t >= a0 || an.hold_before) p[an.prop] = lerp(an.from, an.to, u);
    }
    return p;
  }

  function camAt(sc, t) {
    const c = sc.camera || {}, a = Object.assign({ zoom: 1, x: 0.5, y: 0.5 }, c.from || c), b = Object.assign({}, a, c.to || {});
    const u = EASE[c.ease || 'inout'](clamp((t - at(sc.from)) / Math.max(1e-3, at(sc.to) - at(sc.from)), 0, 1));
    return { zoom: lerp(a.zoom, b.zoom, u), x: lerp(a.x, b.x, u), y: lerp(a.y, b.y, u) };
  }

  window.VAK = { W, H, clamp, lerp, EASE, rng, noise1, at, units: () => UNITS };
  window.setup = function (data) {
    PLAN = data.plan; UNITS = data.units; NARR = data.narration || []; T0 = data.t0 || 0; window.VAK_DATA = data;   // styles read extras (e.g. data.art)
    const cv = document.getElementById('c'); cv.width = W; cv.height = H;
    window.ctx = cv.getContext('2d');
    if (window.STYLE && STYLE.init) STYLE.init(ctx, PLAN);
    for (const sc of PLAN.scenes) for (const l of sc.layers) if (!STYLE.el[l.el]) throw new Error(`style '${STYLE.name}' has no element '${l.el}'`);
    return true;
  };
  window.draw = function (t) {
    const ctx = window.ctx;
    const sc = PLAN.scenes.find(s => t >= at(s.from) && t < at(s.to)) || PLAN.scenes[PLAN.scenes.length - 1];
    const env = { t, scene: sc, W, H, hands: {} };
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
    const cam = camAt(sc, t);
    ctx.save();
    ctx.translate(W / 2, H / 2); ctx.scale(cam.zoom, cam.zoom); ctx.translate(-cam.x * W, -cam.y * H);
    for (const l of sc.layers) {
      const p = propsAt(l, t); if (p.show === 0 || (p.layerA ?? 1) <= 0) continue;
      ctx.save(); ctx.globalAlpha = p.layerA ?? 1; STYLE.el[l.el](ctx, p, t, env); ctx.restore();
    }
    ctx.restore();
    if (STYLE.post) STYLE.post(ctx, t, env);
    // scene fades ("the lamp dims" between scenes; any style may restyle this in post)
    const fi = sc.fade_in ?? 0.5, fo = sc.fade_out ?? 0.5, t0 = at(sc.from), t1 = at(sc.to);
    let dim = 1;
    if (fi > 0) dim = Math.min(dim, clamp((t - t0) / fi, 0, 1));
    if (fo > 0) dim = Math.min(dim, clamp((t1 - t) / fo, 0, 1));
    if (dim < 1) { ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1 - dim; ctx.fillStyle = STYLE.fadeColor || '#000'; ctx.fillRect(0, 0, W, H); ctx.globalAlpha = 1; }
  };
})();
