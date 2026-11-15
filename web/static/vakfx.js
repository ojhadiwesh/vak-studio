// Vāk live visuals: chant styles drawn in the browser in real time, driven by the actual audio and the word timings.
//   const fx = VakFX.create('nada' | 'gold', canvas, { units, deity });  fx.frame(t, A); fx.reset();
//   const A = VakFX.analyser(mediaElement);  A.update() → { amp, low, f0, clarity, centroid, peaks }
//   VakFX.deityOf(units) → 'shiva' | 'devi' | 'vishnu' | 'ganesha' | 'surya' | 'peace'
(function () {
  const TAU = Math.PI * 2;

  // ---------- deity → palette (same detection idea as vak/planner.py) ----------
  const STEMS = { shiva: ['शिव', 'त्र्यम्बक', 'रुद्र', 'महादेव', 'शम्भ', 'शङ्कर'], devi: ['देवी', 'देव्य', 'दुर्ग', 'चण्डिक', 'काली', 'लक्ष्म', 'अम्ब', 'भवान'],
    vishnu: ['नारायण', 'विष्णु', 'कृष्ण', 'राम', 'हरे', 'गोविन्द', 'वासुदेव'], ganesha: ['गणप', 'गं', 'विनायक', 'वक्रतुण्ड'], surya: ['सवितु', 'सूर्य', 'भर्ग', 'आदित्य'] };
  function deityOf(units) {
    const txt = (units || []).map(u => u.devanagari).join(' '); let best = 'peace', n = 0;
    for (const [k, ss] of Object.entries(STEMS)) { const c = ss.reduce((a, s) => a + txt.split(s).length - 1, 0); if (c > n) { n = c; best = k; } }
    return best;
  }
  // colours as [r,g,b] 0..1
  const PAL = {
    shiva:   { water: [.01, .015, .04], deep: [.05, .07, .2], mid: [.35, .45, .75], gold: [.78, .86, 1.0], hot: [.95, .97, 1], dye: [[.5, .65, 1], [.85, .9, 1]],   sand: [[.82, .9, 1], [.6, .72, 1]], plate: [.05, .06, .09] },
    devi:    { water: [.03, .005, .01], deep: [.2, .02, .06], mid: [.75, .12, .2], gold: [1, .72, .32], hot: [1, .95, .82], dye: [[1, .18, .25], [1, .55, .2]],    sand: [[1, .8, .5], [1, .45, .4]], plate: [.09, .04, .04] },
    vishnu:  { water: [.005, .01, .035], deep: [.02, .06, .2], mid: [.1, .35, .7], gold: [1, .8, .4], hot: [1, .97, .85], dye: [[.25, .7, 1], [1, .75, .3]],      sand: [[1, .85, .5], [.6, .85, 1]], plate: [.04, .05, .08] },
    ganesha: { water: [.03, .01, .005], deep: [.2, .05, .02], mid: [.85, .3, .08], gold: [1, .78, .35], hot: [1, .95, .8], dye: [[1, .35, .1], [1, .7, .2]],      sand: [[1, .82, .45], [1, .55, .25]], plate: [.09, .05, .03] },
    surya:   { water: [.02, .012, .01], deep: [.12, .05, .03], mid: [1, .42, .08], gold: [1, .78, .35], hot: [1, .97, .85], dye: [[1, .25, .12], [1, .6, .15]],    sand: [[1, .86, .55], [1, .66, .3]], plate: [.08, .055, .035] },
    peace:   { water: [.004, .02, .025], deep: [.02, .12, .13], mid: [.2, .6, .55], gold: [.98, .9, .7], hot: [1, .98, .9], dye: [[.45, .95, .8], [1, .8, .5]],     sand: [[.95, .92, .8], [.6, .95, .85]], plate: [.04, .07, .07] },
  };

  // ---------- audio analysis ----------
  const CTX = { ac: null, nodes: new WeakMap() };
  function analyser(media) {
    if (!CTX.ac) CTX.ac = new (window.AudioContext || window.webkitAudioContext)();
    let an = CTX.nodes.get(media);
    if (!an) { const src = CTX.ac.createMediaElementSource(media); an = CTX.ac.createAnalyser(); an.fftSize = 2048; an.smoothingTimeConstant = 0.7; src.connect(an); an.connect(CTX.ac.destination); an._src = src; CTX.nodes.set(media, an); }
    const td = new Float32Array(an.fftSize), fdb = new Float32Array(an.frequencyBinCount);
    const S = { amp: 0, low: 0, f0: 0, clarity: 0, centroid: 0, peaks: [] };
    function pitch(sr) {
      const n = 1024, lo = Math.floor(sr / 700), hi = Math.floor(sr / 70); let e0 = 0; for (let i = 0; i < n; i++) e0 += td[i] * td[i];
      if (e0 < 1e-4) return [0, 0]; let best = 0, bl = 0;
      for (let l = lo; l <= hi; l += 1) { let c = 0, e1 = 0; for (let i = 0; i < n; i += 2) { c += td[i] * td[i + l]; e1 += td[i + l] * td[i + l]; } const r = c / Math.sqrt(e0 * 0.5 * e1 + 1e-9); if (r > best) { best = r; bl = l; } }
      return [bl ? sr / bl : 0, Math.min(1, best)];
    }
    return {
      resume() { CTX.ac.resume(); },
      stream() { const d = CTX.ac.createMediaStreamDestination(); an._src.connect(d); return d.stream; },   // the audio, for recording
      update() {
        an.getFloatTimeDomainData(td); let s = 0; for (let i = 0; i < td.length; i++) s += td[i] * td[i];
        S.amp = S.amp * 0.8 + Math.min(1, Math.sqrt(s / td.length) * 4.5) * 0.2;
        const sr = CTX.ac.sampleRate, hz = sr / an.fftSize; [S.f0, S.clarity] = pitch(sr);
        an.getFloatFrequencyData(fdb); let num = 0, den = 0, low = 0; const pk = [];
        for (let i = Math.floor(60 / hz); i < Math.floor(3000 / hz); i++) { const m = Math.pow(10, fdb[i] / 20); num += m * i * hz; den += m; if (i * hz < 250) low += m;
          if (fdb[i] > fdb[i - 1] && fdb[i] >= fdb[i + 1] && fdb[i] > -70) pk.push([i * hz, fdb[i]]); }
        S.centroid = den ? num / den : 0; S.low = S.low * 0.85 + Math.min(1, (den ? low / den : 0) * 2) * 0.15; S.peaks = pk.sort((a, b) => b[1] - a[1]).slice(0, 3);
        return S;
      },
    };
  }

  // ---------- word timing helpers ----------
  function words(units) { return (units || []).flatMap((u, ui) => (u.words || []).filter(w => w.start != null).map((w, wi) => ({ ...w, ui, wi }))); }
  function wordAt(W, t) { let w = null; for (const x of W) if (t >= x.start - 0.08 && t < x.end + 0.25) w = x; return w; }

  // ---------- WebGL helpers ----------
  function glProgram(gl, vs, fs) {
    const sh = (type, src) => { const o = gl.createShader(type); gl.shaderSource(o, src); gl.compileShader(o); if (!gl.getShaderParameter(o, gl.COMPILE_STATUS)) console.error(gl.getShaderInfoLog(o), src); return o; };
    const p = gl.createProgram(); gl.attachShader(p, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(p, sh(gl.FRAGMENT_SHADER, fs)); gl.linkProgram(p); return p;
  }
  const QUAD = new Float32Array([-1, -1, 3, -1, -1, 3]);

  // =====================================================================================================
  // Nāda: sand on a bronze plate that hears the chant
  // =====================================================================================================
  function nada(cv, opts) {
    const W = cv.width = 1280, H = cv.height = 720;
    const gl = cv.getContext('webgl', { preserveDrawingBuffer: true, antialias: false, alpha: false });
    const P = PAL[opts.deity] || PAL.peace;
    const N = 26000, px = new Float32Array(N), py = new Float32Array(N), pos = new Float32Array(N * 2), col = new Float32Array(N * 3), sz = new Float32Array(N);
    const R = H * 0.44, CX = W / 2, CY = H * 0.5, TILT = 0.62;                  // the plate seen from above at an angle: an ellipse
    for (let i = 0; i < N; i++) { const k = Math.random(), c0 = P.sand[0], c1 = P.sand[1], v = 0.75 + Math.random() * 0.25;
      for (let j = 0; j < 3; j++) col[i * 3 + j] = (c0[j] * (1 - k * k) + c1[j] * k * k) * v; sz[i] = Math.random() < 0.06 ? 3.2 : 1.6 + Math.random() * 0.8; }
    const plateP = glProgram(gl, 'attribute vec2 p;varying vec2 v;void main(){v=p;gl_Position=vec4(p,0.,1.);}',
      `precision highp float;varying vec2 v;uniform float amp,al,t,rip;uniform vec2 res,c;uniform vec3 plate,glowc;
      void main(){vec2 q=(v*.5+.5)*res;vec2 d=(q-c)/vec2(${R.toFixed(1)},${(R * TILT).toFixed(1)});float r=length(d);
        vec3 bg=plate*.35*(1.-.5*length(v));
        float inside=smoothstep(1.01,.995,r);
        float mach=.5+.5*sin(r*180.);                                   // fine lathe rings on the metal
        float sheen=pow(max(0.,1.-length(d-vec2(-.35+.15*sin(t*.07),-.45))*.9),3.);   // a soft key light
        vec3 metal=plate*(1.1+.25*mach)+glowc*sheen*(.10+.12*amp);
        float rimL=exp(-pow((r-1.)*55.,2.));                            // the bevelled rim catches light
        float wave=exp(-pow((r-rip)*12.,2.))*step(0.,rip)*(1.-rip);       // a ring of light runs out on each new word
        vec3 col=mix(bg,metal,inside)+glowc*rimL*(.5+.6*amp)+glowc*wave*.35*inside;
        float shadow=smoothstep(1.25,1.0,length(d*vec2(1.,1.)+vec2(0.,-.08)))*(1.-inside);
        col=mix(col,col*.4,shadow*.6);
        gl_FragColor=vec4(col,al);}`);
    const ptP = glProgram(gl, `attribute vec2 a;attribute vec3 cc;attribute float s;uniform vec2 res;uniform float k;varying vec3 vc;
      void main(){gl_Position=vec4(a/res*2.-1.,0.,1.);gl_Position.y*=-1.;gl_PointSize=s*k;vc=cc;}`,
      `precision mediump float;varying vec3 vc;uniform float al;void main(){vec2 d=gl_PointCoord-.5;float f=exp(-dot(d,d)*16.);gl_FragColor=vec4(vc*f*al,1.);}`);
    const buf = (data, usage) => { const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, data, usage); return b; };
    const qb = buf(QUAD, gl.STATIC_DRAW), pb = buf(pos.byteLength, gl.DYNAMIC_DRAW), cb = buf(col, gl.STATIC_DRAW), sb = buf(sz, gl.STATIC_DRAW);
    const W0 = words(opts.units);
    function reset() { for (let i = 0; i < N; i++) { const a = Math.random() * TAU, r = Math.sqrt(Math.random()); px[i] = Math.cos(a) * r; py[i] = Math.sin(a) * r; } }
    reset();
    const same = (a, b) => a && b && a.k === b.k && a.m === b.m && a.n2 === b.n2 && a.w2 === b.w2;
    function f(M, x, y) {
      const r = Math.hypot(x, y), th = Math.atan2(y, x), PI = Math.PI;
      const circ = M.m === 0 ? Math.sin(M.k * PI * r) : Math.cos(M.k * PI * r) * Math.cos(M.m * th);
      if (!M.w2) return circ;
      const sq = Math.cos(M.n2 * PI * x / 1.4) * Math.cos(M.m2 * PI * y / 1.4) - Math.cos(M.m2 * PI * x / 1.4) * Math.cos(M.n2 * PI * y / 1.4);
      return circ * (1 - M.w2) + sq * M.w2;
    }
    let lastF0 = 150, cur = { k: 1.5, m: 0, w2: 0 }, prev = cur, changedAt = -9, cand = null, candAt = 0, lastWord = null, ripT = -9;
    function target(A) {
      if (A.amp < 0.03) return null;
      let f0 = A.clarity > 0.55 && A.f0 > 60 ? A.f0 : lastF0; if (f0 > 620) f0 /= 2; lastF0 = f0;
      const k = Math.max(1, Math.min(6, Math.round((1.0 + 1.7 * Math.log2(f0 / 75)) * 2) / 2));
      const m = Math.max(0, Math.min(10, Math.round(Math.log2(Math.max(A.centroid, 120) / 120) * 3.2 - 1)));
      const p2 = A.peaks[1], w2 = p2 && A.peaks[0] ? Math.max(0, Math.min(0.6, 1 + (p2[1] - A.peaks[0][1]) / 20)) : 0;
      const n2 = p2 ? Math.max(2, Math.min(9, Math.round(Math.log2(p2[0] / 60) * 2.2))) : 3;
      return { k, m, n2, m2: (n2 + m) % 7 + 1, w2: Math.round(w2 * 4) / 4 };
    }
    function step(t, A) {
      const now = performance.now() / 1000, T = target(A), w = wordAt(W0, t);
      if (w && w !== lastWord) { lastWord = w; ripT = now; }
      if (T && !same(T, cur)) { if (!same(T, cand)) { cand = T; candAt = now; } else if (now - candAt > 0.12) { prev = cur; cur = T; changedAt = now; cand = null;
        for (let i = 0; i < N; i += 4) { px[i] += (Math.random() - .5) * .05; py[i] += (Math.random() - .5) * .05; } } }
      if (!T) return;
      const u = Math.min(1, (now - changedAt) / 0.35), e = 1.5e-3, jit = 0.001 + A.amp * 0.014, st = 0.025 + 0.02 * A.amp;
      for (let i = 0; i < N; i++) {
        let x = px[i], y = py[i];
        const F = (a, b) => { const fa = f(cur, a, b); return u >= 1 ? fa : fa * u + f(prev, a, b) * (1 - u); };
        const f0 = F(x, y), gx = (F(x + e, y) - f0) / e, gy = (F(x, y + e) - f0) / e, kk = f0 / (gx * gx + gy * gy + 1e-6);
        x -= gx * kk * st * 6; y -= gy * kk * st * 6; x += (Math.random() - .5) * jit; y += (Math.random() - .5) * jit;
        const r = x * x + y * y; if (r > 0.99) { const s = 0.99 / Math.sqrt(r); x *= s; y *= s; } px[i] = x; py[i] = y;
      }
    }
    function frame(t, A) {
      step(t, A);
      const now = performance.now() / 1000, rip = (now - ripT) / 1.4;
      gl.viewport(0, 0, W, H); gl.enable(gl.BLEND);
      gl.useProgram(plateP); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
      gl.bindBuffer(gl.ARRAY_BUFFER, qb); let l = gl.getAttribLocation(plateP, 'p'); gl.enableVertexAttribArray(l); gl.vertexAttribPointer(l, 2, gl.FLOAT, false, 0, 0);
      const U = n => gl.getUniformLocation(plateP, n);
      gl.uniform1f(U('amp'), A.amp); gl.uniform1f(U('al'), 0.38); gl.uniform1f(U('t'), now); gl.uniform1f(U('rip'), rip < 1 ? rip : -1);
      gl.uniform2f(U('res'), W, H); gl.uniform2f(U('c'), CX, H - CY); gl.uniform3fv(U('plate'), P.plate); gl.uniform3fv(U('glowc'), P.gold);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      for (let i = 0; i < N; i++) { pos[i * 2] = CX + px[i] * R; pos[i * 2 + 1] = CY + py[i] * R * TILT; }
      gl.useProgram(ptP); gl.blendFunc(gl.ONE, gl.ONE);
      gl.bindBuffer(gl.ARRAY_BUFFER, pb); gl.bufferSubData(gl.ARRAY_BUFFER, 0, pos); l = gl.getAttribLocation(ptP, 'a'); gl.enableVertexAttribArray(l); gl.vertexAttribPointer(l, 2, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, cb); l = gl.getAttribLocation(ptP, 'cc'); gl.enableVertexAttribArray(l); gl.vertexAttribPointer(l, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, sb); l = gl.getAttribLocation(ptP, 's'); gl.enableVertexAttribArray(l); gl.vertexAttribPointer(l, 1, gl.FLOAT, false, 0, 0);
      gl.uniform2f(gl.getUniformLocation(ptP, 'res'), W, H);
      const K = gl.getUniformLocation(ptP, 'k'), AL = gl.getUniformLocation(ptP, 'al');
      gl.uniform1f(K, 4.5); gl.uniform1f(AL, 0.035 + A.amp * 0.05); gl.drawArrays(gl.POINTS, 0, N);   // glow
      gl.uniform1f(K, 1.0); gl.uniform1f(AL, 0.42 + A.amp * 0.3); gl.drawArrays(gl.POINTS, 0, N);     // grains
    }
    return { frame, reset };
  }

  // =====================================================================================================
  // Liquid gold: pigment flowing in dark water, stirred by the voice
  // =====================================================================================================
  function gold(cv, opts) {
    cv.width = 1280; cv.height = 720;
    const gl = cv.getContext('webgl', { antialias: false, alpha: false }); const P = PAL[opts.deity] || PAL.peace;
    const fs = `precision highp float;uniform vec2 res;uniform float t,amp,low,fade;uniform vec4 B[6];
    uniform vec3 water,deep,mid,gold,hot,dye1,dye2;
    float h(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
    float n(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(h(i),h(i+vec2(1,0)),f.x),mix(h(i+vec2(0,1)),h(i+vec2(1,1)),f.x),f.y);}
    float fbm(vec2 p){float s=0.,a=.5;mat2 m=mat2(1.6,1.2,-1.2,1.6);for(int i=0;i<6;i++){s+=a*n(p);p=m*p;a*=.5;}return s;}
    void main(){vec2 uv=(gl_FragCoord.xy-.5*res)/res.y;float T=t*.06;
      vec2 p=uv*(2.1-.08*sin(t*.05))+vec2(.0,T*.4);                                   // slow drift, like a camera
      vec2 q=vec2(fbm(p+vec2(0.,T)),fbm(p+vec2(5.2,1.3)-T));
      float w=2.4+amp*2.4+low*1.2;
      vec2 r=vec2(fbm(p+w*q+vec2(1.7,9.2)+T*1.5),fbm(p+w*q+vec2(8.3,2.8)-T));
      float f=fbm(p+w*r);
      vec3 col=mix(water,deep,clamp(length(q)*1.1,0.,1.));
      col=mix(col,mid*.55,clamp(f*f*1.5,0.,1.)*.6);
      float vein=smoothstep(.55,.95,f)*smoothstep(.2,.9,length(r));
      col+=gold*pow(vein,1.6)*(1.0+amp*1.5);
      col+=hot*pow(vein,6.)*(.5+amp*2.2);
      // god rays from above, through the water
      float ray=pow(max(0.,fbm(vec2(uv.x*3.+uv.y*.6,t*.05))-.35),2.)*smoothstep(-.6,.5,uv.y);
      col+=gold*ray*.35*(.6+amp);
      // gold dust drifting up
      vec2 g=uv*vec2(26.,15.)+vec2(0.,-t*.35);vec2 gi=floor(g);float sp=h(gi);vec2 gf=fract(g)-vec2(h(gi+3.1),h(gi+7.7));
      col+=hot*smoothstep(.05,.0,length(gf))*step(.93,sp)*(.4+.6*sin(t*2.+sp*40.))*(.5+amp);
      // a bloom of colour on each word
      for(int i=0;i<6;i++){vec4 b=B[i];if(b.w<0.)continue;float age=b.w;vec2 c=b.xy+.12*(r-.5);
        float d=length(uv-c);float rad=.05+age*.24;float ring=exp(-pow((d-rad)/(.05+age*.06),2.))*exp(-age*.5);
        col+=mix(dye1,dye2,b.z)*ring*(.6+.6*fbm(uv*6.+age));}
      col*=1.-.55*dot(uv,uv);col*=fade;gl_FragColor=vec4(pow(col,vec3(.9)),1.);}`;
    const pr = glProgram(gl, 'attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}', fs); gl.useProgram(pr);
    const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, QUAD, gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(pr, 'p'); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    const U = n => gl.getUniformLocation(pr, n);
    for (const k of ['water', 'deep', 'mid', 'gold', 'hot']) gl.uniform3fv(U(k), P[k]); gl.uniform3fv(U('dye1'), P.dye[0]); gl.uniform3fv(U('dye2'), P.dye[1]);
    const W0 = words(opts.units), blooms = []; let lastW = null; const t0 = performance.now();
    function frame(t, A) {
      const w = wordAt(W0, t);
      if (w && w !== lastW) { lastW = w; const a = Math.random() * TAU, r = 0.15 + Math.random() * 0.3; blooms.push({ x: Math.cos(a) * r * 1.4, y: Math.sin(a) * r * .7, k: Math.random(), t0: t }); if (blooms.length > 6) blooms.shift(); }
      const B = new Float32Array(24).fill(-1); blooms.forEach((bl, i) => { const age = t - bl.t0; if (age >= 0 && age < 9) { B[i * 4] = bl.x; B[i * 4 + 1] = bl.y; B[i * 4 + 2] = bl.k; B[i * 4 + 3] = age; } });
      const wall = (performance.now() - t0) / 1000;
      gl.viewport(0, 0, cv.width, cv.height); gl.uniform2f(U('res'), cv.width, cv.height); gl.uniform1f(U('t'), t + wall * 0.15);
      gl.uniform1f(U('amp'), A.amp); gl.uniform1f(U('low'), A.low); gl.uniform1f(U('fade'), Math.min(1, wall / 1.5)); gl.uniform4fv(U('B'), B); gl.drawArrays(gl.TRIANGLES, 0, 3);
    }
    return { frame, reset() { blooms.length = 0; } };
  }

  window.VakFX = { create: (kind, cv, opts) => (kind === 'nada' ? nada : gold)(cv, opts || {}), analyser, deityOf, words, wordAt, PAL };
})();
