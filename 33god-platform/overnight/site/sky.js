/* sky.js: a living night sky for any 33GOD stage. Plain JS, no libraries, no raw colours (every colour is a token, read
   from the host at layout time, so a [data-theme] block re-colours it).

   One field is one <canvas> laid behind a host element's own drawing (the host becomes an isolated stacking context and
   the canvas sits at z-index -1, so the host's SVG skyline is always in front of it). A field draws, back to front:
     stars     three depth layers; each drifts against the scroll at its own rate (parallax), twinkles, leans toward the
               pointer on a fine pointer, and streaks briefly when the page is flicked
     meteors   an occasional shooting star (opts.meteors per minute)
     skyline   opts.skyline layers of distant city standing on the horizon, sinking behind it at their own parallax rate,
               with a horizon glow and a few windows that switch on and off
     motes     sparks that leave the host's lit windows (any element marked data-sky-emit, in its own fill colour) and rise
               into the sky; the pointer pushes them aside and a scroll leaves them a little behind

   Markup the field reads (all optional):
     [data-sky-horizon]   an element whose top edge is the ground: stars live above it, the skyline stands on it
                          (default: opts.band of the host's height)
     [data-sky-emit="w"]  a lit window that releases motes, weight w (default 1), in its computed fill colour

   API:
     G33Sky.mount(host, opts) -> field     opts: seed, density (px² per star; lower is denser), max (star cap), band,
                                           meteors (per minute), motes (per second), skyline (0..2), pointer (bool),
                                           bleed [t, r, b, l] px the canvas reaches past the host, fade [t, r, b, l] px
                                           the sky dissolves over at each canvas edge (either may be a function
                                           (host, rect) -> array, re-read at every layout)
     G33Sky.place()                        re-read where each host sits on the page (call from a page's own geometry pass)
     G33Sky.stats()                        what each field is doing (tests)
     <div data-sky="meteors motes skyline" data-sky-seed="7">  mounts itself on DOMContentLoaded (static pages)

   Discipline (the same as front.js): geometry is read once per layout change (mount, a ResizeObserver on the host,
   place()), never per frame; a frame is arithmetic on scrollY plus canvas calls. Only fields on screen animate, nothing
   runs in a hidden tab, and prefers-reduced-motion draws one still frame per layout and never animates. */
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
  var LAYER_DEPTH = [0.25, 0.55, 1];
  var SKY_K = [0.34, 0.2];

  function rng(seed) { seed = (Math.abs(seed | 0) % 2147483646) + 1; return function () { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; }; }
  function clamp(x, a, b) { return Math.max(a, Math.min(b, x)); }
  function mod(a, n) { return ((a % n) + n) % n; }

  /* A token's colour as [r, g, b], resolved inside the host so a themed host gets its own values. */
  function tokenRGB(host, name) {
    var p = document.createElement('span');
    p.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden;visibility:hidden;color:var(' + name + ')';
    host.appendChild(p);
    var c = getComputedStyle(p).color;
    host.removeChild(p);
    return parseRGB(c);
  }
  function parseRGB(c) {
    var m = /rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)(?:[\s,/]+([\d.]+%?))?/.exec(c || '');
    if (!m) return null;
    if (m[4] !== undefined && parseFloat(m[4]) === 0) return null;
    return [Math.round(+m[1]), Math.round(+m[2]), Math.round(+m[3])];
  }
  function rgba(p, a) { return 'rgba(' + p[0] + ',' + p[1] + ',' + p[2] + ',' + a + ')'; }

  /* One soft glow sprite per colour, drawn once and stamped with drawImage (a gradient per particle per frame is not cheap). */
  var sprites = {};
  function sprite(p) {
    var key = p.join(',');
    if (sprites[key]) return sprites[key];
    var c = document.createElement('canvas'); c.width = c.height = 32;
    var g = c.getContext('2d'), gr = g.createRadialGradient(16, 16, 0, 16, 16, 16);
    gr.addColorStop(0, rgba(p, 1)); gr.addColorStop(0.18, rgba(p, 0.85)); gr.addColorStop(0.45, rgba(p, 0.22)); gr.addColorStop(1, rgba(p, 0));
    g.fillStyle = gr; g.fillRect(0, 0, 32, 32);
    return (sprites[key] = c);
  }

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
    this.frames = 0; this.w = 0; this.h = 0;
    this.stars = []; this.motes = []; this.meteors = []; this.emit = []; this.layers = []; this.fades = [];
    this.nextMeteor = 0; this.emitAcc = 0; this.flickAcc = 0;
    if (getComputedStyle(host).position === 'static') host.style.position = 'relative';
    host.style.isolation = 'isolate';
    var cv = this.cv = document.createElement('canvas');
    cv.className = 'g33-sky';
    cv.setAttribute('aria-hidden', 'true');
    cv.style.cssText = 'position:absolute;left:0;top:0;width:100%;height:100%;display:block;pointer-events:none;z-index:-1';
    this.bl = [0, 0, 0, 0];
    host.insertBefore(cv, host.firstChild);
    this.ctx = cv.getContext('2d');
    this.layout();
  }

  function edges(v, host, r) {
    if (typeof v === 'function') v = v(host, r);
    if (!v) return [0, 0, 0, 0];
    return [0, 1, 2, 3].map(function (i) { return Math.max(0, Math.round(+v[i] || 0)); });
  }

  /* The canvas box: the host's box grown by the bleed. Everything a field draws is in this box's coordinates. */
  Field.prototype.box = function () {
    var r = this.host.getBoundingClientRect(), b = edges(this.o.bleed, this.host, r);
    return { r: r, b: b, w: r.width + b[1] + b[3], h: r.height + b[0] + b[2], left: r.left + scrollX - b[3], top: r.top + scrollY - b[0] };
  };

  Field.prototype.layout = function () {
    var host = this.host, B = this.box(), r = B.r, bl = B.b;
    var w = B.w, h = B.h, ox = bl[3], oy = bl[0];
    this.left = B.left; this.top = B.top;
    if (r.width < 2 || r.height < 2) { this.w = 0; return; }
    var sizeChanged = Math.abs(w - this.w) > 0.5 || Math.abs(h - this.h) > 0.5;
    this.w = w; this.h = h;
    if (bl.join() !== this.bl.join()) {
      this.bl = bl;
      var cs = this.cv.style;
      cs.left = -bl[3] + 'px'; cs.top = -bl[0] + 'px';
      cs.width = 'calc(100% + ' + (bl[1] + bl[3]) + 'px)'; cs.height = 'calc(100% + ' + (bl[0] + bl[2]) + 'px)';
    }
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var cw = Math.round(w * dpr), ch = Math.round(h * dpr);
    if (this.cv.width !== cw || this.cv.height !== ch) { this.cv.width = cw; this.cv.height = ch; }
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.dpr = dpr;

    var hz = host.querySelector('[data-sky-horizon]');
    this.hz = hz ? clamp(hz.getBoundingClientRect().top - r.top + oy, 8, h) : oy + r.height * this.o.band;

    /* tokens only: a page without --window-lit gets no sky, never a guessed colour */
    var lit = tokenRGB(host, '--window-lit');
    if (!lit) { this.w = 0; this.ctx.clearRect(0, 0, this.cv.width, this.cv.height); return; }
    this.col = {
      lit: lit,
      cool: tokenRGB(host, '--window-working') || lit,
      warm: tokenRGB(host, '--window-you') || lit,
      far: tokenRGB(host, '--facade-edge') || tokenRGB(host, '--stage-rule'),
      near: tokenRGB(host, '--facade'),
      rule: tokenRGB(host, '--stage-rule') || tokenRGB(host, '--facade-edge')
    };

    /* emitters: where they sit inside the host now (they move with it, so this holds until the next layout) */
    var em = [], tw = 0;
    [].forEach.call(host.querySelectorAll('[data-sky-emit]'), function (el) {
      var b = el.getBoundingClientRect();
      if (b.width < 0.5 || b.height < 0.5) return;
      var c = parseRGB(getComputedStyle(el).fill) || parseRGB(getComputedStyle(el).color);
      if (!c) return;
      var wt = parseFloat(el.getAttribute('data-sky-emit')); if (!(wt > 0)) wt = 1;
      em.push({ x: b.left - r.left + ox, y: b.top - r.top + oy, w: b.width, h: b.height, c: c, wt: wt });
      tw += wt;
    });
    this.emit = em; this.emitW = tw;

    if (sizeChanged || !this.stars.length) { this.seedStars(); this.seedSkyline(); }
    this.seedFade();
    this.motes = this.motes.filter(function (m) { return m.x < w && m.y < h; });
    if (flat || !this.live) this.draw(0, 0, true);
  };

  Field.prototype.seedStars = function () {
    var r = rng(this.o.seed * 977 + 13), w = this.w, hz = this.hz, col = this.col;
    var n = Math.round(clamp((w * hz) / this.o.density, 6, this.o.max));
    var st = [];
    for (var i = 0; i < n; i++) {
      var q = r(), l = q < 0.56 ? 0 : q < 0.86 ? 1 : 2, pick = r();
      st.push({
        x: r() * w, y: Math.pow(r(), 1.35) * (hz + 8), l: l,
        s: l === 0 ? 0.55 + r() * 0.45 : l === 1 ? 0.85 + r() * 0.5 : 1.2 + r() * 0.7,
        a: l === 0 ? 0.25 + r() * 0.35 : l === 1 ? 0.4 + r() * 0.4 : 0.6 + r() * 0.4,
        tw: 0.6 + r() * 2.4, ph: r() * 6.283,
        c: pick < 0.8 ? col.lit : pick < 0.94 ? col.cool : col.warm,
        g: l === 2 && r() < 0.5
      });
    }
    /* drawn grouped by colour, so the canvas changes fillStyle a few times a frame, not hundreds */
    st.sort(function (a, b) { return a.c === b.c ? 0 : a.c === col.lit ? -1 : b.c === col.lit ? 1 : a.c === col.cool ? -1 : 1; });
    this.stars = st;
  };

  Field.prototype.seedSkyline = function () {
    this.layers = [];
    if (!this.o.skyline || !this.col.far || !this.col.near) return;
    var hz = this.hz, w = this.w, col = this.col;
    for (var L = 0; L < this.o.skyline; L++) {
      var r = rng(this.o.seed * 131 + L * 71 + 5), far = L === 0, bl = [], x = -12 - r() * 20;
      var maxH = Math.min(far ? 96 : 62, hz * (far ? 0.34 : 0.22)), minH = maxH * 0.18;
      while (x < w + 12) {
        var bw = far ? 9 + r() * 26 : 14 + r() * 34, bh = minH + Math.pow(r(), 1.6) * (maxH - minH), wins = [];
        var cols = Math.max(1, Math.floor((bw - 4) / 5)), rows = Math.max(1, Math.floor((bh - 5) / 6));
        for (var k = 0; k < Math.min(18, cols * rows); k++) if (r() < (far ? 0.12 : 0.2)) {
          var pick = r();
          wins.push({ dx: 2.5 + (k % cols) * 5, dy: 4 + Math.floor(k / cols) * 6, on: r() < 0.7, c: pick < 0.6 ? col.cool : pick < 0.85 ? col.lit : col.warm });
        }
        var spire = !far && bh > maxH * 0.7 && r() < 0.35;
        bl.push({ x: x, w: bw, h: bh, wins: wins, spire: spire });
        x += bw + (far ? r() * 3 : 1 + r() * 7);
      }
      this.layers.push({ b: bl, c: far ? col.far : col.near, a: far ? 0.55 : 0.92, k: SKY_K[L], depth: far ? 0.3 : 0.6 });
    }
    var ctx = this.ctx, g = ctx.createLinearGradient(0, hz - Math.min(90, hz * 0.6), 0, hz);
    g.addColorStop(0, rgba(col.warm, 0)); g.addColorStop(1, rgba(col.warm, 0.11));
    this.glow = g;
  };

  /* the edge fades: one gradient per faded edge, erased out of the finished frame */
  Field.prototype.seedFade = function () {
    var f = edges(this.o.fade, this.host, this.host.getBoundingClientRect()), w = this.w, h = this.h, ctx = this.ctx, c = this.col.lit, out = [];
    function g(x0, y0, x1, y1, rx, ry, rw, rh) {
      var gr = ctx.createLinearGradient(x0, y0, x1, y1); gr.addColorStop(0, rgba(c, 1)); gr.addColorStop(1, rgba(c, 0));
      out.push({ g: gr, x: rx, y: ry, w: rw, h: rh });
    }
    if (f[0]) g(0, 0, 0, f[0], 0, 0, w, f[0]);
    if (f[1]) g(w, 0, w - f[1], 0, w - f[1], 0, f[1], h);
    if (f[2]) g(0, h, 0, h - f[2], 0, h - f[2], w, f[2]);
    if (f[3]) g(0, 0, f[3], 0, 0, 0, f[3], h);
    this.fades = out;
  };

  /* ---------- one frame ---------- */
  Field.prototype.draw = function (t, dt, still) {
    var w = this.w, h = this.h, hz = this.hz;
    if (!w) return;
    var ctx = this.ctx, o = this.o, col = this.col;
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
    ctx.clearRect(0, 0, w, h);
    var vhNow = vh || innerHeight;
    /* rel: how far the host's middle is past the viewport's middle; 0 when it is centred. A still frame has no parallax. */
    var rel = still ? 0 : (sy + vhNow / 2) - (this.top + h / 2);
    var px = o.pointer ? ptr.nx : 0, py = o.pointer ? ptr.ny : 0;
    var streakV = still ? 0 : vy;
    var span = hz + 8;

    /* stars */
    var cur = null, sp, i, s;
    for (i = 0; i < this.stars.length; i++) {
      s = this.stars[i];
      var k = LAYER_K[s.l], d = LAYER_DEPTH[s.l];
      var y = mod(s.y + rel * k + py * d * 5, span) - 4, x = s.x + px * d * 9;
      if (y > hz) continue;
      var a = s.a * (still ? 0.85 : 0.62 + 0.38 * Math.sin(t * s.tw + s.ph));
      if (y > hz - 14) a *= (hz - y) / 14;
      if (a <= 0.01) continue;
      if (s.g) {
        sp = sprite(s.c); ctx.globalAlpha = a * 0.45;
        var gs = s.s * 7; ctx.drawImage(sp, x - gs / 2, y - gs / 2, gs, gs);
      }
      if (cur !== s.c) { cur = s.c; ctx.fillStyle = rgba(s.c, 1); }
      ctx.globalAlpha = a;
      var L = Math.min(26, Math.abs(streakV) * (1 - k) * 0.9);
      if (L > 1) ctx.fillRect(x - s.s / 2, streakV > 0 ? y - s.s / 2 : y - s.s / 2 - L, s.s, s.s + L);
      else ctx.fillRect(x - s.s / 2, y - s.s / 2, s.s, s.s);
    }

    /* meteors, behind the skyline */
    if (o.meteors && !still) {
      if (!this.nextMeteor) this.nextMeteor = t + (60 / o.meteors) * (0.3 + Math.random() * 0.7);
      if (t >= this.nextMeteor) {
        this.nextMeteor = t + (60 / o.meteors) * (0.5 + Math.random());
        var dir = Math.random() < 0.5 ? -1 : 1, ang = (16 + Math.random() * 26) * Math.PI / 180, sc = clamp(w / 700, 0.45, 1.4);
        this.meteors.push({ x: w * (0.15 + Math.random() * 0.7), y: hz * Math.random() * 0.45, dx: Math.cos(ang) * dir, dy: Math.sin(ang),
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
          ctx.globalAlpha = 1; ctx.strokeStyle = gr; ctx.lineWidth = 1.4;
          ctx.beginPath(); ctx.moveTo(hx, hy); ctx.lineTo(hx - m.dx * tl, hy - m.dy * tl); ctx.stroke();
          ctx.globalAlpha = ma; ctx.drawImage(sprite(col.lit), hx - 5, hy - 5, 10, 10);
        }
        ctx.restore();
      }
    }

    /* the distant city on the horizon */
    if (this.layers.length) {
      ctx.globalAlpha = 1; ctx.fillStyle = this.glow; ctx.fillRect(0, 0, w, hz);
      ctx.save(); ctx.beginPath(); ctx.rect(0, 0, w, hz); ctx.clip();
      if (!still && o.skyline) {
        this.flickAcc += dt * 0.9;
        while (this.flickAcc > 1) {
          this.flickAcc -= 1;
          var lay = this.layers[(Math.random() * this.layers.length) | 0], bb = lay.b[(Math.random() * lay.b.length) | 0];
          if (bb && bb.wins.length) { var wi = bb.wins[(Math.random() * bb.wins.length) | 0]; wi.on = !wi.on; }
        }
      }
      for (var li = 0; li < this.layers.length; li++) {
        var ly = this.layers[li], off = clamp(rel * ly.k, -h * 0.3, h * 0.6) + py * ly.depth * 3, ox = px * ly.depth * 5;
        ctx.globalAlpha = ly.a; ctx.fillStyle = rgba(ly.c, 1);
        for (var bi = 0; bi < ly.b.length; bi++) {
          var b = ly.b[bi], top = hz - b.h + off;
          ctx.fillRect(b.x + ox, top, b.w, b.h + h);
          if (b.spire) ctx.fillRect(b.x + ox + b.w / 2 - 0.75, top - 7, 1.5, 7);
        }
        var wc = null;
        for (bi = 0; bi < ly.b.length; bi++) {
          b = ly.b[bi]; top = hz - b.h + off;
          for (var wj = 0; wj < b.wins.length; wj++) {
            var wn = b.wins[wj]; if (!wn.on) continue;
            var wy = top + wn.dy; if (wy > hz - 2 || wn.dx > b.w - 2) continue;
            if (wc !== wn.c) { wc = wn.c; ctx.fillStyle = rgba(wn.c, 1); }
            ctx.globalAlpha = li === 0 ? 0.35 : 0.6;
            ctx.fillRect(b.x + ox + wn.dx, wy, 1.6, 1.6);
          }
        }
      }
      ctx.restore();
      if (col.rule) { ctx.globalAlpha = 0.9; ctx.fillStyle = rgba(col.rule, 1); ctx.fillRect(0, hz - 1, w, 1.5); }
    }

    /* motes: sparks leaving the lit windows */
    if (o.motes && !still) {
      if (this.emit.length && this.live) {
        this.emitAcc += dt * o.motes;
        while (this.emitAcc >= 1 && this.motes.length < 160) {
          this.emitAcc -= 1;
          var pickW = Math.random() * this.emitW, e = this.emit[0];
          for (var ei = 0; ei < this.emit.length; ei++) { pickW -= this.emit[ei].wt; if (pickW <= 0) { e = this.emit[ei]; break; } }
          this.motes.push({ x: e.x + Math.random() * e.w, y: e.y + Math.random() * e.h * 0.6, vx: (Math.random() - 0.5) * 6, vy: -(9 + Math.random() * 18),
            life: 0, max: 2.6 + Math.random() * 3.2, r: 0.9 + Math.random() * 1.4, c: e.c, ph: Math.random() * 6.283, sw: 3 + Math.random() * 6 });
        }
        if (this.emitAcc > 1) this.emitAcc = 1;
      }
      if (this.motes.length) {
        var lx = ptr.cx - (this.left - scrollX), lyp = ptr.cy - (this.top - sy), near = o.pointer && lx > -60 && lx < w + 60 && lyp > -60 && lyp < h + 60;
        ctx.globalCompositeOperation = 'lighter';
        for (i = this.motes.length - 1; i >= 0; i--) {
          var mo = this.motes[i]; mo.life += dt;
          if (mo.life >= mo.max) { this.motes.splice(i, 1); continue; }
          mo.x += (mo.vx + Math.cos(mo.life * 1.7 + mo.ph) * mo.sw) * dt;
          mo.y += mo.vy * dt + vy * 0.12;
          if (near) {
            var ddx = mo.x - lx, ddy = mo.y - lyp, d2 = ddx * ddx + ddy * ddy;
            if (d2 < 4900 && d2 > 0.01) { var f = (1 - d2 / 4900) * 90 * dt / Math.sqrt(d2); mo.x += ddx * f; mo.y += ddy * f; }
          }
          if (mo.y < -8 || mo.y > h + 8) { this.motes.splice(i, 1); continue; }
          var q = mo.life / mo.max, ma2 = Math.min(1, mo.life / 0.45) * (q > 0.55 ? (1 - q) / 0.45 : 1);
          var flick = 0.75 + 0.25 * Math.sin(mo.life * 9 + mo.ph);
          ctx.globalAlpha = ma2 * flick * 0.9;
          var ms = mo.r * 8; ctx.drawImage(sprite(mo.c), mo.x - ms / 2, mo.y - ms / 2, ms, ms);
        }
        ctx.globalCompositeOperation = 'source-over';
      }
    }
    if (this.fades.length) {
      ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'destination-out';
      for (i = 0; i < this.fades.length; i++) { var fd = this.fades[i]; ctx.fillStyle = fd.g; ctx.fillRect(fd.x, fd.y, fd.w, fd.h); }
      ctx.globalCompositeOperation = 'source-over';
    }
    ctx.globalAlpha = 1;
    this.frames++;
  };

  /* ---------- the loop ---------- */
  function anyLive() { for (var i = 0; i < fields.length; i++) if (fields[i].live && fields[i].w) return true; return false; }
  function tick(now) {
    raf = 0;
    if (document.hidden || !anyLive()) return;
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
        for (var i = 0; i < fields.length; i++) if (fields[i].host === e.target) fields[i].live = e.isIntersecting;
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

  /* a page's own geometry pass tells us the hosts may have moved (fonts, a form swapping for its thanks) */
  function place() {
    for (var i = 0; i < fields.length; i++) {
      var f = fields[i], B = f.box();
      if (Math.abs(B.w - f.w) > 0.5 || Math.abs(B.h - f.h) > 0.5 || B.b.join() !== f.bl.join()) f.layout();
      else { f.left = B.left; f.top = B.top; }
    }
    start();
  }

  function stats() {
    return fields.map(function (f) {
      return { host: f.host.id || f.host.className, live: f.live, w: Math.round(f.w), h: Math.round(f.h), stars: f.stars.length, motes: f.motes.length,
        emitters: f.emit.length, skyline: f.layers.length, frames: f.frames, flat: flat };
    });
  }

  if (finePointer && !flat) {
    addEventListener('pointermove', function (e) {
      if (e.pointerType && e.pointerType !== 'mouse' && e.pointerType !== 'pen') return;
      ptr.cx = e.clientX; ptr.cy = e.clientY;
      ptr.tx = clamp(e.clientX / Math.max(1, innerWidth) * 2 - 1, -1, 1); ptr.ty = clamp(e.clientY / Math.max(1, innerHeight) * 2 - 1, -1, 1);
    }, { passive: true });
    document.addEventListener('pointerleave', function () { ptr.cx = ptr.cy = -1e4; ptr.tx = ptr.ty = 0; });
  }
  document.addEventListener('visibilitychange', function () { if (!document.hidden) start(); });
  /* a viewport resize can change a bleed without resizing its host */
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
