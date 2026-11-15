// Vāk motion-graphics styles for chants without a story. Every frame is drawn from the time t (seconds on the chant's
// clock), the word timings and the live voice level A.amp, so the same code plays in the player and records to MP4.
//   rekha    Rekhā · line drawing   one gold line draws the deity's symbol; it moves only while the voice sounds
//   morph    Liquid forms           molten metal flows from shape to shape, one shape per line (bindu → drop → lotus …)
//   akshara  Akṣara · kinetic type  the sung words are the film: each word builds in light, then joins its line
// Registers into window.VakFX (vakfx.js must load first).
(function () {
  const FX = window.VakFX, TAU = Math.PI * 2;
  const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
  const ease = x => (x = clamp(x), x * x * (3 - 2 * x));
  const easeOut = x => 1 - Math.pow(1 - clamp(x), 3);
  const easeBack = x => { x = clamp(x); const c = 1.5; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };
  const css = (c, a = 1) => `rgba(${Math.round(c[0] * 255)},${Math.round(c[1] * 255)},${Math.round(c[2] * 255)},${a})`;
  const hash = n => { const s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); };
  const DEV = '"Tiro Devanagari Sanskrit", "Nirmala UI", serif', UI = 'Inter, system-ui, sans-serif';

  // time the voice has sounded by t (word intervals merged), so motion can follow the singing and rest in the pauses
  function voiced(W) {
    const iv = []; for (const w of W) { const a = w.start, b = Math.max(w.end, w.start + 0.05); if (iv.length && a <= iv[iv.length - 1][1]) iv[iv.length - 1][1] = Math.max(iv[iv.length - 1][1], b); else iv.push([a, b]); }
    const total = iv.reduce((s, [a, b]) => s + b - a, 0) || 1;
    return { total, at(t) { let s = 0; for (const [a, b] of iv) { if (t >= b) s += b - a; else { if (t > a) s += t - a; break; } } return s; },
      first: iv.length ? iv[0][0] : 0, last: iv.length ? iv[iv.length - 1][1] : 0 };
  }
  function unitIndex(units, t) {     // the line being sung, or the last one sung (held until the next starts)
    let k = -1; units.forEach((u, i) => { const s = u.words && u.words.length ? u.words[0].start : u.start; if (s != null && t >= s - 0.15) k = i; }); return k;
  }

  // =====================================================================================================
  // Rekhā: a single line of light draws the deity's symbol
  // =====================================================================================================
  // symbol = list of strokes; each stroke is a polyline in a unit square (x right, y down, about -1..1), plus whether it closes
  function pts(f, n) { const o = []; for (let i = 0; i <= n; i++) o.push(f(i / n)); return o; }
  const arc = (cx, cy, r, a0, a1, n = 90) => pts(u => [cx + r * Math.cos(a0 + (a1 - a0) * u), cy + r * Math.sin(a0 + (a1 - a0) * u)], n);
  const seg = (a, b, n = 24) => pts(u => [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u], n);
  const bez = (p0, p1, p2, p3, n = 40) => pts(u => { const v = 1 - u; return [v * v * v * p0[0] + 3 * v * v * u * p1[0] + 3 * v * u * u * p2[0] + u * u * u * p3[0], v * v * v * p0[1] + 3 * v * v * u * p1[1] + 3 * v * u * u * p2[1] + u * u * u * p3[1]]; }, n);
  const join = (...ps) => ps.reduce((a, p) => a.concat(a.length ? p.slice(1) : p), []);
  const mirror = s => s.map(([x, y]) => [-x, y]);
  function petal(bx, by, len, wid, ang) {            // a closed petal from its base, pointing along ang
    const ca = Math.cos(ang), sa = Math.sin(ang), P = (u, v) => [bx + u * ca - v * sa, by + u * sa + v * ca];
    return join(bez(P(0, 0), P(len * .25, -wid), P(len * .75, -wid * .8), P(len, 0)), bez(P(len, 0), P(len * .75, wid * .8), P(len * .25, wid), P(0, 0)));
  }
  function wave(y, x0, x1, amp, k, n = 80) { return pts(u => [x0 + (x1 - x0) * u, y + amp * Math.sin(u * k * TAU)], n); }
  const SYMBOLS = {
    lotus() {
      const S = [], base = [0, .38];
      S.push({ p: petal(base[0], base[1], .92, .2, -Math.PI / 2), fill: 1 });
      for (const [a, l, w] of [[.42, .8, .19], [.85, .66, .17], [1.25, .5, .14]]) { S.push({ p: petal(base[0], base[1], l, w, -Math.PI / 2 - a), fill: 1 }); S.push({ p: petal(base[0], base[1], l, w, -Math.PI / 2 + a), fill: 1 }); }
      S.push({ p: bez([-.62, .42], [-.3, .56], [.3, .56], [.62, .42]) });                     // the cup under the flower
      S.push({ p: arc(0, -.12, .86, -Math.PI * .95, Math.PI * .95 - TAU + TAU, 160).map(([x, y]) => [x, y]) });   // halo
      S.push({ p: arc(0, -.66, .045, 0, TAU, 30), fill: 1 });                              // bindu above
      S.push({ p: wave(.64, -.9, .9, .02, 3) }); S.push({ p: wave(.74, -.66, .66, .016, 2.5) }); S.push({ p: wave(.83, -.4, .4, .012, 2) });
      return S;
    },
    shiva() {
      const S = [];
      S.push({ p: join(seg([-1.25, .9], [-.78, .5]), seg([-.78, .5], [-.6, .62]), seg([-.6, .62], [-.3, .3]), seg([-.3, .3], [-.16, .42]), seg([.16, .42], [.4, .16]), seg([.4, .16], [.64, .5]), seg([.64, .5], [.8, .42]), seg([.8, .42], [1.25, .9])).filter(([x]) => Math.abs(x) > .15 || true) });   // Kailāsa
      S.push({ p: seg([0, .86], [0, -.36], 60) });                                         // the shaft
      S.push({ p: join(seg([-.11, .02], [.11, .02]), seg([.11, .02], [-.11, .24]), seg([-.11, .24], [.11, .24]), seg([.11, .24], [-.11, .02])), fill: 1 });   // ḍamaru
      S.push({ p: join(seg([0, -.36], [-.07, -.52]), seg([-.07, -.52], [0, -.86]), seg([0, -.86], [.07, -.52]), seg([.07, -.52], [0, -.36])), fill: 1 });    // centre blade
      const side = join(seg([0, -.36], [-.16, -.36], 10), bez([-.16, -.36], [-.36, -.36], [-.38, -.5], [-.34, -.74]));
      S.push({ p: side }); S.push({ p: mirror(side) });
      S.push({ p: join(arc(.4, -.62, .15, Math.PI * .75, Math.PI * 2.1, 70), arc(.46, -.66, .12, Math.PI * 2.05, Math.PI * .8, 70)), fill: 1 });   // crescent
      S.push({ p: arc(0, -.2, .78, Math.PI * .62, Math.PI * 2.38, 160) });                 // halo
      return S;
    },
    surya() {
      const S = [], c = [0, -.12];
      S.push({ p: arc(c[0], c[1], .3, -Math.PI / 2, Math.PI * 1.5, 120), fill: 1 });
      S.push({ p: arc(c[0], c[1], .19, -Math.PI / 2, Math.PI * 1.5, 90) });
      for (let i = 0; i < 12; i++) { const a = -Math.PI / 2 + i * TAU / 12, ca = Math.cos(a), sa = Math.sin(a), r0 = .38, r1 = i % 2 ? .58 : .68;
        S.push({ p: bez([c[0] + ca * r0, c[1] + sa * r0], [c[0] + ca * (r0 + .08) - sa * .05, c[1] + sa * (r0 + .08) + ca * .05], [c[0] + ca * (r1 - .08) + sa * .05, c[1] + sa * (r1 - .08) - ca * .05], [c[0] + ca * r1, c[1] + sa * r1], 24) }); }
      S.push({ p: seg([-1.1, .52], [1.1, .52], 60) });
      S.push({ p: wave(.64, -.8, .8, .018, 3) }); S.push({ p: wave(.74, -.55, .55, .014, 2.5) }); S.push({ p: wave(.83, -.32, .32, .01, 2) });
      return S;
    },
  };
  const SYMBOL_OF = { shiva: 'shiva', surya: 'surya', devi: 'lotus', vishnu: 'lotus', ganesha: 'lotus', peace: 'lotus' };

  function rekha(cv, opts) {
    cv.width = 1280; cv.height = 720;
    const ctx = cv.getContext('2d'), W = cv.width, H = cv.height, P = FX.PAL[opts.deity] || FX.PAL.peace;
    const strokes = SYMBOLS[SYMBOL_OF[opts.deity] || 'lotus']();
    // one continuous pen path: strokes in order, with travel moves between them (drawn faintly)
    const path = [];                                   // {x, y, s (arc length), k (stroke index), travel}
    let L = 0, prev = null;
    strokes.forEach((st, k) => {
      st.p.forEach((q, i) => {
        if (prev) L += Math.hypot(q[0] - prev[0], q[1] - prev[1]) * (i === 0 ? 0.35 : 1);   // travel counts less: the pen hurries
        path.push({ x: q[0], y: q[1], s: L, k, travel: i === 0 }); prev = q;
      });
      st.end = L;
    });
    const Wd = FX.words(opts.units), V = voiced(Wd), widths = new Float32Array(path.length).fill(-1);
    const units = opts.units || [];
    const lineEnds = units.map(u => (u.words && u.words.length ? u.words[u.words.length - 1].end : u.end) || 0);
    const scale = H * 0.4, cx = W / 2, cy = H * 0.5;
    const grain = document.createElement('canvas'); grain.width = 256; grain.height = 256;
    { const g = grain.getContext('2d'), im = g.createImageData(256, 256); for (let i = 0; i < im.data.length; i += 4) { const v = 128 + (hash(i) - .5) * 60; im.data[i] = im.data[i + 1] = im.data[i + 2] = v; im.data[i + 3] = 14; } g.putImageData(im, 0, 0); }
    let lastT = -1;
    function penAt(s) { let lo = 0, hi = path.length - 1; while (lo < hi) { const m = (lo + hi + 1) >> 1; if (path[m].s <= s) lo = m; else hi = m - 1; } return lo; }
    function frame(t, A) {
      if (t < lastT - 0.5) widths.fill(-1); lastT = t;
      const prog = V.total ? clamp(V.at(t) / V.total) : 0, s = prog * L, n = penAt(s), done = t > V.last + 0.2;
      const after = clamp((t - V.last) / 2.5);
      // camera: close on the pen while drawing, pulling back to the whole symbol at the end
      const pa = path[penAt(Math.max(0, s - L * 0.04))], z = 1 + 0.22 * (1 - ease(after)) * ease((t - V.first + 1) / 2);
      const fx = (1 - ease(after)) * 0.35, ox = -pa.x * fx, oy = -pa.y * fx;
      const X = x => cx + ((x + ox) * z) * scale, Y = y => cy + ((y + oy) * z) * scale;
      // background: deep night of the deity's colour, soft centre light, paper grain
      const bg = ctx.createRadialGradient(cx, cy * .9, 10, cx, cy, W * .75);
      bg.addColorStop(0, css(P.deep.map(c => c * 1.25 + .02))); bg.addColorStop(.55, css(P.water.map(c => c + .01))); bg.addColorStop(1, '#000');
      ctx.globalCompositeOperation = 'source-over'; ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);
      ctx.fillStyle = ctx.createPattern(grain, 'repeat'); ctx.fillRect(0, 0, W, H);
      // faint dot grid, like a kolam layout, that the drawing sits on
      ctx.fillStyle = css(P.gold, .07);
      for (let gx = -12; gx <= 12; gx++) for (let gy = -7; gy <= 7; gy++) { const x = X(gx * .16), y = Y(gy * .16); if (x > -5 && x < W + 5 && y > -5 && y < H + 5) ctx.fillRect(x - 1, y - 1, 2, 2); }
      // colour floods closed shapes when their line has been sung (and everything at the end)
      const fillA = k => { const st = strokes[k]; if (!st.fill || st.end > s + 1e-6) return 0; let a = 0; lineEnds.forEach(e => { if (t > e) a = Math.max(a, clamp((t - e) / 1.2)); }); return Math.max(a * .55, after * .9); };
      ctx.globalCompositeOperation = 'lighter';
      strokes.forEach((st, k) => { const a = fillA(k); if (a <= 0) return;
        ctx.beginPath(); st.p.forEach((q, i) => i ? ctx.lineTo(X(q[0]), Y(q[1])) : ctx.moveTo(X(q[0]), Y(q[1]))); ctx.closePath();
        const g = ctx.createRadialGradient(X(st.p[0][0]), Y(st.p[0][1]), 2, X(st.p[0][0]), Y(st.p[0][1]), scale * .9);
        g.addColorStop(0, css(P.dye[0], .32 * a)); g.addColorStop(1, css(P.dye[1], .12 * a)); ctx.fillStyle = g; ctx.fill(); });
      // the line: a wide soft glow pass, then the bright core; width follows the voice when it was drawn
      const amp = A && A.amp ? A.amp : 0;
      for (let i = 0; i <= n; i++) if (widths[i] < 0) { const w = Wd.find(x => t >= x.start && t <= x.end); widths[i] = 1.4 + (amp ? amp * 3.2 : (w ? 1.4 + Math.sin((t - w.start) / Math.max(.2, w.end - w.start) * Math.PI) : .6)); }
      // glow passes: one path per stroke at the stroke's mean width; core pass: variable width, butt joins, no overlap glow
      ctx.lineCap = 'round'; ctx.lineJoin = 'round';
      const runs = []; { let i = 1; while (i <= n) { if (path[i].travel) { i++; continue; } const k = path[i].k; let j = i; while (j + 1 <= n && path[j + 1].k === k && !path[j + 1].travel) j++; runs.push([i - 1, j]); i = j + 1; } }
      const glowK = 1 + after * .25, glowA = 1 + after * .4;
      for (const [wm, al, col] of [[9, .06, P.gold], [3.4, .2, P.gold]]) {
        ctx.strokeStyle = css(col, al * glowA);
        for (const [a, b] of runs) { let m = 0; for (let q = a; q <= b; q++) m += Math.max(widths[q], 1.4); m /= (b - a + 1);
          ctx.beginPath(); ctx.moveTo(X(path[a].x), Y(path[a].y)); for (let q = a + 1; q <= b; q++) ctx.lineTo(X(path[q].x), Y(path[q].y)); ctx.lineWidth = m * wm * glowK; ctx.stroke(); }
      }
      ctx.globalCompositeOperation = 'source-over'; ctx.strokeStyle = css(P.hot, .95); ctx.lineCap = 'butt';
      for (const [a, b] of runs) for (let q = a + 1; q <= b; q++) { ctx.beginPath(); ctx.moveTo(X(path[q - 1].x), Y(path[q - 1].y)); ctx.lineTo(X(path[q].x), Y(path[q].y)); ctx.lineWidth = Math.max(widths[q], 1.4) * glowK; ctx.stroke(); }
      ctx.lineCap = 'round'; ctx.globalCompositeOperation = 'lighter';
      // the pen: a bright point with sparks, resting (breathing) in the pauses
      if (!done && t > V.first - 0.6) {
        const p = path[n], x = X(p.x), y = Y(p.y), sounding = Wd.some(w => t >= w.start && t <= w.end), r = (sounding ? 16 : 10) + amp * 26 + Math.sin(t * 3) * 2;
        const g = ctx.createRadialGradient(x, y, 0, x, y, r * 3); g.addColorStop(0, css(P.hot, .95)); g.addColorStop(.2, css(P.gold, .5)); g.addColorStop(1, css(P.gold, 0));
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r * 3, 0, TAU); ctx.fill();
        for (let k = 0; k < 14; k++) { const age = ((t * 1.7 + hash(k)) % 1), a = hash(k + 9) * TAU, d = age * (24 + 40 * hash(k + 3)) * (sounding ? 1 : .4);
          ctx.fillStyle = css(P.hot, (1 - age) * .8); ctx.fillRect(x + Math.cos(a) * d, y + Math.sin(a) * d - age * 10, 2, 2); }
      }
      // at the end the finished symbol breathes with light
      if (after > 0) { const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, W * .5); g.addColorStop(0, css(P.gold, .1 * after * (.8 + .2 * Math.sin(t * 1.4)))); g.addColorStop(1, css(P.gold, 0)); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); }
      ctx.globalCompositeOperation = 'source-over';
      const vg = ctx.createRadialGradient(cx, cy, H * .35, cx, cy, W * .7); vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(0,0,0,.55)'); ctx.fillStyle = vg; ctx.fillRect(0, 0, W, H);
      ctx.globalAlpha = clamp(t + 1); ctx.globalAlpha = 1;
    }
    return { frame, reset() { widths.fill(-1); } };
  }

  // =====================================================================================================
  // Liquid forms: molten metal morphing between sacred shapes, one shape per line
  // =====================================================================================================
  const SHAPES = { bindu: 0, drop: 1, lotus: 2, sun: 3, crescent: 4, flame: 5, trident: 6 };
  const SEQ = { shiva: ['drop', 'crescent', 'trident', 'bindu'], surya: ['sun', 'lotus', 'drop', 'sun'], devi: ['flame', 'lotus', 'sun', 'flame'],
    vishnu: ['lotus', 'drop', 'sun', 'lotus'], ganesha: ['drop', 'lotus', 'flame', 'sun'], peace: ['drop', 'lotus', 'flame', 'sun'] };
  function morph(cv, opts) {
    cv.width = 1280; cv.height = 720;
    const gl = cv.getContext('webgl', { antialias: false, alpha: false, preserveDrawingBuffer: true }), P = FX.PAL[opts.deity] || FX.PAL.peace;
    const fs = `precision highp float;uniform vec2 res;uniform float t,amp,sa,sb,mixk,pulse,wobble,orbit;uniform vec3 water,deep,mid,gold,hot,dye1;
    float smin(float a,float b,float k){float h=clamp(.5+.5*(b-a)/k,0.,1.);return mix(b,a,h)-k*h*(1.-h);}
    float cap(vec2 p,vec2 a,vec2 b,float r){vec2 pa=p-a,ba=b-a;float h=clamp(dot(pa,ba)/dot(ba,ba),0.,1.);return length(pa-ba*h)-r;}
    float ucap(vec2 p,float r1,float r2,float h){p.x=abs(p.x);float b=(r1-r2)/h,a=sqrt(1.-b*b),k=dot(p,vec2(-b,a));
      if(k<0.)return length(p)-r1;if(k>a*h)return length(p-vec2(0.,h))-r2;return dot(p,vec2(a,b))-r1;}
    float shape(float id,vec2 p){
      if(id<.5)return length(p)-.13;
      if(id<1.5)return ucap(p-vec2(0.,-.14),.2,.01,.5);
      if(id<2.5){vec2 b=p-vec2(0.,-.24);float d=1e3;                          // lotus: five petals rising from one base
        for(int i=0;i<5;i++){float fi=float(i)-2.,an=fi*.5,c=cos(an),s=sin(an);vec2 q=vec2(c*b.x-s*b.y,s*b.x+c*b.y);
          d=smin(d,ucap(q-vec2(0.,.03),.075,.012,.44-.07*abs(fi)),.035);}
        return smin(d,length(vec2(p.x*.55,p.y+.25))-.11,.06);}
      if(id<3.5){float an=atan(p.y,p.x),sec=6.2831853/12.,a=mod(an+sec*.5,sec)-sec*.5;vec2 q=length(p)*vec2(cos(a),sin(a));
        return smin(length(p)-.19,cap(q,vec2(.25,0.),vec2(.33,0.),.026),.05);}
      if(id<4.5)return max(length(p)-.28,-(length(p-vec2(.12,.07))-.25));
      if(id<5.5){vec2 q=p-vec2(0.,-.16);q.x+=.035*sin(q.y*9.-t*3.)*smoothstep(0.,.4,q.y);return ucap(q,.17,.005,.58);}
      vec2 q=vec2(abs(p.x),p.y);float d=cap(p,vec2(0.,-.42),vec2(0.,.2),.024);d=smin(d,cap(p,vec2(0.,.2),vec2(0.,.44),.032),.03);
      d=smin(d,cap(q,vec2(0.,.12),vec2(.16,.18),.024),.04);d=smin(d,cap(q,vec2(.16,.18),vec2(.18,.4),.024),.04);return d;}
    float field(vec2 p){
      float d=mix(shape(sa,p),shape(sb,p),mixk);
      d+=.012*sin(p.x*11.+t*1.7)*sin(p.y*9.-t*1.3)*(.4+wobble*2.);
      for(int i=0;i<5;i++){float fi=float(i),a=t*(.22+fi*.04)+fi*1.2566;float rr=.42+.08*sin(t*.5+fi*2.)-orbit*.25;
        vec2 c=vec2(cos(a),sin(a)*.62)*rr;d=smin(d,length(p-c)-(.025+.018*sin(t+fi)+amp*.02),.09);}
      return d-pulse*.03;}
    vec3 env(vec3 r){float y=r.y;vec3 c=mix(deep*.6,mid,smoothstep(-.6,.6,y));c+=hot*pow(max(0.,1.-abs(y-.35)*3.5),3.)*1.3;
      c+=gold*pow(max(0.,1.-abs(r.x+.4)*2.),4.)*.8;return c;}
    void main(){vec2 uv=(gl_FragCoord.xy-.5*res)/res.y;vec2 p=uv*1.32;
      float d=field(p);float e=.0025;
      vec3 bg=mix(water,deep*.7,smoothstep(.9,0.,length(uv)));bg+=gold*.04*exp(-length(uv)*2.5);
      float caus=pow(abs(sin(uv.x*14.+sin(uv.y*9.+t*.4)*2.)*sin(uv.y*12.+t*.3)),6.);bg+=gold*caus*.025;
      vec3 col=bg;
      col+=mix(mid,dye1,.5)*exp(-max(d,0.)*16.)*(.22+amp*.5);                          // glow around the form
      if(d<0.){float E=.022;
        float hx1=sqrt(max(-field(p+vec2(E,0.)),0.)),hx0=sqrt(max(-field(p-vec2(E,0.)),0.)),hy1=sqrt(max(-field(p+vec2(0.,E)),0.)),hy0=sqrt(max(-field(p-vec2(0.,E)),0.));
        float h=sqrt(-d);vec3 n=normalize(vec3((hx0-hx1)/(2.*E)*.09,(hy0-hy1)/(2.*E)*.09,1.));vec3 v=vec3(0.,0.,1.),r=reflect(-v,n);
        vec3 m=env(r)*gold*1.25;float fr=pow(1.-n.z,2.);m=mix(m,hot,fr*.35);
        float spec=pow(max(0.,dot(r,normalize(vec3(-.4,.6,.7)))),40.);m+=hot*spec*1.4;
        m*=.55+.45*h;col=mix(col,m,smoothstep(0.,-.004,d));}
      col*=1.-.45*dot(uv,uv);gl_FragColor=vec4(pow(col,vec3(.92)),1.);}`;
    const vs = 'attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}';
    const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; };
    const pr = gl.createProgram(); gl.attachShader(pr, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(pr, sh(gl.FRAGMENT_SHADER, fs)); gl.linkProgram(pr); gl.useProgram(pr);
    const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(pr, 'p'); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    const U = n => gl.getUniformLocation(pr, n);
    for (const k of ['water', 'deep', 'mid', 'gold', 'hot']) gl.uniform3fv(U(k), P[k]); gl.uniform3fv(U('dye1'), P.dye[0]);
    const units = opts.units || [], Wd = FX.words(units), seq = SEQ[opts.deity] || SEQ.peace;
    const starts = units.map(u => (u.words && u.words.length ? u.words[0].start : u.start) || 0);
    const shapeOf = k => SHAPES[k < 0 ? 'bindu' : seq[k % seq.length]];
    let amp = 0;
    function frame(t, A) {
      amp = A && A.amp ? A.amp : 0;
      let k = -1; starts.forEach((s, i) => { if (t >= s - 0.45) k = i; });
      const from = shapeOf(k - 1), to = shapeOf(k), m = k < 0 ? 1 : ease((t - (starts[k] - 0.45)) / 1.1);
      const w = Wd.filter(x => t >= x.start - .05).pop(), age = w ? t - w.start : 9;
      const pulse = Math.exp(-age * 3) * 1.0 + amp * .6;
      const sounding = Wd.some(x => t >= x.start && t <= x.end), orbit = sounding ? .3 + amp * .7 : 0;
      gl.viewport(0, 0, cv.width, cv.height); gl.uniform2f(U('res'), cv.width, cv.height); gl.uniform1f(U('t'), t);
      gl.uniform1f(U('amp'), amp); gl.uniform1f(U('sa'), from); gl.uniform1f(U('sb'), to); gl.uniform1f(U('mixk'), m);
      gl.uniform1f(U('pulse'), pulse); gl.uniform1f(U('wobble'), amp + (sounding ? .25 : 0)); gl.uniform1f(U('orbit'), orbit);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    }
    return { frame, reset() {} };
  }

  // =====================================================================================================
  // Akṣara: kinetic Devanagari type; the words build in light and gather into their line
  // =====================================================================================================
  function akshara(cv, opts) {
    cv.width = 1280; cv.height = 720;
    const ctx = cv.getContext('2d'), W = cv.width, H = cv.height, P = FX.PAL[opts.deity] || FX.PAL.peace, units = opts.units || [];
    const ROW = H * 0.74, HERO = H * 0.43, rowSize = 40;
    const lay = units.map(u => {                       // each line's words laid out centred in the row
      ctx.font = `${rowSize}px ${DEV}`; const ws = (u.words || []).map(w => ({ w, wd: ctx.measureText(w.dev).width })), gap = rowSize * .45;
      let tot = ws.reduce((s, x) => s + x.wd, 0) + gap * Math.max(0, ws.length - 1), sc = Math.min(1, (W * .86) / Math.max(1, tot));
      let x = W / 2 - tot * sc / 2; ws.forEach(o => { o.x = x + o.wd * sc / 2; o.sc = sc; x += (o.wd + gap) * sc; }); return ws;
    });
    const ink = css(P.hot), sig = css(P.gold), dim = 'rgba(255,255,255,.2)';
    function heroSize(dev) { ctx.font = `200px ${DEV}`; const w = ctx.measureText(dev).width; return Math.min(200, 200 * (W * .8) / Math.max(1, w)); }
    function frame(t, A) {
      const amp = A && A.amp ? A.amp : 0, k = unitIndex(units, t), last = units.length - 1;
      const endT = units.length ? (units[last].words && units[last].words.length ? units[last].words[units[last].words.length - 1].end : units[last].end) : 0;
      const fin = clamp((t - endT - .8) / 1.4);
      // background: one dark field, a 12-column grid, one signal colour
      const bg = ctx.createLinearGradient(0, 0, 0, H); bg.addColorStop(0, css(P.deep.map(c => c * .9))); bg.addColorStop(1, css(P.water));
      ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);
      ctx.strokeStyle = 'rgba(255,255,255,.035)'; ctx.lineWidth = 1;
      for (let i = 1; i < 12; i++) { const x = Math.round(W * i / 12) + .5; ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
      ctx.beginPath(); ctx.moveTo(0, Math.round(ROW + 34) + .5); ctx.lineTo(W, Math.round(ROW + 34) + .5); ctx.stroke();
      if (fin > 0) { finale(t, fin, amp); return; }
      if (k < 0) {                                     // before the first word: the title waits, the grid breathes
        ctx.fillStyle = 'rgba(255,255,255,.5)'; ctx.font = `600 13px ${UI}`; ctx.textAlign = 'left'; ctx.fillText('ॐ', W / 12 + 8, 44); return;
      }
      const u = units[k], L = lay[k], ws = u.words || [];
      const uStart = ws.length ? ws[0].start : u.start, prevEnd = k > 0 ? starts(k - 1) : 0;
      // the line row slides in from below as it begins
      const inRow = easeOut((t - uStart + .5) / .6);
      // counters and labels, Swiss style
      ctx.textAlign = 'left'; ctx.fillStyle = sig; ctx.font = `700 13px ${UI}`;
      ctx.fillText(String(k + 1).padStart(2, '0'), W / 12 + 8, 44);
      ctx.fillStyle = 'rgba(255,255,255,.45)'; ctx.font = `500 13px ${UI}`; ctx.fillText('/ ' + String(units.length).padStart(2, '0'), W / 12 + 32, 44);
      ctx.fillStyle = sig; ctx.fillRect(W / 12 + 8, 54, (W * 10 / 12 - 16) * clamp((t - (units[0].words[0] || units[0]).start) / Math.max(1, endT - (units[0].words[0] || units[0]).start)), 2);
      // the row: sung words solid, the current one in the signal colour, the rest as outlines
      ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
      L.forEach((o, i) => {
        const w = o.w, y = ROW + (1 - inRow) * 40, sung = t >= w.end, cur = t >= w.start - .12 && t < w.end;
        const nxt = ws[i + 1], heroOut = nxt ? easeOut((t - nxt.start + .12) / .35) : (k < last ? easeOut((t - starts(k + 1) + .3) / .4) : 0);
        if (t >= w.start - .12 && heroOut < 1) return;  // this word is in the centre right now
        ctx.font = `${rowSize * o.sc}px ${DEV}`; ctx.globalAlpha = inRow;
        if (sung || (t >= w.start - .12)) { ctx.fillStyle = ink; ctx.fillText(w.dev, o.x, y); }
        else { ctx.strokeStyle = dim; ctx.lineWidth = 1; ctx.strokeText(w.dev, o.x, y); }
        ctx.globalAlpha = 1;
      });
      ctx.fillStyle = 'rgba(255,255,255,.55)'; ctx.font = `italic 17px ${UI}`; ctx.globalAlpha = inRow; ctx.fillText(u.iast || '', W / 2, ROW + 62);
      const lineDone = ws.length && t > ws[ws.length - 1].end + .1;
      if (u.english) { ctx.fillStyle = css(P.gold, .9); ctx.font = `500 19px ${UI}`; ctx.globalAlpha = inRow * clamp((t - (ws.length ? ws[ws.length - 1].end : uStart)) / .6); ctx.fillText(u.english, W / 2, ROW + 96); }
      ctx.globalAlpha = 1;
      // the hero word: flies up from its slot, builds left to right in time with the voice, then returns to the row
      ws.forEach((w, i) => {
        const o = L[i]; if (t < w.start - .12) return;
        const nxt = ws[i + 1], back = nxt ? easeOut((t - nxt.start + .12) / .35) : (k < last ? easeOut((t - starts(k + 1) + .3) / .4) : (lineDone ? ease((t - w.end - .6) / .6) : 0));
        if (back >= 1) return;
        const up = easeBack((t - w.start + .12) / .4), m = up * (1 - back), fadeA = 1 - clamp(back * 1.6);
        const hs = heroSize(w.dev), size = rowSize * o.sc + (hs - rowSize * o.sc) * m;
        const x = o.x + (W / 2 - o.x) * m, y = ROW + (HERO + hs * .32 - ROW) * m;
        const rev = clamp((t - w.start) / Math.max(.25, w.end - w.start));
        ctx.font = `${size}px ${DEV}`; const tw = ctx.measureText(w.dev).width;
        ctx.globalAlpha = back > 0 ? fadeA : 1;
        if (back === 0 && up > .7) { ctx.strokeStyle = `rgba(255,255,255,${.22 * m})`; ctx.lineWidth = 1.2; ctx.strokeText(w.dev, x, y); }   // the rest of the word, waiting in outline
        ctx.save(); ctx.beginPath(); ctx.rect(x - tw / 2 - 4, y - size * 1.2, (tw + 8) * (back > 0 ? 1 : rev), size * 1.6); ctx.clip();
        ctx.shadowColor = css(P.gold, .75); ctx.shadowBlur = (18 + amp * 46) * m;
        const g = ctx.createLinearGradient(0, y - size * .8, 0, y + size * .2); g.addColorStop(0, css(P.hot)); g.addColorStop(.7, css(P.gold)); g.addColorStop(1, css(P.dye[1]));
        ctx.fillStyle = m > .3 ? g : ink; ctx.fillText(w.dev, x, y); ctx.restore();
        if (back === 0 && rev < 1 && m > .5) {          // the writing edge: a thin line of light with a soft halo
          const ex = x - tw / 2 + (tw + 8) * rev - 4, top = y - size * .92, h = size * 1.12;
          const eg = ctx.createLinearGradient(0, top, 0, top + h); eg.addColorStop(0, css(P.hot, 0)); eg.addColorStop(.5, css(P.hot, .9)); eg.addColorStop(1, css(P.hot, 0));
          ctx.save(); ctx.shadowColor = css(P.gold, .9); ctx.shadowBlur = 18 + amp * 30; ctx.fillStyle = eg; ctx.fillRect(ex - 1, top, 2, h); ctx.restore();
          const sg = ctx.createRadialGradient(ex, y - size * .36, 0, ex, y - size * .36, 22 + amp * 30); sg.addColorStop(0, css(P.hot, .5)); sg.addColorStop(1, css(P.hot, 0));
          ctx.fillStyle = sg; ctx.fillRect(ex - 60, y - size * .36 - 60, 120, 120);
        }
        if (m > .6) {                                   // a rule under the hero that grows with the word, then its sense
          ctx.fillStyle = sig; ctx.fillRect(W / 2 - tw / 2, y + size * .2, tw * rev, 3);
          ctx.globalAlpha = clamp((m - .6) / .4) * fadeA; ctx.fillStyle = 'rgba(255,255,255,.8)'; ctx.font = `italic 20px ${UI}`;
          ctx.fillText(w.split || w.iast || '', W / 2, y + size * .2 + 34);
          if (w.meaning) { ctx.fillStyle = 'rgba(255,255,255,.55)'; ctx.font = `15px ${UI}`; ctx.fillText(w.meaning.length > 90 ? w.meaning.slice(0, 88) + '…' : w.meaning, W / 2, y + size * .2 + 58); }
          ctx.globalAlpha = 1;
        }
        ctx.globalAlpha = 1;
      });
      void prevEnd;
    }
    function starts(i) { const u = units[i]; return u.words && u.words.length ? u.words[0].start : u.start; }
    function finale(t, fin, amp) {                     // the whole chant, set like a title page
      const n = units.length, lh = Math.min(70, (H * .62) / Math.max(1, n)), top = H / 2 - lh * (n - 1) / 2;
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      units.forEach((u, i) => {
        const a = easeOut(fin * 1.6 - i * .15); ctx.globalAlpha = a;
        ctx.font = `${Math.min(46, lh * .66)}px ${DEV}`; ctx.fillStyle = ink; ctx.shadowColor = css(P.gold, .5); ctx.shadowBlur = 14 + amp * 20;
        ctx.fillText(u.devanagari, W / 2, top + i * lh + (1 - a) * 20); ctx.shadowBlur = 0;
      });
      ctx.globalAlpha = fin; ctx.fillStyle = sig; const rw = W * .3 * easeOut(fin);
      ctx.fillRect(W / 2 - rw / 2, top - lh * .75, rw, 2); ctx.fillRect(W / 2 - rw / 2, top + lh * (n - .25), rw, 2);
      ctx.globalAlpha = 1; ctx.textBaseline = 'alphabetic';
    }
    return { frame, reset() {} };
  }

  // =====================================================================================================
  // Kaṇa: particles of light gather into ॐ, then into each sung word, then into the deity's symbol
  // =====================================================================================================
  function kana(cv, opts) {
    // drawn at the screen's real resolution (CSS size x device pixel ratio, 1280-2560 wide); the motion itself runs in a
    // 1280x720 design space, so it looks the same at any size
    const box = cv.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
    const RW = Math.round(clamp(box.width ? box.width * dpr : 1920, 1280, 2560)), RH = Math.round(RW * 9 / 16), K = RW / 1280;
    cv.width = RW; cv.height = RH;
    const W = 1280, H = 720, N = 26000, P = FX.PAL[opts.deity] || FX.PAL.peace;
    const gl = cv.getContext('webgl', { antialias: false, alpha: false, preserveDrawingBuffer: true });
    const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; };
    const prog = (vs, fs) => { const p = gl.createProgram(); gl.attachShader(p, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(p, sh(gl.FRAGMENT_SHADER, fs)); gl.linkProgram(p); return p; };
    // background: the deity's night, a soft light behind the form
    const bgP = prog('attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}',
      `precision mediump float;uniform vec2 res;uniform vec3 water,deep,gold;uniform float glow;
       void main(){vec2 uv=(gl_FragCoord.xy-.5*res)/res.y;float r=length(uv-vec2(0.,.05));
       vec3 c=mix(deep*.75,water,smoothstep(0.,.95,r));c+=gold*.06*glow*exp(-r*3.);c*=1.-.35*dot(uv,uv);gl_FragColor=vec4(c,1.);}`);
    const ptP = prog(`attribute vec2 pos;attribute vec2 a;uniform vec2 res;uniform float scale,amp,grow;varying float vk,vb;
       void main(){vec2 q=pos/res*2.-1.;gl_Position=vec4(q.x,-q.y,0.,1.);vk=a.x;vb=a.y;gl_PointSize=scale*(1.+a.x*grow)*(1.+amp*.45);}`,
      `precision mediump float;uniform vec3 c1,c2,hot;uniform float alpha,soft;varying float vk,vb;
       void main(){vec2 d=gl_PointCoord-.5;float r=dot(d,d)*4.;if(r>1.)discard;
       float s=soft>.5?exp(-r*2.5)*(1.-r):smoothstep(1.,.15,r);
       vec3 c=mix(c1,c2,vk*.6);c=mix(c,hot,clamp(vb*.8+(1.-soft)*.25,0.,1.));gl_FragColor=vec4(c*s*alpha*(.6+vb),1.);}`);
    const quad = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, quad); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const posB = gl.createBuffer(), attB = gl.createBuffer();
    const pos = new Float32Array(N * 2), vel = new Float32Array(N * 2), att = new Float32Array(N * 2), seed = new Float32Array(N);
    for (let i = 0; i < N; i++) { seed[i] = hash(i * 1.7); att[i * 2] = hash(i * 3.1); att[i * 2 + 1] = 0; pos[i * 2] = W / 2 + (hash(i * 5.3) - .5) * W * 1.3; pos[i * 2 + 1] = H / 2 + (hash(i * 7.9) - .5) * H * 1.3; }
    // targets: N points sampled from a shape drawn on a small canvas (a word, ॐ or the symbol), cached by name
    const off = document.createElement('canvas'); off.width = W; off.height = H; const oc = off.getContext('2d', { willReadFrequently: true });
    const cache = new Map();
    function sample(draw, key) {
      if (cache.has(key)) return cache.get(key);
      oc.clearRect(0, 0, W, H); oc.fillStyle = '#fff'; oc.strokeStyle = '#fff'; draw(oc);     // full design resolution: crisp letter edges
      const d = oc.getImageData(0, 0, W, H).data, pts = [];
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (d[(y * W + x) * 4 + 3] > 140) pts.push(x, y);
      const tg = new Float32Array(N * 2), m = pts.length / 2 || 1;
      for (let i = 0; i < N; i++) { const j = Math.floor(hash(i * 12.9898 + key.length) * m) * 2; tg[i * 2] = pts[j] + hash(i * 4.4); tg[i * 2 + 1] = pts[j + 1] + hash(i * 8.8); }
      cache.set(key, tg); return tg;
    }
    function textTarget(s) {
      return sample(c => { let fs = 320; c.font = `${fs}px ${DEV}`; const w = c.measureText(s).width; fs = Math.min(fs, fs * 1120 / Math.max(1, w)); c.font = `${fs}px ${DEV}`;
        c.textAlign = 'center'; c.textBaseline = 'alphabetic'; const m = c.measureText(s);   // centred on the glyphs' actual ink
        c.fillText(s, 640, 300 + (m.actualBoundingBoxAscent - m.actualBoundingBoxDescent) / 2); }, 't:' + s);
    }
    const strokes = SYMBOLS[SYMBOL_OF[opts.deity] || 'lotus']();
    function symbolTarget() {
      return sample(c => { c.lineWidth = 5; c.lineCap = 'round'; c.lineJoin = 'round';
        for (const st of strokes) { c.beginPath(); st.p.forEach(([x, y], i) => { const X = 640 + x * 300, Y = 350 + y * 300; if (i) c.lineTo(X, Y); else c.moveTo(X, Y); }); c.stroke(); } }, 'symbol');
    }
    const units = opts.units || [], Wd = FX.words(units), V = voiced(Wd);
    let cur = null, curKey = '', lastT = -1, changedAt = -9;
    function targetFor(t) {
      const m = modeAt(Wd, V, t);
      if (m.w) return [m.key, () => textTarget(m.w.dev)];
      if (m.key === 'pre') return ['om', () => textTarget('ॐ')];
      return ['symbol', symbolTarget];
    }
    function frame(t, A) {
      const amp = A && A.amp ? A.amp : 0, jump = lastT >= 0 && Math.abs(t - lastT) > 1.2;
      const dt = jump || lastT < 0 ? 0 : clamp(t - lastT, 0, 1 / 20); lastT = t;
      const [key, mk] = targetFor(t);
      if (key !== curKey) { curKey = key; cur = mk(); changedAt = t;
        for (let i = 0; i < N; i++) { const a = seed[i] * TAU, k = 40 + 120 * hash(i + t); vel[i * 2] += Math.cos(a) * k; vel[i * 2 + 1] += Math.sin(a) * k; } }   // a burst as the form changes
      if (jump) { pos.set(cur); vel.fill(0); }
      const since = t - changedAt, stiff = 70 + 190 * ease(since / .45), damp = Math.exp(-15 * dt), turb = 110 + amp * 1300, tt = t * .6;
      for (let i = 0; i < N; i++) {
        const ix = i * 2, x = pos[ix], y = pos[ix + 1], s = seed[i];
        const nx = Math.sin(y * .011 + tt + s * 6) + Math.sin(y * .023 - tt * 1.3 + s * 3), ny = Math.cos(x * .012 - tt + s * 5) + Math.cos(x * .021 + tt * 1.1);
        const loose = s < .05 ? 2.2 : 1;                  // a few grains drift free, like dust in a sunbeam
        vel[ix] = (vel[ix] + ((cur[ix] - x) * stiff / loose + nx * turb * loose) * dt) * damp;
        vel[ix + 1] = (vel[ix + 1] + ((cur[ix + 1] - y) * stiff / loose + ny * turb * loose - (s < .05 ? 14 : 0)) * dt) * damp;
        pos[ix] = x + vel[ix] * dt; pos[ix + 1] = y + vel[ix + 1] * dt;
        att[ix + 1] = clamp(Math.hypot(vel[ix], vel[ix + 1]) / 260);    // fast grains burn hotter
      }
      gl.viewport(0, 0, RW, RH); gl.disable(gl.BLEND);
      gl.useProgram(bgP); gl.bindBuffer(gl.ARRAY_BUFFER, quad); let l = gl.getAttribLocation(bgP, 'p'); gl.enableVertexAttribArray(l); gl.vertexAttribPointer(l, 2, gl.FLOAT, false, 0, 0);
      gl.uniform2f(gl.getUniformLocation(bgP, 'res'), RW, RH); for (const k of ['water', 'deep', 'gold']) gl.uniform3fv(gl.getUniformLocation(bgP, k), P[k]);
      gl.uniform1f(gl.getUniformLocation(bgP, 'glow'), .6 + amp * 1.5); gl.drawArrays(gl.TRIANGLES, 0, 3);
      gl.disableVertexAttribArray(l);
      gl.useProgram(ptP); gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE);
      gl.bindBuffer(gl.ARRAY_BUFFER, posB); gl.bufferData(gl.ARRAY_BUFFER, pos, gl.DYNAMIC_DRAW); l = gl.getAttribLocation(ptP, 'pos'); gl.enableVertexAttribArray(l); gl.vertexAttribPointer(l, 2, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, attB); gl.bufferData(gl.ARRAY_BUFFER, att, gl.DYNAMIC_DRAW); const l2 = gl.getAttribLocation(ptP, 'a'); gl.enableVertexAttribArray(l2); gl.vertexAttribPointer(l2, 2, gl.FLOAT, false, 0, 0);
      const u = n => gl.getUniformLocation(ptP, n);
      gl.uniform2f(u('res'), W, H); gl.uniform1f(u('amp'), amp);
      gl.uniform3fv(u('c1'), P.gold); gl.uniform3fv(u('c2'), P.dye[1]); gl.uniform3fv(u('hot'), P.hot);
      // pass 1: a soft halo around every grain (the glow of the form); pass 2: the grains themselves, small and sharp
      gl.uniform1f(u('soft'), 1); gl.uniform1f(u('scale'), 9 * K); gl.uniform1f(u('grow'), .6); gl.uniform1f(u('alpha'), .045 + amp * .05); gl.drawArrays(gl.POINTS, 0, N);
      gl.uniform1f(u('soft'), 0); gl.uniform1f(u('scale'), 1.55 * K); gl.uniform1f(u('grow'), 1.1); gl.uniform1f(u('alpha'), .62 + amp * .35); gl.drawArrays(gl.POINTS, 0, N);
      gl.disableVertexAttribArray(l); gl.disableVertexAttribArray(l2);
    }
    return { frame, reset() { lastT = -1; curKey = ''; } };
  }

  // =====================================================================================================
  // Shared kit for the element styles (Agni, Dhūpa, Ākāśa): sharp full-resolution WebGL, shapes sampled from words
  // =====================================================================================================
  const DW = 1280, DH = 720;                          // design space; drawn at the screen's real resolution
  function glKit(cv) {
    const box = cv.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
    const RW = Math.round(clamp(box.width ? box.width * dpr : 1920, 1280, 2560)), RH = Math.round(RW * 9 / 16);
    cv.width = RW; cv.height = RH;
    const gl = cv.getContext('webgl', { antialias: true, alpha: false, preserveDrawingBuffer: true });
    const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; };
    const prog = (vs, fs) => { const p = gl.createProgram(); gl.attachShader(p, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(p, sh(gl.FRAGMENT_SHADER, fs)); gl.linkProgram(p); p.U = {}; return p; };
    const quad = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, quad); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const bufs = {};
    function set(p, name, v) {
      const l = p.U[name] !== undefined ? p.U[name] : (p.U[name] = gl.getUniformLocation(p, name)); if (l === null) return;
      if (typeof v === 'number') gl.uniform1f(l, v); else if (v.length === 2) gl.uniform2fv(l, v); else if (v.length === 3) gl.uniform3fv(l, v); else gl.uniform4fv(l, v);
    }
    function attr(p, name, data, size) {
      const b = bufs[name] || (bufs[name] = gl.createBuffer()); gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, data, gl.DYNAMIC_DRAW);
      const l = gl.getAttribLocation(p, name); gl.enableVertexAttribArray(l); gl.vertexAttribPointer(l, size, gl.FLOAT, false, 0, 0); return l;
    }
    function background(p, U) {
      gl.viewport(0, 0, RW, RH); gl.disable(gl.BLEND); gl.useProgram(p);
      gl.bindBuffer(gl.ARRAY_BUFFER, quad); const l = gl.getAttribLocation(p, 'p'); gl.enableVertexAttribArray(l); gl.vertexAttribPointer(l, 2, gl.FLOAT, false, 0, 0);
      set(p, 'res', [RW, RH]); for (const k in U) set(p, k, U[k]); gl.drawArrays(gl.TRIANGLES, 0, 3); gl.disableVertexAttribArray(l);
    }
    const ptP = prog(`attribute vec2 pos;attribute vec3 a;uniform vec2 res;uniform float scale;varying vec3 va;
      void main(){vec2 q=pos/res*2.-1.;gl_Position=vec4(q.x,-q.y,0.,1.);va=a;gl_PointSize=max(1.,scale*a.z);}`,
      `precision mediump float;uniform vec3 c1,c2,hot;uniform float alpha,soft;varying vec3 va;
      void main(){vec2 d=gl_PointCoord-.5;float r=dot(d,d)*4.;if(r>1.)discard;
      float s=soft>.5?exp(-r*2.5)*(1.-r):smoothstep(1.,.15,r);
      vec3 c=mix(c1,c2,va.x);c=mix(c,hot,clamp(va.y,0.,1.));gl_FragColor=vec4(c*s*alpha*(.3+va.y),1.);}`);
    // a = [colour mix, heat (0 cold … 1 white-hot), size factor]
    function points(pos, a, n, passes, col) {
      gl.useProgram(ptP); gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE);
      const l1 = attr(ptP, 'pos', pos, 2), l2 = attr(ptP, 'a', a, 3);
      set(ptP, 'res', [DW, DH]); set(ptP, 'c1', col[0]); set(ptP, 'c2', col[1]); set(ptP, 'hot', col[2]);
      for (const [soft, scale, alpha] of passes) { set(ptP, 'soft', soft); set(ptP, 'scale', scale * RW / DW); set(ptP, 'alpha', alpha); gl.drawArrays(gl.POINTS, 0, n); }
      gl.disableVertexAttribArray(l1); gl.disableVertexAttribArray(l2);
    }
    return { gl, RW, RH, prog, set, attr, background, points };
  }
  const BG_VS = 'attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}';
  const NOISE = `float h1(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
    float n2(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(h1(i),h1(i+vec2(1,0)),f.x),mix(h1(i+vec2(0,1)),h1(i+vec2(1,1)),f.x),f.y);}
    float fbm(vec2 p){float s=0.,a=.5;mat2 m=mat2(1.6,1.2,-1.2,1.6);for(int i=0;i<5;i++){s+=a*n2(p);p=m*p;a*=.5;}return s;}`;
  function shapes(N, deity) {                        // N points on a word, ॐ or the deity's symbol (cached)
    const off = document.createElement('canvas'); off.width = DW; off.height = DH; const oc = off.getContext('2d', { willReadFrequently: true });
    const cache = new Map(), strokes = SYMBOLS[SYMBOL_OF[deity] || 'lotus']();
    function sample(draw, key) {
      if (cache.has(key)) return cache.get(key);
      oc.clearRect(0, 0, DW, DH); oc.fillStyle = '#fff'; oc.strokeStyle = '#fff'; draw(oc);
      const d = oc.getImageData(0, 0, DW, DH).data, pts = [];
      for (let y = 0; y < DH; y++) for (let x = 0; x < DW; x++) if (d[(y * DW + x) * 4 + 3] > 140) pts.push(x, y);
      const tg = new Float32Array(N * 2), m = pts.length / 2 || 1;
      for (let i = 0; i < N; i++) { const j = Math.floor(hash(i * 12.9898 + key.length) * m) * 2; tg[i * 2] = pts[j] + hash(i * 4.4); tg[i * 2 + 1] = pts[j + 1] + hash(i * 8.8); }
      tg.raw = pts; cache.set(key, tg); return tg;
    }
    return {
      text(s, cy = 300, fsMax = 300, maxW = 1080) {
        return sample(c => { let fs = fsMax; c.font = `${fs}px ${DEV}`; const w = c.measureText(s).width; fs = Math.min(fs, fs * maxW / Math.max(1, w)); c.font = `${fs}px ${DEV}`;
          c.textAlign = 'center'; c.textBaseline = 'alphabetic'; const m = c.measureText(s); c.fillText(s, 640, cy + (m.actualBoundingBoxAscent - m.actualBoundingBoxDescent) / 2); }, `t:${s}:${cy}:${fsMax}`);
      },
      symbol(cx = 640, cy = 350, sc = 300, lw = 5) {
        return sample(c => { c.lineWidth = lw; c.lineCap = 'round'; c.lineJoin = 'round';
          for (const st of strokes) { c.beginPath(); st.p.forEach(([x, y], i) => { const X = cx + x * sc, Y = cy + y * sc; if (i) c.lineTo(X, Y); else c.moveTo(X, Y); }); c.stroke(); } }, `s:${cx}:${cy}:${sc}`);
      },
    };
  }
  function modeAt(Wd, V, t) {                         // what the particles should form now
    if (t < V.first - .15) return { key: 'pre' };
    if (t > V.last + .4) return { key: 'end' };         // the deity's symbol only after the last word
    let w = null; for (const x of Wd) if (t >= x.start - .15) w = x;   // in a pause between lines the last sung word stays
    return w ? { key: 'w' + w.start, w } : { key: 'pre' };
  }

  // ---------- flow: each word is built from material that rises out of a source (the fire, the incense) ----------
  // modes: 0 free (ambient, moved by the style), 1 bound (gliding into / holding its place in the word), 2 released (old word dissolving)
  function flow(N, slots, o) {
    const pos = new Float32Array(N * 2), vel = new Float32Array(N * 2), mode = new Uint8Array(N), age = new Float32Array(N), slot = new Int32Array(N).fill(-1);
    let tg = null, next = 0, budget = 0, fill = 1, cursor = 0;
    return { pos, vel, mode, age,
      target(t2, fillTime) {                          // a new shape: the old one is let go, the new one fills in over fillTime
        for (let i = 0; i < N; i++) if (mode[i] === 1) { mode[i] = 2; age[i] = 0; slot[i] = -1; }
        tg = t2; next = 0; budget = 0; fill = fillTime;
      },
      step(dt, t, amp) {
        if (tg && next < slots) {                     // recruit fresh material at the source, a steady stream until the word is full
          budget += slots * dt / fill; let tries = 0;
          while (budget >= 1 && next < slots && tries < N) {
            const i = cursor; cursor = (cursor + 1) % N; tries++;
            if (mode[i] === 0 || (mode[i] === 2 && age[i] > o.reuseAfter)) { o.spawn(i); mode[i] = 1; slot[i] = next++; age[i] = 0; budget--; }
          }
        }
        for (let i = 0; i < N; i++) {
          const ix = i * 2;
          if (mode[i] === 1) {                          // steer towards its place: fast far away, gentle arrival, never overshooting
            const k = slot[i] * 2, dx = tg[k] - pos[ix], dy = tg[k + 1] - pos[ix + 1], d = Math.hypot(dx, dy) + 1e-6;
            const sp = o.maxSpeed * Math.min(1, d / o.slowR), n = o.noise(i, t, amp, d), g = Math.min(1, o.steer * dt);
            vel[ix] += (dx / d * sp + n[0] - vel[ix]) * g; vel[ix + 1] += (dy / d * sp + n[1] - vel[ix + 1]) * g; age[i] += dt;
          } else if (mode[i] === 2) { o.released(i, dt, t, amp); age[i] += dt; if (age[i] > o.fadeOut) { mode[i] = 0; o.spawn(i); age[i] = 0; } }
          else o.free(i, dt, t, amp);
          pos[ix] += vel[ix] * dt; pos[ix + 1] += vel[ix + 1] * dt;
        }
      } };
  }

  // =====================================================================================================
  // Agni: a havan fire; embers rise from it and gather into each sung word
  // =====================================================================================================
  function agni(cv, opts) {
    const G = glKit(cv), P = FX.PAL[opts.deity] || FX.PAL.peace, FXp = 640, FYp = 612;
    const bg = G.prog(BG_VS, `precision highp float;uniform vec2 res;uniform float t,amp,flare;uniform vec3 deep;${NOISE}
      void main(){vec2 uv=gl_FragCoord.xy/res;vec2 q=(gl_FragCoord.xy-vec2(.5*res.x,res.y*${(1 - 612 / 720).toFixed(4)}))/res.y;  // origin: the fire's base
        float r=length(q*vec2(.8,1.2));vec3 c=deep*.18+vec3(.02,.008,.004);
        c+=vec3(1.,.42,.12)*.42*(.75+amp*.9+flare*.4)*exp(-r*3.2);                    // firelight on the wall
        c*=.85+.15*n2(gl_FragCoord.xy/res.y*vec2(90.,40.));                            // rough stone
        // the kuṇḍa: a brick pit, rim lit from above
        float pit=step(abs(q.x),.27)*step(q.y,.0)*step(-.16,q.y);
        if(pit>0.){float bx=fract(q.x*22.+step(.5,fract(q.y*26.))*.5),by=fract(q.y*26.);float mortar=step(.92,bx)+step(.85,by);
          vec3 brick=mix(vec3(.24,.08,.04),vec3(.12,.04,.02),n2(floor(vec2(q.x*22.,q.y*26.))*3.));
          c=mix(brick,vec3(.05,.02,.01),clamp(mortar,0.,1.))*(.35+.9*exp(q.y*9.)*(.7+amp*.6));}
        // flames: noise climbing out of the pit, taller with the voice
        float H=.27+amp*.24+flare*.08;vec2 f=q;f.x+=(fbm(vec2(q.y*5.-t*1.3,t*.7))-.5)*.08*clamp(q.y/H,0.,1.)*3.;
        float fl=0.;
        if(f.y>-.02&&f.y<H*1.6&&abs(f.x)<.3){
          float w=max(.004,.19*(1.-smoothstep(-.02,H,f.y)));float n=fbm(vec2(f.x*7.,f.y*5.-t*3.2)),n3=fbm(vec2(f.x*13.+3.,f.y*9.-t*4.6));
          fl=smoothstep(w,w*.15,abs(f.x))*smoothstep(-.03,.02,f.y)*smoothstep(H*1.2,0.,f.y-(n-.45)*.26);
          fl+=.45*smoothstep(w*.7,0.,abs(f.x+(n3-.5)*.12))*smoothstep(H*.8,0.,f.y-(n3-.5)*.3)*smoothstep(-.02,.03,f.y);   // inner tongues
          fl=clamp(fl,0.,1.3);}
        vec3 fc=mix(vec3(.6,.06,.01),vec3(1.,.45,.08),smoothstep(.0,.5,fl));fc=mix(fc,vec3(1.,.9,.6),smoothstep(.6,1.,fl));
        c+=fc*fl*1.25;
        c*=1.-.45*dot(uv-.5,uv-.5)*2.;gl_FragColor=vec4(c,1.);}`);
    const SLOTS = 6500, NN = 14000, S = shapes(SLOTS, opts.deity), Wd = FX.words(opts.units || []), V = voiced(Wd);
    const a = new Float32Array(NN * 3), life = new Float32Array(NN), seed = new Float32Array(NN), nv = [0, 0];
    for (let i = 0; i < NN; i++) seed[i] = hash(i * 1.37);
    let F = null;
    const spawn = i => { const s = hash(i * 9.1 + life[i] * 7.7 + seed[i]), r = Math.sqrt(hash(i * 3 + s)), an = s * TAU;   // a soft oval inside the flames
      F.pos[i * 2] = FXp + Math.cos(an) * r * 62; F.pos[i * 2 + 1] = FYp - 22 + Math.sin(an) * r * 16;
      F.vel[i * 2] = (hash(i * 5 + s) - .5) * 60; F.vel[i * 2 + 1] = -170 - 170 * hash(i * 7 + s); life[i] = 0; };
    F = flow(NN, SLOTS, { spawn, maxSpeed: 1500, slowR: 130, steer: 7, reuseAfter: .4, fadeOut: 1.1,
      noise(i, t, amp, d) { const s = seed[i], k = Math.min(1, d / 200) * 70 + 5 * (1 + amp * 3); nv[0] = Math.sin(t * 2.1 + s * 40) * k; nv[1] = Math.cos(t * 1.7 + s * 33) * k * .6; return nv; },
      released(i, dt, t, amp) { const ix = i * 2; F.vel[ix] = (F.vel[ix] + Math.sin(t * 2 + seed[i] * 50) * 70 * dt) * Math.exp(-1.5 * dt); F.vel[ix + 1] = (F.vel[ix + 1] + (-90 - amp * 120) * dt) * Math.exp(-1.5 * dt); },
      free(i, dt, t, amp) { const ix = i * 2, x = F.pos[ix], y = F.pos[ix + 1], s = seed[i], nx = Math.sin(y * .02 + t * 1.4 + s * 9) * 40, ny = Math.cos(x * .018 - t * 1.4 + s * 7) * 30;
        F.vel[ix] = (F.vel[ix] + nx * 2.5 * dt) * Math.exp(-1.2 * dt); F.vel[ix + 1] = (F.vel[ix + 1] + (-90 - amp * 160 + ny) * dt) * Math.exp(-1.2 * dt); life[i] += dt;
        if (y < -20 || life[i] > 1.4 + s * 2) spawn(i); } });
    for (let i = 0; i < NN; i++) { spawn(i); life[i] = seed[i] * 3; F.pos[i * 2 + 1] -= seed[i] * 420; }
    let key = '', since = -9, lastT = -1, hasT = false;
    function frame(t, A) {
      const amp = A && A.amp ? A.amp : 0, dt = lastT < 0 || Math.abs(t - lastT) > 1.2 ? 0 : clamp(t - lastT, 0, 1 / 20); lastT = t;
      const m = modeAt(Wd, V, t);
      if (m.key !== key) { key = m.key; since = t;
        if (m.w) { F.target(S.text(m.w.dev, 270, 250), clamp((m.w.end - m.w.start) * .3, .25, .6)); hasT = true; }
        else if (m.key === 'end') { F.target(S.symbol(640, 300, 240, 5), 1.6); hasT = true; }
        else { F.target(null, 1); hasT = false; } }
      if (dt > 0) F.step(dt, t, amp);
      for (let i = 0; i < NN; i++) {
        const md = F.mode[i], s = seed[i], flick = .55 + .45 * Math.sin(t * 9 + s * 60);
        a[i * 3] = s;
        if (md === 1) { const g = ease(F.age[i] / .45); a[i * 3 + 1] = (.25 + .75 * g) * (.55 + .45 * flick) * clamp(F.age[i] / .12, .15, 1); a[i * 3 + 2] = (.8 + .4 * g) + s * g; }   // dim in flight, bright once settled
        else if (md === 2) { a[i * 3 + 1] = clamp(1 - F.age[i] / 1.1) * .85 * flick; a[i * 3 + 2] = 1.1; }
        else { a[i * 3 + 1] = clamp(1 - life[i] / (1.4 + s * 2)) * flick * .7; a[i * 3 + 2] = .7 + clamp(1 - life[i] / 4); }
      }
      G.background(bg, { t, amp, flare: Math.exp(-(t - since) * 2.5) * (hasT ? 1 : 0), deep: P.deep });
      G.points(F.pos, a, NN, [[1, 9, .028 + amp * .03], [0, 1.9, .55 + amp * .3]], [[.75, .12, .02], [1, .45, .08], [1, .92, .6]]);
    }
    return { frame, reset() { lastT = -1; key = ''; } };
  }

  // =====================================================================================================
  // Dhūpa: incense smoke in a dark shrine; the voice stirs it and each word forms in the smoke
  // =====================================================================================================
  function dhupa(cv, opts) {
    const G = glKit(cv), P = FX.PAL[opts.deity] || FX.PAL.peace;
    const TIPS = [[606, 520], [640, 500], [674, 520]];
    const bg = G.prog(BG_VS, `precision highp float;uniform vec2 res;uniform float t,amp;uniform vec3 deep,gold;${NOISE}
      float seg(vec2 p,vec2 a,vec2 b){vec2 pa=p-a,ba=b-a;float h=clamp(dot(pa,ba)/dot(ba,ba),0.,1.);return length(pa-ba*h);}
      void main(){vec2 uv=gl_FragCoord.xy/res;vec2 q=vec2(gl_FragCoord.x/res.x*${DW}.,(1.-gl_FragCoord.y/res.y)*${DH}.);
        vec3 c=mix(deep*.22,deep*.05,uv.y*.2+.8-uv.y)+vec3(.006);
        c+=gold*.16*exp(-length((q-vec2(1100.,250.))/vec2(520.,420.))*2.2)*(.9+.1*sin(t*2.3));     // an oil lamp just out of frame
        c+=gold*.05*exp(-length((q-vec2(640.,560.))/vec2(300.,140.)));
        // brass holder and three sticks with glowing tips
        vec2 bq=(q-vec2(640.,566.))/vec2(78.,46.);float bowl=step(length(bq),1.)*step(0.,bq.y);                 // brass bowl of ash
        float rim=smoothstep(.06,0.,abs(length((q-vec2(640.,566.))/vec2(78.,12.))-1.));
        vec3 brass=vec3(.42,.28,.1)*(.35+.65*smoothstep(.9,.0,bq.y))*(.7+.3*smoothstep(-.6,.6,-bq.x));
        c=mix(c,brass,bowl);c+=vec3(.9,.65,.3)*rim*.35;
        float foot=step(abs(q.x-640.),34.)*step(610.,q.y)*step(q.y,624.);c=mix(c,vec3(.25,.16,.06),foot);
        float st=min(min(seg(q,vec2(626.,565.),vec2(606.,520.)),seg(q,vec2(640.,565.),vec2(640.,500.))),seg(q,vec2(654.,565.),vec2(674.,520.)));
        c=mix(c,vec3(.18,.07,.04),smoothstep(2.2,1.,st));
        float tip=min(min(length(q-vec2(606.,520.)),length(q-vec2(640.,500.))),length(q-vec2(674.,520.)));
        c+=vec3(1.,.38,.08)*(exp(-tip*.35)*1.4+exp(-tip*.06)*.12)*(.8+.2*sin(t*5.+q.x));
        c*=.9+.1*n2(q*.02+t*.02);c*=1.-.5*dot(uv-.5,uv-.5)*2.;gl_FragColor=vec4(c,1.);}`);
    const SLOTS = 7000, NN = 16000, S = shapes(SLOTS, opts.deity), Wd = FX.words(opts.units || []), V = voiced(Wd);
    const a = new Float32Array(NN * 3), life = new Float32Array(NN), seed = new Float32Array(NN), span = new Float32Array(NN), nv = [0, 0], cv2 = [0, 0];
    for (let i = 0; i < NN; i++) seed[i] = hash(i * 2.71);
    // curl noise: velocity from a stream function, so the smoke swirls without bunching up
    function curl(x, y, t, out) {
      const k1 = .006, k2 = .013, a1 = x * k1 + t * .25, b1 = y * k1 - t * .2, a2 = x * k2 - y * k2 * .7 + t * .4;
      out[0] = -Math.sin(a1) * Math.sin(b1) * 75 - Math.cos(a2) * .7 * 45;          // px/s
      out[1] = -Math.cos(a1) * Math.cos(b1) * 75 - Math.cos(a2) * 45;
    }
    let F = null;
    const spawn = i => { const tip = TIPS[i % 3]; F.pos[i * 2] = tip[0] + (hash(i + life[i] + seed[i]) - .5) * 3; F.pos[i * 2 + 1] = tip[1];
      F.vel[i * 2] = 0; F.vel[i * 2 + 1] = -40 - 25 * seed[i]; life[i] = 0; span[i] = 7 + 6 * seed[i]; };
    F = flow(NN, SLOTS, { spawn, maxSpeed: 560, slowR: 160, steer: 3.4, reuseAfter: .8, fadeOut: 1.5,
      noise(i, t, amp, d) { curl(F.pos[i * 2], F.pos[i * 2 + 1], t + seed[i] * 2, cv2); const k = (.22 + Math.min(1, d / 250) * .9) * (1 + amp * 2); nv[0] = cv2[0] * k; nv[1] = cv2[1] * k; return nv; },
      released(i, dt, t, amp) { const ix = i * 2; curl(F.pos[ix], F.pos[ix + 1], t + seed[i] * 2, cv2); const j = (Math.random() - .5) * 160;
        F.vel[ix] = (F.vel[ix] + (cv2[0] * 2.2 * (1 + amp * 2) + j) * dt) * Math.exp(-.9 * dt); F.vel[ix + 1] = (F.vel[ix + 1] + (-75 + cv2[1] * 1.6) * dt) * Math.exp(-.9 * dt); },
      free(i, dt, t, amp) { const ix = i * 2, y = F.pos[ix + 1], stir = 1 + amp * 3; curl(F.pos[ix], y, t + seed[i] * 2, cv2);
        const hgt = .4 + clamp((520 - y) / 260), j = (Math.random() - .5) * 220 * hgt;    // swirl and spread more as it rises
        F.vel[ix] = (F.vel[ix] + (cv2[0] * hgt * 2.2 * stir + j) * dt) * Math.exp(-.9 * dt); F.vel[ix + 1] = (F.vel[ix + 1] + (-52 + cv2[1] * hgt * 1.4 * stir) * dt) * Math.exp(-.9 * dt); life[i] += dt;
        if (life[i] > span[i] || y < -60) spawn(i); } });
    for (let i = 0; i < NN; i++) { spawn(i); life[i] = seed[i] * span[i]; F.pos[i * 2 + 1] -= life[i] * 40; F.pos[i * 2] += Math.sin(life[i] + i) * life[i] * 6; }
    let key = '', lastT = -1;
    function frame(t, A) {
      const amp = A && A.amp ? A.amp : 0, dt = lastT < 0 || Math.abs(t - lastT) > 1.2 ? 0 : clamp(t - lastT, 0, 1 / 20); lastT = t;
      const m = modeAt(Wd, V, t);
      if (m.key !== key) { key = m.key;
        if (m.w) F.target(S.text(m.w.dev, 290, 270), clamp((m.w.end - m.w.start) * .45, .45, 1.1));
        else if (m.key === 'end') F.target(S.symbol(640, 300, 230, 7), 2.2);
        else F.target(null, 1); }
      if (dt > 0) F.step(dt, t, amp);
      for (let i = 0; i < NN; i++) {
        const md = F.mode[i], s = seed[i]; a[i * 3] = s;
        if (md === 1) { const g = clamp(F.age[i] / .9), born = clamp(F.age[i] / .35);              // a thin wisp off the tip, thickening into a letter
          a[i * 3 + 1] = (.12 + .38 * g) * born; a[i * 3 + 2] = (.45 + 1.05 * born) * (1.2 - .35 * g) * (1 + s * .5); }
        else if (md === 2) { const g = clamp(F.age[i] / 1.5); a[i * 3 + 1] = .5 * (1 - g) * (1 - g); a[i * 3 + 2] = 1.1 + g * 2.6; }   // the old word thins and drifts away
        else { const g = clamp(life[i] / span[i]); a[i * 3 + 1] = .04 * (1 - g) * clamp(g * 6, .15, 1); a[i * 3 + 2] = .35 + g * 3.4; }
      }
      G.background(bg, { t, amp, deep: P.deep, gold: P.gold });
      const smoke = [[.5, .53, .6], [.8, .82, .88], P.gold.map(c => c * .8)];
      G.points(F.pos, a, NN, [[1, 26, .011 + amp * .008], [1, 7, .03 + amp * .015]], smoke);
    }
    return { frame, reset() { lastT = -1; key = ''; } };
  }

  // =====================================================================================================
  // Ākāśa: the night sky; each sung word becomes a constellation over stardust, and the sun rises at the end
  // =====================================================================================================
  function akasha(cv, opts) {
    const G = glKit(cv), P = FX.PAL[opts.deity] || FX.PAL.peace, N = 9000, gl = G.gl;
    const bg = G.prog(BG_VS, `precision highp float;uniform vec2 res;uniform float t,amp,rise;uniform vec3 deep,mid,dye1,dye2,gold;${NOISE}
      void main(){vec2 uv=gl_FragCoord.xy/res;vec2 q=(gl_FragCoord.xy-.5*res)/res.y;float T=t*.02;
        vec3 c=mix(vec3(.004,.006,.02),deep*.35,uv.y*.3);
        float n=fbm(q*2.2+vec2(T,-T*.6)+fbm(q*3.-T)*.8);float n2v=fbm(q*4.5-vec2(T*1.4,T));
        c+=mix(dye1,dye2,n2v)*pow(max(0.,n-.38),2.)*1.6*(.8+amp*.6);                  // nebula
        c+=mid*.08*pow(max(0.,n-.3),1.5);
        for(int k=0;k<3;k++){float sc=60.+float(k)*70.;vec2 g=gl_FragCoord.xy/res.y*sc;vec2 gi=floor(g);float hv=h1(gi+float(k)*17.);
          vec2 gf=fract(g)-vec2(h1(gi+3.1),h1(gi+7.3));float tw=.6+.4*sin(t*(1.+hv*3.)+hv*40.);
          c+=vec3(.85,.9,1.)*smoothstep(.06,0.,length(gf))*step(.965-float(k)*.004,hv)*tw*(1.-rise*.9)*(1.2-float(k)*.3);}
        c+=gold*.1*amp*exp(-length(q)*2.5);                                                // the Om pulse
        float hz=smoothstep(.55,0.,uv.y);vec3 dawn=mix(vec3(1.,.42,.12),vec3(1.,.8,.45),smoothstep(0.,.35,uv.y));
        c=mix(c,c*.4+dawn*hz*1.1+vec3(.15,.2,.35)*.25*(1.-hz),rise);                       // sunrise at the end
        c+=vec3(1.,.85,.5)*rise*exp(-length((q-vec2(0.,-.62+rise*.12))*vec2(1.,1.))*5.)*1.2;
        c*=1.-.35*dot(uv-.5,uv-.5)*2.;gl_FragColor=vec4(c,1.);}`);
    const lnP = G.prog(`attribute vec2 pos;attribute float al;uniform vec2 res;varying float v;void main(){vec2 q=pos/res*2.-1.;gl_Position=vec4(q.x,-q.y,0.,1.);v=al;}`,
      `precision mediump float;uniform vec3 col;varying float v;void main(){gl_FragColor=vec4(col*v,1.);}`);
    const S = shapes(N, opts.deity), Wd = FX.words(opts.units || []), V = voiced(Wd);
    const pos = new Float32Array(N * 2), vel = new Float32Array(N * 2), a = new Float32Array(N * 3), seed = new Float32Array(N);
    for (let i = 0; i < N; i++) { seed[i] = hash(i * 3.3); pos[i * 2] = hash(i * 5.1) * DW; pos[i * 2 + 1] = hash(i * 6.7) * DH; }
    // constellation for a shape: K stars by farthest-point sampling, joined by a minimum spanning tree
    const cons = new Map();
    function constellation(tgKey, raw, K) {
      if (cons.has(tgKey)) return cons.get(tgKey);
      const n = raw.length / 2, step = Math.max(1, Math.floor(n / 2500)), cand = [];
      for (let i = 0; i < n; i += step) cand.push([raw[i * 2], raw[i * 2 + 1]]);
      const stars = [cand[Math.floor(cand.length / 2)]], dmin = cand.map(p => Math.hypot(p[0] - stars[0][0], p[1] - stars[0][1]));
      while (stars.length < Math.min(K, cand.length)) { let b = 0; for (let i = 1; i < cand.length; i++) if (dmin[i] > dmin[b]) b = i; stars.push(cand[b]);
        for (let i = 0; i < cand.length; i++) dmin[i] = Math.min(dmin[i], Math.hypot(cand[i][0] - cand[b][0], cand[i][1] - cand[b][1])); }
      stars.sort((p, q) => p[0] - q[0]);                           // they light up left to right, as the word is read
      const inT = stars.map((_, i) => i === 0), edges = [];
      for (let c = 1; c < stars.length; c++) { let best = null;
        for (let i = 0; i < stars.length; i++) if (inT[i]) for (let j = 0; j < stars.length; j++) if (!inT[j]) { const d = Math.hypot(stars[i][0] - stars[j][0], stars[i][1] - stars[j][1]); if (!best || d < best[2]) best = [i, j, d]; }
        inT[best[1]] = true; edges.push([best[0], best[1]]); }
      const out = { stars, edges }; cons.set(tgKey, out); return out;
    }
    const sp = new Float32Array(64 * 2), sa = new Float32Array(64 * 3), lines = new Float32Array(64 * 12), lal = new Float32Array(64 * 6);
    let key = '', tg = null, since = 0, lastT = -1, C = null, prevC = null, prevAt = 0, end0 = 0;
    function drawCons(cn, t0, t1, t, fade) {
      if (!cn) return;
      const k = cn.stars.length, dur = Math.max(.6, t1 - t0), lit = i => clamp((t - t0 - dur * i / k) / .25);
      let ns = 0, nl = 0;
      cn.stars.forEach((s, i) => { const v = lit(i) * fade; if (v <= 0) return; sp[ns * 2] = s[0]; sp[ns * 2 + 1] = s[1]; sa[ns * 3] = hash(i); sa[ns * 3 + 1] = v * (.7 + .3 * Math.sin(t * 3 + i)); sa[ns * 3 + 2] = 1 + hash(i + 3); ns++; });
      cn.edges.forEach(([i, j]) => { const v = Math.min(lit(i), lit(j)) * fade; if (v <= 0) return; const A0 = cn.stars[i], B0 = cn.stars[j], g = clamp((t - t0 - dur * Math.max(i, j) / k) / .45);
        const bx = A0[0] + (B0[0] - A0[0]) * g, by = A0[1] + (B0[1] - A0[1]) * g, dx = by - A0[1], dy = -(bx - A0[0]), L = Math.hypot(dx, dy) || 1, w = .9;
        const ox = dx / L * w, oy = dy / L * w, q = [A0[0] + ox, A0[1] + oy, A0[0] - ox, A0[1] - oy, bx + ox, by + oy, bx + ox, by + oy, A0[0] - ox, A0[1] - oy, bx - ox, by - oy];
        lines.set(q, nl * 12); lal.fill(v * .55, nl * 6, nl * 6 + 6); nl++; });
      if (nl) { gl.useProgram(lnP); gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE); const l1 = G.attr(lnP, 'pos', lines.subarray(0, nl * 12), 2), l2 = G.attr(lnP, 'al', lal.subarray(0, nl * 6), 1);
        G.set(lnP, 'res', [DW, DH]); G.set(lnP, 'col', P.gold); gl.drawArrays(gl.TRIANGLES, 0, nl * 6); gl.disableVertexAttribArray(l1); gl.disableVertexAttribArray(l2); }
      if (ns) G.points(sp.subarray(0, ns * 2), sa.subarray(0, ns * 3), ns, [[1, 30, .22], [0, 4.2, 1]], [[1, .95, .85], P.hot, [1, 1, 1]]);
    }
    function frame(t, A) {
      const amp = A && A.amp ? A.amp : 0, dt = lastT < 0 || Math.abs(t - lastT) > 1.2 ? 0 : clamp(t - lastT, 0, 1 / 20); lastT = t;
      const m = modeAt(Wd, V, t);
      if (m.key !== key) { prevC = C; prevAt = t; key = m.key; since = t;
        if (m.w) { tg = S.text(m.w.dev, 300, 290); const syl = m.w.syl || m.w.dev.length / 2; C = { ...constellation('w:' + m.w.dev, tg.raw, Math.round(clamp(syl * 4, 10, 30))), t0: m.w.start, t1: m.w.end }; }
        else if (m.key === 'end') { tg = S.symbol(640, 330, 260, 4); C = { ...constellation('symbol', tg.raw, 40), t0: t, t1: t + 3 }; end0 = t; }
        else { tg = null; C = null; } }
      const st = 60 + 200 * ease((t - since) / .45), damp = Math.exp(-13 * dt);
      for (let i = 0; i < N; i++) {
        const ix = i * 2, x = pos[ix], y = pos[ix + 1], s = seed[i], bound = tg && s < .8;
        const nx = Math.sin(y * .01 + t * .3 + s * 6) * 14, ny = Math.cos(x * .01 - t * .25 + s * 4) * 14;
        if (bound) { vel[ix] = (vel[ix] + ((tg[ix] - x) * st + nx * (1 + amp * 5)) * dt) * damp; vel[ix + 1] = (vel[ix + 1] + ((tg[ix + 1] - y) * st + ny * (1 + amp * 5)) * dt) * damp; }
        else { vel[ix] = (vel[ix] + nx * dt) * Math.exp(-.5 * dt); vel[ix + 1] = (vel[ix + 1] + ny * dt) * Math.exp(-.5 * dt); }
        pos[ix] = x + vel[ix] * dt; pos[ix + 1] = y + vel[ix + 1] * dt;
        if (pos[ix] < -20) pos[ix] += DW + 40; if (pos[ix] > DW + 20) pos[ix] -= DW + 40; if (pos[ix + 1] < -20) pos[ix + 1] += DH + 40; if (pos[ix + 1] > DH + 20) pos[ix + 1] -= DH + 40;
        a[i * 3] = s; a[i * 3 + 1] = bound ? .35 + .3 * Math.sin(t * 2 + s * 30) : .12; a[i * 3 + 2] = bound ? 1 + s : .7 + s * .6;
      }
      const rise = m.key === 'end' ? ease((t - end0 - 1) / 5) : 0;
      G.background(bg, { t, amp, rise, deep: P.deep, mid: P.mid, dye1: P.dye[0], dye2: P.dye[1], gold: P.gold });
      G.points(pos, a, N, [[1, 7, .035], [0, 1.6, .5 + amp * .2]], [[.7, .78, 1], P.gold, [1, 1, 1]]);
      if (prevC && t - prevAt < 1.4) drawCons(prevC, prevC.t0, prevC.t1, t, 1 - (t - prevAt) / 1.4);
      if (C) drawCons(C, C.t0, C.t1, t, 1);
    }
    return { frame, reset() { lastT = -1; key = ''; } };
  }

  FX.styles = Object.assign(FX.styles || {}, { rekha, morph, akshara, kana, agni, dhupa, akasha });
  const base = FX.create;
  FX.create = (kind, cv, o) => (FX.styles[kind] ? FX.styles[kind](cv, o || {}) : base(kind, cv, o));
  FX.MOTION = { kana: 'Kaṇa · particles of light', agni: 'Agni · sacred fire', dhupa: 'Dhūpa · incense smoke', akasha: 'Ākāśa · night sky', rekha: 'Rekhā · line drawing', morph: 'Liquid forms', akshara: 'Akṣara · kinetic type' };
})();
