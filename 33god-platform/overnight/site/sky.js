/* sky.js: a living night sky for any 33GOD stage. Plain JS, no libraries, no raw colours (every colour is a token, read
   from the host at layout time, so a [data-theme] block re-colours it).

   One field is two <canvas> layers on a host element. The host becomes an isolated stacking context; the sky canvas sits
   at z-index -1, behind the host's own drawing (its SVG city is always in front of the sky), and a spark canvas sits at
   z-index 1, in front of it (so sparks rising past a facade are seen, not hidden behind it). Back to front:
     stars     three depth layers; each drifts against the scroll at its own rate (parallax), twinkles, leans toward the
               pointer on a fine pointer, and streaks briefly when the page is flicked; a few are bright and glow
     meteors   an occasional shooting star (opts.meteors per minute; only where the sky is tall enough to see one)
     skyline   opts.skyline layers of distant city standing on the horizon, full height at rest and sinking behind the
               ground at their own parallax rate as the host scrolls away, with a horizon glow and windows that blink
     motes     (spark canvas) sparks that leave the host's lit windows (any element marked data-sky-emit, in its own fill
               colour) and rise into the sky; the pointer pushes them aside and a scroll leaves them a little behind

   Markup the field reads (all optional):
     [data-sky-horizon]   an element whose top edge is the ground: stars live above it, the skyline stands on it, and a
                          ground rule as thick as its stroke runs the canvas' whole width (default: opts.band of the host)
     [data-sky-emit="w"]  a lit window that releases sparks, weight w (default 1), in its computed fill colour

   API:
     G33Sky.mount(host, opts) -> field     opts: seed, density (px² per star; lower is denser), max (star cap), band,
                                           meteors (per minute), motes (per second), skyline (0..2), pointer (bool),
                                           bleed [t, r, b, l] px the canvases reach past the host, fade [t, r, b, l] px
                                           the sky dissolves over at each canvas edge (either may be a function
                                           (host, rect) -> array, re-read at every layout)
     G33Sky.place()                        re-read where each host sits on the page (call from a page's own geometry pass)
     G33Sky.stats()                        what each field is doing (tests)
     <div data-sky="meteors motes skyline" data-sky-seed="7">  mounts itself on DOMContentLoaded (static pages)

   Discipline (the same as front.js): geometry is read once per layout change (mount, a ResizeObserver on the host, a
   viewport resize, place()), never per frame; a frame is arithmetic on scrollY plus canvas calls. A host inside a sticky
   element (a pinned exhibit) has its sticky geometry cached, so its on-screen position is still arithmetic. Only fields on
   screen animate, nothing runs in a hidden tab, and prefers-reduced-motion draws one still frame per layout. */
(function () {
  'use strict';
  if (window.G33Sky) return;

  var flat = false;
  try { flat = matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) { flat = false; }
  var finePointer = false;
  try { finePointer = matchMedia('(pointer: fine)').matches; } catch (e) { finePointer = false; }

  var fields = [], raf = 0, last = 0, sy = 0, vy = 0, vh = 0;
  var ptr = { cx: -1e4, cy: -1e4, nx: 0, ny: 0, tx: 0, ty: 0 };
  /* parallax rate of each star layer against the scroll: 0 moves with the page, 1 stays fixed on screen */
  var LAYER_K = [0.9, 0.72, 0.48];
  var LAYER_DEPTH = [0.3, 0.6, 1];
  /* how fast each skyline layer sinks behind the ground per px of scroll (far, near) */
  var SKY_K = [0.18, 0.1];
  var TAU = 6.283185307;

  function rng(seed) { seed = (Math.abs(seed | 0) % 2147483646) + 1; return function () { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; }; }
  function clamp(x, a, b) { return Math.max(a, Math.min(b, x)); }

  /* ---------- colours: a token, resolved inside the host, as [r, g, b] ---------- */
  var swatch = null;
  function parseRGB(c) {
    c = String(c || '').trim();
    if (!c || c === 'none' || c === 'transparent') return null;
    var m = /^rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)(?:[\s,/]+([\d.]+)(%?))?\s*\)$/.exec(c);
    if (m) {
      if (m[4] !== undefined && parseFloat(m[4]) === 0) return null;
      return [Math.round(+m[1]), Math.round(+m[2]), Math.round(+m[3])];
    }
    m = /^color\(srgb\s+([\d.e-]+)\s+([\d.e-]+)\s+([\d.e-]+)(?:\s*\/\s*([\d.]+)(%?))?\s*\)$/.exec(c);
    if (m) {
      if (m[4] !== undefined && parseFloat(m[4]) === 0) return null;
      return m.slice(1, 4).map(function (v) { return Math.round(clamp(+v, 0, 1) * 255); });
    }
    /* anything else Chrome may serialise (oklch, lab, display-p3): let a 1x1 canvas convert it */
    try {
      if (!swatch) { swatch = document.createElement('canvas').getContext('2d', { willReadFrequently: true }); swatch.canvas.width = swatch.canvas.height = 1; }
      swatch.clearRect(0, 0, 1, 1); swatch.fillStyle = c; swatch.fillRect(0, 0, 1, 1);
      var d = swatch.getImageData(0, 0, 1, 1).data;
      return d[3] ? [d[0], d[1], d[2]] : null;
    } catch (e) { return null; }
  }
  function tokenRGB(host, name) {
    var p = document.createElement('span');
    p.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden;visibility:hidden;color:var(' + name + ')';
    host.appendChild(p);
    var c = getComputedStyle(p).color;
    host.removeChild(p);
    return parseRGB(c);
  }
  function rgba(p, a) { return 'rgba(' + p[0] + ',' + p[1] + ',' + p[2] + ',' + a + ')'; }

  /* One soft glow sprite per colour, drawn once and stamped with drawImage (a gradient per particle per frame is not cheap).
     The sprite rides on the colour array itself, so a frame never builds a cache key. */
  var spriteCache = {};
  function sprite(p) {
    if (p.spr) return p.spr;
    var key = p.join(',');
    if (!spriteCache[key]) {
      var c = document.createElement('canvas'); c.width = c.height = 32;
      var g = c.getContext('2d'), gr = g.createRadialGradient(16, 16, 0, 16, 16, 16);
      gr.addColorStop(0, rgba(p, 1)); gr.addColorStop(0.16, rgba(p, 0.9)); gr.addColorStop(0.42, rgba(p, 0.25)); gr.addColorStop(1, rgba(p, 0));
      g.fillStyle = gr; g.fillRect(0, 0, 32, 32);
      spriteCache[key] = c;
    }
    return (p.spr = spriteCache[key]);
  }
  function ink(p) { return p.ink || (p.ink = rgba(p, 1)); }

  /* ---------- a field ---------- */
  function Field(host, o) {
    this.host = host;
    this.o = {
      seed: o.seed == null ? 1 : o.seed, density: o.density || 1100, max: o.max || 420, band: o.band || 1,
      meteors: flat ? 0 : (o.meteors || 0), motes: flat ? 0 : (o.motes || 0), skyline: Math.min(2, o.skyline || 0),
      pointer: o.pointer !== false && finePointer && !flat,
      bleed: o.bleed || null, fade: o.fade || null
    };
    this.live = !window.IntersectionObserver;
    this.frames = 0; this.w = 0; this.h = 0; this.dpr = 0; this.bl = [0, 0, 0, 0];
    this.stars = []; this.motes = []; this.meteors = []; this.emit = []; this.layers = []; this.fadeKey = '';
    this.nextMeteor = 0; this.emitAcc = 0; this.flickAcc = 0; this.fgBox = null; this.stick = null;
    if (getComputedStyle(host).position === 'static') host.style.position = 'relative';
    host.style.isolation = 'isolate';
    this.cv = this.canvas(-1);
    this.ctx = this.cv.getContext('2d');
    if (this.o.motes) { this.fg = this.canvas(1); this.fctx = this.fg.getContext('2d'); }
    this.layout();
  }

  Field.prototype.canvas = function (z) {
    var cv = document.createElement('canvas');
    cv.className = z < 0 ? 'g33-sky' : 'g33-sky g33-sky--sparks';
    cv.setAttribute('aria-hidden', 'true');
    cv.style.cssText = 'position:absolute;left:0;top:0;width:100%;height:100%;display:block;pointer-events:none;z-index:' + z;
    if (z < 0) this.host.insertBefore(cv, this.host.firstChild); else this.host.appendChild(cv);
    return cv;
  };

  function edges(v, host, r) {
    if (typeof v === 'function') v = v(host, r);
    if (!v) return [0, 0, 0, 0];
    return [0, 1, 2, 3].map(function (i) { return Math.max(0, Math.round(+v[i] || 0)); });
  }
  function dprFor(area) {
    /* small canvases stay sharp on dense phones; a big one trades a little sharpness for frame time */
    return Math.min(window.devicePixelRatio || 1, area < 120000 ? 3 : area < 250000 ? 2 : 1.5);
  }

  /* The canvas box: the host's box grown by the bleed. Everything a field draws is in this box's coordinates. */
  Field.prototype.box = function () {
    var r = this.host.getBoundingClientRect(), b = edges(this.o.bleed, this.host, r);
    return { r: r, b: b, w: r.width + b[1] + b[3], h: r.height + b[0] + b[2], left: r.left + scrollX - b[3], top: r.top + scrollY - b[0] };
  };

  /* Where the canvas box sits on the page, cached. Under a sticky ancestor the box moves with the sticky element, so we keep
     what it takes to place it arithmetically: the container's page top and height, the sticky element's height, its stick
     offset, its natural offset in the container and the box's offset inside it. */
  Field.prototype.anchor = function (B) {
    this.left = B.left; this.top = B.top; this.stick = null;
    for (var el = this.host.parentElement; el && el !== document.body; el = el.parentElement) {
      var cs = getComputedStyle(el);
      if (cs.position !== 'sticky') continue;
      var p = el.parentElement; if (!p) break;
      var er = el.getBoundingClientRect(), pr = p.getBoundingClientRect(), prev = el.previousElementSibling;
      this.stick = { pTop: pr.top + scrollY, pH: pr.height, sH: er.height, at: parseFloat(cs.top) || 0,
        nat: prev ? prev.offsetTop + prev.offsetHeight : 0, off: B.top - scrollY - er.top };
      break;
    }
  };
  /* the canvas box's top edge in the viewport at scroll position y */
  Field.prototype.vTop = function (y) {
    var s = this.stick;
    if (!s) return this.top - y;
    var natural = s.pTop + s.nat - y;
    return Math.min(Math.max(natural, s.at), s.pTop + s.pH - s.sH - y) + s.off;
  };

  Field.prototype.layout = function () {
    var host = this.host, B = this.box(), r = B.r, bl = B.b;
    var w = B.w, h = B.h, ox = bl[3], oy = bl[0];
    this.anchor(B);
    if (r.width < 2 || r.height < 2) { this.w = 0; return; }
    var sizeChanged = Math.abs(w - this.w) > 0.5 || Math.abs(h - this.h) > 0.5;
    this.w = w; this.h = h;
    var cvs = this.fg ? [this.cv, this.fg] : [this.cv];
    if (bl.join() !== this.bl.join()) {
      this.bl = bl;
      cvs.forEach(function (c) {
        var cs = c.style;
        cs.left = -bl[3] + 'px'; cs.top = -bl[0] + 'px';
        cs.width = 'calc(100% + ' + (bl[1] + bl[3]) + 'px)'; cs.height = 'calc(100% + ' + (bl[0] + bl[2]) + 'px)';
      });
    }
    var dpr = this.dpr = dprFor(w * h);
    var cw = Math.round(w * dpr), ch = Math.round(h * dpr);
    cvs.forEach(function (c) { if (c.width !== cw || c.height !== ch) { c.width = cw; c.height = ch; } c.getContext('2d').setTransform(dpr, 0, 0, dpr, 0, 0); });

    /* the ground: its top edge, and the rule as thick as the drawing's own stroke */
    var hzEl = host.querySelector('[data-sky-horizon]');
    this.rule = 0;
    if (hzEl) {
      var hb = hzEl.getBoundingClientRect(), sw = parseFloat(hzEl.getAttribute('stroke-width')) || 0, ctm = null;
      try { ctm = hzEl.getScreenCTM && hzEl.getScreenCTM(); } catch (e) { ctm = null; }
      var t = sw && hb.height < 1 ? sw * (ctm ? Math.abs(ctm.d) : 1) : 0;
      this.rule = t;
      this.hz = clamp(hb.top - r.top + oy - t / 2, 8, h);
    } else this.hz = oy + r.height * this.o.band;

    /* tokens only: a page without --window-lit gets no sky, never a guessed colour */
    var lit = tokenRGB(host, '--window-lit');
    if (!lit) { this.w = 0; this.ctx.clearRect(0, 0, w, h); return; }
    this.col = {
      lit: lit,
      cool: tokenRGB(host, '--window-working') || lit,
      warm: tokenRGB(host, '--window-you') || lit,
      far: tokenRGB(host, '--facade-edge') || tokenRGB(host, '--stage-rule'),
      near: tokenRGB(host, '--facade'),
      rule: tokenRGB(host, '--stage-rule') || tokenRGB(host, '--facade-edge')
    };

    /* emitters: where they sit inside the canvas box now (they move with it, so this holds until the next layout);
       one a sliced SVG has pushed off the canvas releases nothing */
    var em = [], tw = 0;
    [].forEach.call(host.querySelectorAll('[data-sky-emit]'), function (el) {
      var b = el.getBoundingClientRect();
      if (b.width < 0.5 || b.height < 0.5) return;
      var x = b.left - r.left + ox, y = b.top - r.top + oy;
      if (x + b.width <= 0 || x >= w || y + b.height <= 0 || y >= h) return;
      var cs = getComputedStyle(el), c = parseRGB(cs.fill) || parseRGB(cs.color);
      if (!c) return;
      var wt = parseFloat(el.getAttribute('data-sky-emit')); if (!(wt > 0)) wt = 1;
      em.push({ x: x, y: y, w: b.width, h: b.height, c: c, wt: wt });
      tw += wt;
    });
    this.emit = em; this.emitW = tw;

    if (sizeChanged || !this.stars.length) { this.seedStars(); this.seedSkyline(); }
    this.seedFade();
    this.motes = this.motes.filter(function (m) { return m.x > -8 && m.x < w + 8 && m.y < h; });
    if (flat || !this.live) this.draw(0, 0, true);
  };

  Field.prototype.seedStars = function () {
    var r = rng(this.o.seed * 977 + 13), w = this.w, hz = this.hz, col = this.col;
    var n = Math.round(clamp((w * hz) / this.o.density, 6, this.o.max));
    var st = [];
    for (var i = 0; i < n; i++) {
      var q = r(), l = q < 0.55 ? 0 : q < 0.85 ? 1 : 2, pick = r(), bright = r() < 0.08;
      st.push({
        x: r() * w, y: Math.pow(r(), 1.3) * (hz + 8), l: l,
        s: bright ? 1.8 + r() * 0.6 : l === 0 ? 0.8 + r() * 0.4 : l === 1 ? 1.1 + r() * 0.5 : 1.4 + r() * 0.6,
        a: bright ? 0.85 + r() * 0.15 : l === 0 ? 0.4 + r() * 0.35 : l === 1 ? 0.5 + r() * 0.35 : 0.65 + r() * 0.35,
        tw: 0.5 + r() * 2.6, ph: r() * TAU,
        c: pick < 0.78 ? col.lit : pick < 0.93 ? col.cool : col.warm,
        g: bright || (l === 2 && r() < 0.35)
      });
    }
    /* drawn grouped by colour, so the canvas changes fillStyle a few times a frame, not hundreds */
    var order = function (c) { return c === col.lit ? 0 : c === col.cool ? 1 : 2; };
    st.sort(function (a, b) { return order(a.c) - order(b.c); });
    this.stars = st;
  };

  Field.prototype.seedSkyline = function () {
    this.layers = [];
    if (!this.o.skyline || !this.col.far || !this.col.near) return;
    var hz = this.hz, w = this.w, col = this.col;
    for (var L = 0; L < this.o.skyline; L++) {
      var r = rng(this.o.seed * 131 + L * 71 + 5), far = L === 0, bl = [], x = -12 - r() * 20;
      var maxH = Math.min(far ? 130 : 84, hz * (far ? 0.3 : 0.22)), minH = maxH * 0.2;
      while (x < w + 12) {
        var bw = far ? 10 + r() * 28 : 14 + r() * 34, bh = minH + Math.pow(r(), 1.5) * (maxH - minH), wins = [];
        var cols = Math.max(1, Math.floor((bw - 4) / 5)), rows = Math.max(1, Math.floor((bh - 5) / 6));
        for (var k = 0; k < Math.min(24, cols * rows); k++) if (r() < (far ? 0.14 : 0.22)) {
          var pick = r();
          wins.push({ dx: 2.5 + (k % cols) * 5, dy: 4 + Math.floor(k / cols) * 6, on: r() < 0.7, c: pick < 0.6 ? col.cool : pick < 0.85 ? col.lit : col.warm });
        }
        var spire = bh > maxH * 0.7 && r() < 0.35;
        bl.push({ x: x, w: bw, h: bh, wins: wins, spire: spire });
        x += bw + (far ? r() * 3 : 1 + r() * 7);
      }
      this.layers.push({ b: bl, c: far ? col.far : col.near, a: far ? 0.85 : 1, k: SKY_K[L], depth: far ? 0.3 : 0.6, rim: !far });
    }
    var g = this.ctx.createLinearGradient(0, hz - Math.min(110, hz * 0.6), 0, hz);
    g.addColorStop(0, rgba(col.warm, 0)); g.addColorStop(1, rgba(col.warm, 0.13));
    this.glow = g;
  };

  /* the edge fades: a CSS mask on both canvases (the compositor does it, not every frame's raster); only the mask's alpha
     counts, so its colour is just the field's own star token */
  Field.prototype.seedFade = function () {
    var f = edges(this.o.fade, this.host, this.host.getBoundingClientRect()), c = this.col.lit, key = f.join();
    if (key === this.fadeKey) return;
    this.fadeKey = key;
    var on = rgba(c, 1), off = rgba(c, 0), dirs = ['to bottom', 'to left', 'to top', 'to right'], layers = [];
    for (var i = 0; i < 4; i++) if (f[i]) layers.push('linear-gradient(' + dirs[i] + ', ' + off + ' 0px, ' + on + ' ' + f[i] + 'px)');
    var m = layers.join(', '), comp = layers.length > 1 ? layers.map(function () { return 'intersect'; }).join(', ') : '';
    (this.fg ? [this.cv, this.fg] : [this.cv]).forEach(function (cv) {
      cv.style.webkitMaskImage = m; cv.style.maskImage = m;
      cv.style.webkitMaskComposite = comp ? layers.map(function () { return 'source-in'; }).join(', ') : '';
      cv.style.maskComposite = comp;
    });
  };

  /* ---------- one frame ---------- */
  Field.prototype.draw = function (t, dt, still) {
    var w = this.w, h = this.h, hz = this.hz;
    if (!w) return;
    var ctx = this.ctx, o = this.o, col = this.col, i;
    ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
    ctx.clearRect(0, 0, w, h);
    var vhNow = vh || innerHeight, top = this.vTop(sy);
    /* rel: how far the box's middle sits above the viewport's middle (0 when centred), the star layers' phase.
       sink: how far the box has scrolled past the point where its bottom entered the viewport (0 at rest), the skyline's.
       A still frame has neither. */
    var rel = still ? 0 : vhNow / 2 - (top + h / 2);
    /* rest: where the box sits at scroll 0 if it is on the first screen, else where its bottom meets the viewport's */
    var sink = still ? 0 : Math.max(0, Math.min(this.top, vhNow - h) - top);
    this.moved = this.prevTop == null || still ? 0 : this.prevTop - top; this.prevTop = still ? null : top;
    var px = o.pointer ? ptr.nx : 0, py = o.pointer ? ptr.ny : 0;
    var streakV = still ? 0 : vy, streakMax = Math.min(22, h * 0.12);
    var span = hz + 8, cur = null, s, sp;

    /* stars */
    for (i = 0; i < this.stars.length; i++) {
      s = this.stars[i];
      var k = LAYER_K[s.l], d = LAYER_DEPTH[s.l];
      var y = s.y - rel * k + py * d * 9;
      y = y - span * Math.floor(y / span) - 4;
      if (y > hz) continue;
      var x = s.x + px * d * 16;
      var a = s.a * (still ? 0.85 : 0.45 + 0.55 * (0.5 + 0.5 * Math.sin(t * s.tw + s.ph)));
      if (y > hz - 14) a *= (hz - y) / 14;
      if (a <= 0.02) continue;
      if (s.g) {
        sp = sprite(s.c); ctx.globalAlpha = a * 0.6;
        var gs = s.s * 7; ctx.drawImage(sp, x - gs / 2, y - gs / 2, gs, gs);
      }
      if (cur !== s.c) { cur = s.c; ctx.fillStyle = ink(s.c); }
      ctx.globalAlpha = a;
      var L = Math.min(streakMax, Math.abs(streakV) * (1 - k) * 0.9);
      if (L > 1) ctx.fillRect(x - s.s / 2, streakV > 0 ? y - s.s / 2 : y - s.s / 2 - L, s.s, s.s + L);
      else ctx.fillRect(x - s.s / 2, y - s.s / 2, s.s, s.s);
    }

    /* meteors, behind the skyline; only where there is room to see one cross */
    if (o.meteors && !still && hz >= 70) {
      if (!this.nextMeteor) this.nextMeteor = t + (60 / o.meteors) * (0.2 + Math.random() * 0.5);
      if (t >= this.nextMeteor) {
        this.nextMeteor = t + (60 / o.meteors) * (0.5 + Math.random());
        var dir = Math.random() < 0.5 ? -1 : 1, ang = (14 + Math.random() * 24) * Math.PI / 180, sc = clamp(w / 700, 0.5, 1.4);
        this.meteors.push({ x: w * (0.15 + Math.random() * 0.7), y: hz * Math.random() * 0.4, dx: Math.cos(ang) * dir, dy: Math.sin(ang),
          v: (380 + Math.random() * 360) * sc, life: 0, max: 0.55 + Math.random() * 0.55, tail: (70 + Math.random() * 90) * sc });
      }
      if (this.meteors.length) {
        ctx.save(); ctx.beginPath(); ctx.rect(0, 0, w, hz); ctx.clip();
        ctx.lineCap = 'round';
        for (i = this.meteors.length - 1; i >= 0; i--) {
          var m = this.meteors[i]; m.life += dt;
          if (m.life >= m.max) { this.meteors.splice(i, 1); continue; }
          var p = m.life / m.max, hx = m.x + m.dx * m.v * m.life, hy = m.y + m.dy * m.v * m.life, tl = m.tail * Math.min(1, p * 3);
          var gr = ctx.createLinearGradient(hx, hy, hx - m.dx * tl, hy - m.dy * tl);
          var ma = Math.sin(Math.PI * p);
          gr.addColorStop(0, rgba(col.lit, 0.95 * ma)); gr.addColorStop(1, rgba(col.lit, 0));
          ctx.globalAlpha = 1; ctx.strokeStyle = gr; ctx.lineWidth = 1.5;
          ctx.beginPath(); ctx.moveTo(hx, hy); ctx.lineTo(hx - m.dx * tl, hy - m.dy * tl); ctx.stroke();
          ctx.globalAlpha = ma; ctx.drawImage(sprite(col.lit), hx - 6, hy - 6, 12, 12);
        }
        ctx.restore();
      }
    } else if (this.meteors.length) this.meteors.length = 0;

    /* the distant city on the horizon: full height at rest, sinking behind the ground as the box scrolls away */
    if (this.layers.length) {
      ctx.globalAlpha = 1; ctx.fillStyle = this.glow; ctx.fillRect(0, 0, w, hz);
      ctx.save(); ctx.beginPath(); ctx.rect(0, 0, w, hz); ctx.clip();
      if (!still) {
        this.flickAcc += dt * 1.2;
        while (this.flickAcc > 1) {
          this.flickAcc -= 1;
          var lay = this.layers[(Math.random() * this.layers.length) | 0], bb = lay.b[(Math.random() * lay.b.length) | 0];
          if (bb && bb.wins.length) { var wi = bb.wins[(Math.random() * bb.wins.length) | 0]; wi.on = !wi.on; }
        }
      }
      for (var li = 0; li < this.layers.length; li++) {
        var ly = this.layers[li], off = Math.min(h, sink * ly.k) + py * ly.depth * 4, ox = px * ly.depth * 8;
        ctx.globalAlpha = ly.a; ctx.fillStyle = ink(ly.c);
        var bi, b, btop;
        for (bi = 0; bi < ly.b.length; bi++) {
          b = ly.b[bi]; btop = hz - b.h + off;
          ctx.fillRect(b.x + ox, btop, b.w, b.h + h);
          if (b.spire) ctx.fillRect(b.x + ox + b.w / 2 - 0.75, btop - 8, 1.5, 8);
        }
        if (ly.rim && col.far) {
          ctx.globalAlpha = 0.55; ctx.fillStyle = ink(col.far);
          for (bi = 0; bi < ly.b.length; bi++) { b = ly.b[bi]; ctx.fillRect(b.x + ox, hz - b.h + off, b.w, 1); }
        }
        var wc = null;
        for (bi = 0; bi < ly.b.length; bi++) {
          b = ly.b[bi]; btop = hz - b.h + off;
          for (var wj = 0; wj < b.wins.length; wj++) {
            var wn = b.wins[wj]; if (!wn.on) continue;
            var wy = btop + wn.dy; if (wy > hz - 2 || wn.dx > b.w - 2) continue;
            if (wc !== wn.c) { wc = wn.c; ctx.fillStyle = ink(wn.c); }
            ctx.globalAlpha = li === 0 ? 0.4 : 0.65;
            ctx.fillRect(b.x + ox + wn.dx, wy, 1.6, 1.6);
          }
        }
      }
      ctx.restore();
    }
    if (this.rule && col.rule) { ctx.globalAlpha = 1; ctx.fillStyle = ink(col.rule); ctx.fillRect(0, hz, w, this.rule); }
    ctx.globalAlpha = 1;

    /* motes, on the spark canvas in front of the drawing: sparks leaving the lit windows */
    if (this.fg && !still) this.sparks(dt, h, w);
    this.frames++;
  };

  Field.prototype.sparks = function (dt, h, w) {
    var ctx = this.fctx, o = this.o, i;
    var bb = this.fgBox;
    if (bb) { ctx.clearRect(bb[0], bb[1], bb[2] - bb[0], bb[3] - bb[1]); this.fgBox = null; }
    if (this.emit.length) {
      this.emitAcc += dt * o.motes;
      while (this.emitAcc >= 1 && this.motes.length < 160) {
        this.emitAcc -= 1;
        var pickW = Math.random() * this.emitW, e = this.emit[0];
        for (var ei = 0; ei < this.emit.length; ei++) { pickW -= this.emit[ei].wt; if (pickW <= 0) { e = this.emit[ei]; break; } }
        this.motes.push({ x: e.x + Math.random() * e.w, y: e.y + Math.random() * e.h * 0.6, vx: (Math.random() - 0.5) * 6, vy: -(14 + Math.random() * 20),
          life: 0, max: 2.6 + Math.random() * 3.2, r: 0.9 + Math.random() * 1.4, c: e.c, ph: Math.random() * TAU, sw: 3 + Math.random() * 6 });
      }
      if (this.emitAcc > 1) this.emitAcc = 1;
    }
    if (!this.motes.length) return;
    var lx = ptr.cx - (this.left - scrollX), lyp = ptr.cy - this.vTop(sy), near = o.pointer && lx > -60 && lx < w + 60 && lyp > -60 && lyp < h + 60;
    ctx.globalCompositeOperation = 'lighter';
    var x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    for (i = this.motes.length - 1; i >= 0; i--) {
      var mo = this.motes[i]; mo.life += dt;
      if (mo.life >= mo.max) { this.motes.splice(i, 1); continue; }
      mo.x += (mo.vx + Math.cos(mo.life * 1.7 + mo.ph) * mo.sw) * dt;
      mo.y += mo.vy * dt + this.moved * 0.12;
      if (near) {
        var ddx = mo.x - lx, ddy = mo.y - lyp, d2 = ddx * ddx + ddy * ddy;
        if (d2 < 4900 && d2 > 0.01) { var f = (1 - d2 / 4900) * 90 * dt / Math.sqrt(d2); mo.x += ddx * f; mo.y += ddy * f; }
      }
      if (mo.y < -8 || mo.y > h + 8) { this.motes.splice(i, 1); continue; }
      var q = mo.life / mo.max, a = Math.min(1, mo.life / 0.45) * (q > 0.55 ? (1 - q) / 0.45 : 1);
      ctx.globalAlpha = a * (0.75 + 0.25 * Math.sin(mo.life * 9 + mo.ph)) * 0.9;
      var ms = mo.r * 8, mx = mo.x - ms / 2, my = mo.y - ms / 2;
      ctx.drawImage(sprite(mo.c), mx, my, ms, ms);
      if (mx < x0) x0 = mx; if (my < y0) y0 = my; if (mx + ms > x1) x1 = mx + ms; if (my + ms > y1) y1 = my + ms;
    }
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = 1;
    if (x1 > x0) this.fgBox = [Math.floor(x0) - 2, Math.floor(y0) - 2, Math.ceil(x1) + 2, Math.ceil(y1) + 2];
  };

  /* ---------- the loop ---------- */
  function anyLive() { for (var i = 0; i < fields.length; i++) if (fields[i].live && fields[i].w) return true; return false; }
  /* At rest (no scroll, the pointer settled, no meteor in flight) twinkle and sparks read the same at 30 fps, so a calm
     page draws every other frame; any motion goes straight back to every frame. */
  var odd = false;
  function calm() {
    if (Math.abs(vy) > 0.05 || Math.abs(scrollY - sy) > 0.5 || Math.abs(ptr.tx - ptr.nx) > 0.002 || Math.abs(ptr.ty - ptr.ny) > 0.002) return false;
    for (var i = 0; i < fields.length; i++) if (fields[i].live && fields[i].meteors.length) return false;
    return true;
  }
  function tick(now) {
    raf = 0;
    if (document.hidden || !anyLive()) return;
    odd = !odd;
    if (odd && calm()) { raf = requestAnimationFrame(tick); return; }
    var dt = Math.min(0.05, Math.max(0, (now - last) / 1000)); last = now;
    var y = scrollY, d = clamp(y - sy, -90, 90); sy = y; vh = innerHeight;
    vy += (d - vy) * 0.3; if (Math.abs(vy) < 0.05) vy = 0;
    ptr.nx += (ptr.tx - ptr.nx) * 0.06; ptr.ny += (ptr.ty - ptr.ny) * 0.06;
    var t = now / 1000;
    for (var i = 0; i < fields.length; i++) if (fields[i].live) fields[i].draw(t, dt, false);
    raf = requestAnimationFrame(tick);
  }
  function start() {
    if (flat || raf || document.hidden || !anyLive()) return;
    last = performance.now(); sy = scrollY; vy = 0;
    raf = requestAnimationFrame(tick);
  }

  var io = null;
  function observe(f) {
    if (!window.IntersectionObserver) { f.live = true; return; }
    if (!io) io = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        for (var i = 0; i < fields.length; i++) if (fields[i].host === e.target) {
          fields[i].live = e.isIntersecting;
          if (!e.isIntersecting) { fields[i].motes.length = 0; fields[i].meteors.length = 0; }
        }
      });
      start();
    }, { rootMargin: '120px 0px' });
    io.observe(f.host);
  }

  var ro = null, roPending = [], roRaf = 0;
  function watch(f) {
    if (!window.ResizeObserver) return;
    if (!ro) ro = new ResizeObserver(function (es) {
      es.forEach(function (e) { for (var i = 0; i < fields.length; i++) if (fields[i].host === e.target && roPending.indexOf(fields[i]) < 0) roPending.push(fields[i]); });
      if (!roRaf) roRaf = requestAnimationFrame(function () { roRaf = 0; var p = roPending; roPending = []; p.forEach(function (x) { x.layout(); }); start(); });
    });
    ro.observe(f.host);
  }

  function mount(host, opts) {
    if (!host) return null;
    for (var i = 0; i < fields.length; i++) if (fields[i].host === host) return fields[i];
    var f = new Field(host, opts || {});
    fields.push(f);
    observe(f); watch(f);
    start();
    return f;
  }

  /* a page's own geometry pass tells us the hosts may have moved (fonts, a form swapping for its thanks, an exhibit pinning) */
  function place() {
    for (var i = 0; i < fields.length; i++) {
      var f = fields[i], B = f.box();
      if (Math.abs(B.w - f.w) > 0.5 || Math.abs(B.h - f.h) > 0.5 || B.b.join() !== f.bl.join() || dprFor(B.w * B.h) !== f.dpr) f.layout();
      else f.anchor(B);
    }
    start();
  }

  function stats() {
    return fields.map(function (f) {
      return { host: f.host.id || f.host.className, live: f.live, w: Math.round(f.w), h: Math.round(f.h), dpr: f.dpr, stars: f.stars.length, motes: f.motes.length,
        emitters: f.emit.length, skyline: f.layers.length, sticky: !!f.stick, frames: f.frames, flat: flat };
    });
  }

  if (finePointer && !flat) {
    addEventListener('pointermove', function (e) {
      if (e.pointerType && e.pointerType !== 'mouse' && e.pointerType !== 'pen') return;
      ptr.cx = e.clientX; ptr.cy = e.clientY;
      ptr.tx = clamp(e.clientX / Math.max(1, innerWidth) * 2 - 1, -1, 1); ptr.ty = clamp(e.clientY / Math.max(1, innerHeight) * 2 - 1, -1, 1);
    }, { passive: true });
    /* the pointer left the window: mouseout with no related target (pointerleave on document does not fire reliably) */
    addEventListener('mouseout', function (e) { if (!e.relatedTarget) { ptr.cx = ptr.cy = -1e4; ptr.tx = ptr.ty = 0; } });
  }
  document.addEventListener('visibilitychange', function () { if (!document.hidden) start(); });
  /* a viewport resize can change a bleed, or the devicePixelRatio (a window dragged to another screen), without resizing a host */
  var rz = 0;
  addEventListener('resize', function () {
    vh = innerHeight;
    if (!rz) rz = requestAnimationFrame(function () { rz = 0; place(); });
  });

  /* static pages: <div data-sky="meteors motes skyline" data-sky-seed="7" data-sky-density="900"> */
  function auto() {
    [].forEach.call(document.querySelectorAll('[data-sky]'), function (el) {
      var on = ' ' + (el.getAttribute('data-sky') || '') + ' ', num = function (k, d) { var v = parseFloat(el.getAttribute('data-sky-' + k)); return isNaN(v) ? d : v; };
      mount(el, { seed: num('seed', 1), density: num('density', 1100), meteors: on.indexOf(' meteors ') >= 0 ? num('meteors', 3) : 0,
        motes: on.indexOf(' motes ') >= 0 ? num('motes', 3) : 0, skyline: on.indexOf(' skyline ') >= 0 ? num('skyline', 2) : 0 });
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', auto); else auto();

  window.G33Sky = { mount: mount, place: place, stats: stats, flat: flat };
})();
