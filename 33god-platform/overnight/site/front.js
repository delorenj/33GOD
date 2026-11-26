/* The 33GOD front page: five flagships, one band of org-chart icons, the counts, the ask.
   Plain JS, no libraries. Every word comes from manifest.json (the "front" record; the org band reads the tour's
   org-chart beat). The tour lives on in tour.html and keeps its own scripts.

   Layout, in one rule: an exhibit pins ONLY when its whole stage fits the small viewport (100svh minus the header),
   measured here in JS, at this width, with these fonts. Otherwise it flows as a normal section. Either way the
   exhibit's three beats advance off scroll position (data-step), so a phone, a short laptop and a tall tablet
   all get the same story and nothing is ever clipped. Reduced motion shows every final state and never pins. */
(function () {
  'use strict';
  var NS = 'http://www.w3.org/2000/svg';
  var root = document.documentElement;
  var flat = false;
  try { flat = matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) { flat = false; }
  if (flat) root.classList.add('flat');

  /* ---------- small helpers ---------- */
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function clamp(x, a, b) { return Math.max(a === undefined ? 0 : a, Math.min(b === undefined ? 1 : b, x)); }
  function rng(seed) { return function () { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; }; }
  function pick(o, path) { return path.split('.').reduce(function (a, k) { return a == null ? a : a[k]; }, o); }
  var M, F, TOTAL = 0;
  /* {site.x}, {total} and {name} are filled in; nothing else is a token. */
  function t(s, extra) {
    return String(s).replace(/\{([^}]+)\}/g, function (m, k) {
      if (k === 'total') return String(TOTAL);
      if (extra && extra[k] != null) return extra[k];
      if (k.indexOf('site.') === 0) { var v = pick(M, k); return v == null ? m : v; }
      return m;
    });
  }
  function ic(id, cls) { return '<svg class="i' + (cls ? ' ' + cls : '') + '" aria-hidden="true"><use href="#i-' + esc(id) + '"/></svg>'; }
  function svgEl(name, attrs, parent) {
    var n = document.createElementNS(NS, name);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }
  function fail(msg) {
    var host = document.getElementById('front');
    host.innerHTML = '<div class="fail" role="alert"><h1>This page could not load its words.</h1><p>' + esc(msg) + '</p></div>';
  }

  /* ---------- markup ---------- */
  function header() {
    var s = M.site;
    var nav = F.flagships.map(function (f) {
      return '<a class="f-' + f.id + '" href="#f-' + f.id + '" title="' + esc(f.num + ' ' + f.name) + '" aria-label="' + esc(f.name) + '">' +
        ic(f.icon) + '<span class="l">' + esc(f.name) + '</span><span class="s">' + esc(f.short) + '</span></a>';
    }).join('');
    var bars = F.flagships.map(function (f) { return '<i class="f-' + f.id + '"></i>'; }).join('');
    return '<header class="hdr" id="hdr"><div class="hdr__in">' +
      '<a class="brand" href="#top" aria-label="' + esc(F.aria.home) + '"><svg aria-hidden="true"><use href="#mark"/></svg><b>' + esc(s.name) + '</b></a>' +
      '<nav class="nav" id="nav" aria-label="' + esc(F.aria.flagships) + '">' + nav + '</nav>' +
      '<a class="cta" href="#briefing" aria-label="' + esc(s.cta) + '">' + ic('mail') + '<span class="cta__s">' + esc(F.ctaShort) + '</span><span class="cta__l">' + esc(s.cta) + '</span></a>' +
      '</div><div class="prog" role="presentation">' + bars + '</div></header>';
  }

  function hero() {
    var h = F.hero;
    var tiles = F.flagships.map(function (f) {
      return '<li class="tile f-' + f.id + '"><a href="#f-' + f.id + '"><span class="tile__top">' + ic(f.icon) + '<span class="tile__n">' + esc(f.num) + '</span></span>' +
        '<span class="tile__name">' + esc(f.name) + '</span><span class="tile__tag">' + esc(f.tag) + '</span></a></li>';
    }).join('');
    var stats = F.stats.filter(function (x) { return x.hero; }).map(function (x) {
      return '<div class="fact"><span class="fact__ic">' + ic(x.icon) + '</span><b class="fact__n">' + esc(x.n) + '</b><span class="fact__l">' + esc(x.short) + '</span></div>';
    }).join('');
    return '<section class="hero" id="top"><div class="hero__in">' +
      '<div class="hero__copy"><p class="kicker">' + esc(h.kicker) + '</p>' +
      '<h1>' + esc(h.title) + '<br> <em>' + esc(h.titleTurn) + '</em></h1>' +
      '<p class="lede">' + esc(h.line) + '</p>' +
      '<div class="hero__cta"><a class="btn" href="#f-' + F.flagships[0].id + '">' + esc(h.primary) + ' ' + ic('down') + '</a>' +
      '<a class="textlink" href="tour.html" title="' + esc(t(h.tourNote)) + '">' + esc(t(h.tour)) + ' ' + ic('right') + '</a></div></div>' +
      '<figure class="hero__art" aria-hidden="true"><svg id="hero-bldg" viewBox="0 0 360 300"></svg></figure>' +
      '<div class="hero__idx" id="flagships"><ol class="tiles" aria-label="' + esc(F.aria.flagships) + '">' + tiles + '</ol>' +
      '<div class="facts" role="group" aria-label="' + esc(F.aria.counts) + '">' + stats + '</div>' +
      '<p class="note">' + esc(h.statsStamp) + '</p></div>' +
      '</div></section>';
  }

  function chips(f) {
    return '<ul class="chips">' + f.chips.map(function (c) { return '<li class="chip"><span class="ic">' + ic(c.icon) + '</span><span>' + esc(c.text) + '</span></li>'; }).join('') + '</ul>';
  }
  function pill() { return '<span class="pill">' + esc(F.stagedLabel) + '</span>'; }

  function pieceHtml(f) {
    var p = f.piece;
    if (f.id === 'pjangler') {
      return '<div class="panel pj" role="img" aria-label="' + esc(p.aria) + '">' +
        '<div class="pj__sky"><svg class="pj__bldg" id="pj-art" viewBox="0 0 260 340" aria-hidden="true"></svg>' +
        '<p class="pj__cap"><span class="tag">' + esc(p.floor) + '</span>' + esc(p.floorNote) + '</p></div>' +
        '<div class="check"><div class="check__h"><h3>' + esc(p.title) + '</h3>' + pill() + '</div><small>' + esc(p.note) + '</small>' +
        '<ol>' + p.steps.map(function (s) { return '<li><span class="ic">' + ic(s.icon) + '</span><span class="tx">' + esc(s.text) + '</span>' + ic('check', 'tick') + '</li>'; }).join('') + '</ol></div></div>';
    }
    if (f.id === 'gateway') {
      var pools = p.pools.map(function (k, i) {
        return '<li class="pool' + (i === 4 ? ' pool--new' : '') + '" data-pool="' + (i + 1) + '"><span class="pool__n">0' + (i + 1) + '</span><span class="pool__kind">' + esc(k) +
          '</span><span class="pool__state"></span><span class="meter"><i></i></span></li>';
      }).join('');
      var wires = [50, 150, 250, 350, 450].map(function (y, i) { return '<path data-w="' + (i + 1) + '" d="M0 250C55 250 45 ' + y + ' 100 ' + y + '"/>'; }).join('');
      var chain = p.chain.map(function (c) { return '<span>' + esc(c) + '</span>'; }).join(ic('right'));
      var say = p.say.map(function (s, i) { return '<p data-at="' + i + '"><b>' + esc(s.route) + '</b>' + esc(s.line) + '</p>'; }).join('');
      var stats = p.stats.map(function (s) { return '<div><dt>' + esc(s.n) + '</dt><dd>' + esc(s.label) + '</dd></div>'; }).join('');
      return '<div class="panel gw" role="img" aria-label="' + esc(p.aria) + '">' +
        '<div class="panel__bar"><span>' + esc(p.bar) + '</span>' + pill() + '</div>' +
        '<div class="gw__flow"><div class="gw__ask">' + ic('user') + '<small>' + esc(p.ask.label) + '</small><b>' + esc(p.ask.value) + '</b></div>' +
        '<div class="gw__wirecell"><svg class="gw__wires" viewBox="0 0 100 500" preserveAspectRatio="none" aria-hidden="true">' + wires + '</svg></div>' +
        '<ol class="pools">' + pools + '</ol></div>' +
        '<div class="chain">' + chain + '<em>' + esc(p.chainNote) + '</em></div>' +
        '<div class="gw__say swap">' + say + '</div>' +
        '<dl class="stats">' + stats + '</dl><p class="stamp">' + esc(p.stamp) + '</p></div>';
    }
    if (f.id === 'heyma') {
      var parts = p.parts.map(function (x) {
        return '<li class="part" data-p="' + esc(x.id) + '"><svg class="i" aria-hidden="true"><use href="#p-' + esc(x.icon) + '"/></svg><b>' + esc(x.name) + '</b><span>' + esc(x.line) + '</span></li>';
      }).join('');
      var c = p.call;
      return '<div class="panel hm"><div class="hm__parts"><ul class="parts">' + parts + '</ul><p class="hm__note">' + esc(p.note) + '</p></div>' +
        '<figure class="phone"><div class="phone__body"><div class="phone__top"><span class="island"></span></div>' +
        '<div class="call__head">' + ic('phone') + '<span>' + esc(c.label) + '</span>' + pill() + '</div>' +
        '<div class="wave" id="hm-wave" aria-hidden="true"></div>' +
        '<div class="line line--pt"><small>' + esc(c.heardLabel) + '</small><p lang="pt">' + esc(c.heard) + '</p></div>' +
        '<div class="line line--en"><small>' + esc(c.translatedLabel) + '</small><p>' + esc(c.translated) + '</p></div>' +
        '<div class="line line--you"><small>' + esc(c.replyLabel) + '</small><p>' + esc(c.reply) + '</p></div>' +
        '</div></figure><p class="stamp">' + esc(p.stamp) + '</p></div>';
    }
    if (f.id === 'flume') {
      var r = p.roles;
      function role(x, cls) { return '<div class="role' + (cls ? ' ' + cls : '') + '">' + ic(x.icon) + '<b>' + esc(x.name) + '</b><span>' + esc(x.line) + '</span></div>'; }
      var pipe = p.pipeline.map(function (x) { return '<li>' + ic(x.icon) + esc(x.text) + '</li>'; }).join('');
      return '<div class="panel fl"><div class="org"><div class="org__lvl">' + role(r[0]) + '</div>' +
        '<svg class="tree" viewBox="0 0 100 20" preserveAspectRatio="none" aria-hidden="true"><path d="M50 0v10M16.5 10h67M16.5 10v10M50 10v10M83.5 10v10"/></svg>' +
        role(r[1]) + role(r[2]) + role(p.hire, 'role--open') + '</div>' +
        '<div class="fl__bar">' + pill() + '</div><ol class="pipe">' + pipe + '</ol><p class="stamp">' + esc(p.stamp) + '</p></div>';
    }
    if (f.id === 'holocene-auto') {
      var s = p.screen, film = demo(p.video);
      var li = p.standup.map(function (x, i) { return '<li' + (i === p.standup.length - 1 ? ' class="ahead"' : '') + '><small>0' + (i + 1) + '</small><span>' + esc(x) + '</span></li>'; }).join('');
      /* the real footage, when there is any, takes the drawn car screen's place (and the panel is no longer staged) */
      return '<div class="panel ha">' + (film || '<div class="car" role="img" aria-label="' + esc(p.aria) + '">' +
        '<svg class="car__wind" id="ha-wind" viewBox="0 0 600 220" preserveAspectRatio="xMidYMid slice" aria-hidden="true"></svg>' +
        '<div class="screen"><div class="screen__top"><svg class="mk" aria-hidden="true"><use href="#mark"/></svg><span>' + esc(s.product) + '</span><span class="on">' + ic('speaker') + esc(s.signal) + '</span></div>' +
        '<p class="screen__big">' + esc(s.line) + '</p>' +
        '<div class="screen__bot"><b>' + ic('check') + esc(s.count) + '</b><span>' + esc(s.sub) + '</span></div></div></div>') +
        '<div class="standup"><h3>' + ic('car') + esc(p.standupTitle) + (film ? '' : pill()) + '</h3><ol>' + li + '</ol></div>' +
        '<p class="stamp">' + esc(p.stamp) + '</p></div>';
    }
    return '';
  }

  /* A real demo video on a flagship (piece.video): data, not a section. Any flagship may carry one; Holocene Auto's
     replaces its drawn screen, anyone else's sits under its set piece. Only the one video host is ever drawn, so a typo
     or a download link never reaches the page. `crop` [x, y, w, h] (source pixels) shows only the part of the frame
     that holds the picture, for footage inside black bars; the poster is cropped the same way. It plays muted and
     looped while it is on screen, pauses off it, never starts by itself under reduced motion, and links to the full
     player for sound. */
  var VIDEO_HOST = 'https://v.delo.sh/';
  function onHost(u) { return typeof u === 'string' && u.indexOf(VIDEO_HOST) === 0 && u.length > VIDEO_HOST.length; }
  function demo(v) {
    if (!v || !onHost(v.src) || !onHost(v.poster) || !onHost(v.page) || !v.size || !(v.size[0] > 0 && v.size[1] > 0)) return '';
    var W = v.size[0], H = v.size[1], c = v.crop && v.crop[2] > 0 && v.crop[3] > 0 ? v.crop : [0, 0, W, H];
    var pct = function (x) { return (Math.round(x * 10000) / 100) + '%'; };
    var box = '--ar:' + c[2] + ' / ' + c[3] + ';--vw:' + pct(W / c[2]) + ';--vh:' + pct(H / c[3]) + ';--vx:' + pct(-c[0] / c[2]) + ';--vy:' + pct(-c[1] / c[3]);
    return '<figure class="demo"><div class="demo__frame" style="' + box + '">' +
      '<video muted loop playsinline preload="none" disablepictureinpicture poster="' + esc(v.poster) + '" aria-label="' + esc(v.label) + '">' +
      '<source src="' + esc(v.src) + '" type="video/mp4"></video>' +
      '<span class="demo__tag">' + esc(v.tag) + '</span>' +
      '<button class="demo__play" type="button" aria-label="' + esc(v.play) + '" data-play="' + esc(v.play) + '" data-pause="' + esc(v.pause) + '">' +
      ic('play', 'demo__on') + ic('pause', 'demo__off') + '</button></div>' +
      '<figcaption><a class="textlink demo__open" href="' + esc(v.page) + '" target="_blank" rel="noopener">' + ic('speaker') + esc(v.open) + ' ' + ic('right') + '</a></figcaption></figure>';
  }
  function demoAfter(f) { return f.id === 'holocene-auto' ? '' : demo(f.piece.video); }

  function exhibit(f, i) {
    var steps = '<span class="steps" aria-hidden="true"><i></i><i></i><i></i></span>';
    var next = '<a class="next" href="#' + esc(f.next.to) + '">' + esc(t(F.next, { name: f.next.label })) + ' ' + ic('down') + '</a>';
    var ticks = f.id === 'pjangler' ? ' data-ticks="' + f.piece.steps.length + '" data-tick-sel=".check li"' :
      f.id === 'flume' ? ' data-ticks="' + f.piece.pipeline.length + '" data-tick-sel=".pipe li"' :
        f.id === 'holocene-auto' ? ' data-ticks="' + (f.piece.standup.length - 1) + '" data-tick-sel=".standup li:not(.ahead)"' : '';
    var morning = f.id === 'holocene-auto';
    return '<section class="ex f-' + f.id + '" id="f-' + f.id + '" data-flag="' + f.id + '" data-steps="3"' + ticks + (morning ? ' data-theme="morning"' : '') + ' aria-labelledby="h-' + f.id + '">' +
      '<div class="ex__stage"><div class="ex__in">' +
      '<div class="ex__copy"><div class="ex__badge"><span class="ex__icon">' + ic(f.icon) + '</span><span class="ex__meta"><span class="ex__num">' + esc(f.num) + '</span><span class="kicker">' + esc(f.kicker) + '</span></span></div>' +
      '<h2 id="h-' + f.id + '">' + esc(f.headline) + ' <em>' + esc(f.headlineTurn) + '</em></h2>' +
      '<p class="ex__line">' + esc(f.line) + '</p>' + chips(f) + '</div>' +
      '<div class="ex__piece">' + pieceHtml(f) + demoAfter(f) + '</div>' +
      '<div class="ex__foot">' + steps + next + '</div>' +
      '</div>' + (morning ? '' : '<div class="ex__sky" aria-hidden="true"></div>') + '</div></section>';
  }

  /* The shelf: pieces that already ship on their own in the AutomaticAI store. One generic card per front.shelf[] entry, so a
     new store product is one data entry and never a hand-built section. It only ever links to a page on the store itself
     (never a payment or download URL), and buyable products come first, whatever the order in the data. */
  var STORE = 'https://store.automaticai.io/';
  function shelf() {
    var H = F.shelfHead, list = (F.shelf || []).filter(function (x) { return typeof x.href === 'string' && x.href.indexOf(STORE) === 0; });
    if (!H || !list.length) return '';
    list = list.map(function (x, i) { return { x: x, i: i }; }).sort(function (a, b) {
      return ((b.x.status === 'on-sale') - (a.x.status === 'on-sale')) || (a.i - b.i);
    }).map(function (o) { return o.x; });
    var cards = list.map(function (x) {
      var on = x.status === 'on-sale';
      return '<li class="shelf__card shelf__card--' + esc(x.status) + '" data-shelf="' + esc(x.id) + '">' +
        '<div class="shelf__top"><h3>' + esc(x.name) + '</h3><span class="spill">' + esc(x.pill) + '</span></div>' +
        '<p class="shelf__what">' + esc(x.line) + '</p>' +
        '<ul class="shelf__chips">' + x.chips.map(function (c) { return '<li>' + esc(c) + '</li>'; }).join('') + '</ul>' +
        '<p class="shelf__offer"><b>' + esc(x.offer || H.noOffer) + '</b>' + (x.offer ? '<span>' + esc(t(H.asOf, { date: x.asOf })) + '</span>' : '') + '</p>' +
        '<a class="btn' + (on ? '' : ' btn--quiet') + '" href="' + esc(x.href) + '" target="_blank" rel="noopener">' + esc(x.button) + ' ' + ic('right') +
        '<span class="sr"> (' + esc(H.newTab) + ')</span></a></li>';
    }).join('');
    return '<section class="shelf" id="shelf" aria-labelledby="shelf-h"><div class="shelf__in">' +
      '<p class="kicker">' + esc(H.kicker) + '</p><h2 id="shelf-h">' + esc(H.title) + '</h2><p class="shelf__line">' + esc(H.line) + '</p>' +
      '<ul class="shelf__list">' + cards + '</ul>' +
      '<div class="shelf__foot"><p class="note">' + esc(H.stamp) + '</p>' +
      '<a class="next" href="#' + esc(H.next.to) + '">' + esc(t(F.next, { name: H.next.label })) + ' ' + ic('down') + '</a></div></div></section>';
  }

  function orgBand() {
    var b = M.beats.filter(function (x) { return x.id === 'org-chart'; })[0];
    var o = F.org, c = b.copy;
    var tiles = c.departments.map(function (d) {
      return '<li class="dept"><span class="dept__ic">' + ic(o.icons[d.name] || 'cube') + '</span><b>' + esc(d.name) + '</b><span>' + esc(d.dept) + '</span></li>';
    }).join('');
    return '<section class="orgband" id="org-band" aria-labelledby="org-h"><div class="orgband__in">' +
      '<p class="kicker">' + esc(o.kicker) + '</p><h2 id="org-h">' + esc(o.title) + '</h2><p class="orgband__line">' + esc(o.line) + '</p>' +
      '<ul class="depts" aria-label="' + esc(F.aria.org) + '">' + tiles + '</ul>' +
      '<p class="you"><span class="dept__ic">' + ic('user') + '</span><b>' + esc(c.you.label) + '</b><span>' + esc(c.you.line) + '</span></p></div></section>';
  }

  function well() {
    var w = F.well;
    var figs = F.stats.map(function (x) {
      return '<div class="fig' + (x.you ? ' fig--you' : '') + '"><span class="fig__ic">' + ic(x.icon) + '</span><dt>' + esc(x.n) + '</dt><dd>' + esc(x.label) + '</dd></div>';
    }).join('');
    return '<section class="well" id="counts" aria-labelledby="well-h"><p class="kicker">' + esc(w.kicker) + '</p><h2 id="well-h">' + esc(w.title) + '</h2>' +
      '<dl class="figs">' + figs + '</dl><p class="note">' + esc(w.stamp) + '</p></section>';
  }

  function ask() {
    var a = F.ask;
    return '<section class="ask" id="briefing" aria-labelledby="ask-h"><div class="ask__in">' +
      '<p class="kicker">' + esc(a.kicker) + '</p><h2 id="ask-h">' + esc(a.title) + '</h2><p class="ask__line">' + esc(a.line) + '</p>' +
      '<div id="ask-live" aria-live="polite"><form id="ask-form"><label class="sr" for="em">' + esc(a.label) + '</label>' +
      '<input id="em" type="email" required placeholder="' + esc(a.placeholder) + '" autocomplete="email">' +
      '<input class="hp" type="text" name="_hp" tabindex="-1" autocomplete="off" aria-hidden="true">' +
      '<button class="btn" type="submit">' + esc(a.button) + '</button></form>' +
      '<p class="note">' + esc(a.note) + '</p></div>' +
      '<a class="textlink" href="' + esc(t(a.watchHref)) + '" target="_blank" rel="noopener">' + esc(a.watch) + ' ' + ic('right') + '</a></div></section>';
  }

  function footer() {
    var f = M.site.footer, ff = F.footer;
    return '<footer class="foot"><a class="brand" href="#top" aria-label="' + esc(F.aria.home) + '"><svg aria-hidden="true"><use href="#mark"/></svg><b>' + esc(M.site.name) + '</b></a>' +
      '<span class="foot__by">' + esc(f.byline) + ' · <a href="' + esc(f.link.href) + '">' + esc(f.link.label) + '</a></span>' +
      '<nav class="foot__nav" aria-label="' + esc(F.aria.more) + '"><a class="flink" href="tour.html">' + esc(t(ff.tour)) + ' ' + ic('right') + '</a>' +
      '<a class="flink" href="' + esc(M.site.viewSimulationHref) + '" target="_blank" rel="noopener">' + esc(t(ff.simulation)) + ' ' + ic('right') + '</a></nav>' +
      '<span class="foot__c">' + esc(f.colophon) + '</span></footer>';
  }

  /* ---------- the drawn pieces ---------- */
  var FLAG_COLOUR = { pjangler: 'var(--acc-pjangler)', gateway: 'var(--acc-gateway)', heyma: 'var(--acc-heyma)', flume: 'var(--acc-flume)', 'holocene-auto': 'var(--acc-holocene-auto)' };

  /* The hero building: 12 floors of 8 windows, five lit in the flagships' colours and one in yours, a skyline either side.
     The sky behind it is live (sky.js): the ground line is its horizon, and the lit windows (data-sky-emit) send sparks up. */
  function heroArt() {
    var hb = document.getElementById('hero-bldg'); if (!hb) return;
    var r = rng(33);
    svgEl('rect', { x: 8, y: 196, width: 70, height: 86, fill: 'var(--facade)', stroke: 'var(--facade-edge)' }, hb);
    svgEl('rect', { x: 28, y: 168, width: 40, height: 30, fill: 'var(--facade)', stroke: 'var(--facade-edge)' }, hb);
    svgEl('rect', { x: 282, y: 176, width: 70, height: 106, fill: 'var(--facade)', stroke: 'var(--facade-edge)' }, hb);
    [[18, 214, 'var(--acc-pjangler)'], [46, 238, 'var(--window-lit)'], [296, 196, 'var(--acc-heyma)'], [322, 226, 'var(--acc-gateway)'], [306, 254, 'var(--window-lit)']].forEach(function (w) {
      svgEl('rect', { x: w[0], y: w[1], width: 8, height: 6, fill: w[2], opacity: '.5', 'data-sky-emit': '.5' }, hb);
    });
    svgEl('path', { d: 'M180 30V10', stroke: 'var(--facade-edge)', 'stroke-width': 2 }, hb);
    svgEl('rect', { x: 177, y: 5, width: 6, height: 5, fill: 'var(--window-lit)', 'data-sky-emit': '3' }, hb);
    svgEl('rect', { x: 100, y: 30, width: 160, height: 252, fill: 'var(--facade)', stroke: 'var(--facade-edge)' }, hb);
    var special = { '1-2': 'pjangler', '3-6': 'gateway', '5-1': 'heyma', '7-4': 'flume', '9-6': 'holocene-auto', '11-3': 'you' };
    for (var f = 0; f < 12; f++) for (var c = 0; c < 8; c++) {
      var s = special[f + '-' + c], x = 105 + c * 19.5, y = 39 + f * 20;
      if (s) {
        var col = s === 'you' ? 'var(--window-you)' : FLAG_COLOUR[s];
        svgEl('rect', { x: x - 3, y: y - 3, width: 20, height: 16, rx: 3, fill: col, opacity: '.22' }, hb);
        svgEl('rect', { x: x, y: y, width: 14, height: 10, rx: 1, fill: col, 'data-sky-emit': '4' }, hb);
        continue;
      }
      var v = r();
      var lw = { x: x, y: y, width: 14, height: 10, rx: 1, fill: v < 0.34 ? 'var(--window-dark)' : v < 0.5 ? 'var(--window-working)' : 'var(--window-lit)', opacity: v >= 0.5 ? '.78' : '1' };
      if (v >= 0.5 && (f * 8 + c) % 3 === 0) lw['data-sky-emit'] = '.35';
      svgEl('rect', lw, hb);
    }
    svgEl('path', { d: 'M0 282H360', stroke: 'var(--stage-rule)', 'stroke-width': 2, 'data-sky-horizon': '' }, hb);
  }

  /* PJangler: twelve floors, a crane, and the thirteenth floor on its sling. */
  function pjArt() {
    var a = document.getElementById('pj-art'); if (!a) return;
    var r = rng(7);
    var crane = svgEl('g', { stroke: 'var(--g33-line-strong)', fill: 'none', 'stroke-width': 2 }, a);
    svgEl('path', { d: 'M206 320V34M218 320V34' }, crane);
    svgEl('path', { d: 'M206 320l12-24-12-24 12-24-12-24 12-24-12-24 12-24-12-24 12-24-12-24', 'stroke-width': 1 }, crane);
    svgEl('path', { d: 'M62 30h188M62 38h140M206 34l6-14 6 14', 'stroke-width': 1.5 }, crane);
    svgEl('rect', { x: 232, y: 38, width: 18, height: 12, fill: 'var(--g33-line-strong)', stroke: 'none' }, crane);
    svgEl('rect', { x: 24, y: 80, width: 140, height: 240, fill: 'var(--facade)', stroke: 'var(--facade-edge)' }, a);
    for (var f = 0; f < 12; f++) for (var c = 0; c < 8; c++) {
      var v = r();
      svgEl('rect', { 'class': 'w' + (v < 0.35 ? '' : v < 0.5 ? ' k' : ' l'), x: 31 + c * 16.2, y: 88 + f * 19.5, width: 12, height: 9, rx: 1 }, a);
    }
    svgEl('path', { d: 'M0 320.5H260', stroke: 'var(--g33-line-strong)', 'data-sky-horizon': '' }, a);
    svgEl('rect', { x: 86, y: 28, width: 16, height: 10, fill: 'var(--acc-pjangler)' }, a);
    var g = svgEl('g', { 'class': 'floor13' }, a);
    svgEl('path', { 'class': 'sling', d: 'M94 33L28 56M94 33L160 56', stroke: 'var(--acc-pjangler)', 'stroke-width': 1.2, fill: 'none' }, g);
    svgEl('rect', { x: 24, y: 56, width: 140, height: 24, rx: 2, fill: 'var(--facade)', stroke: 'var(--acc-pjangler)', 'stroke-width': 1.5 }, g);
    for (var k = 0; k < 8; k++) svgEl('rect', { 'class': 'w13', x: 31 + k * 16.2, y: 64, width: 12, height: 9, rx: 1 }, g);
  }

  /* The skyline strip under each dark stage: a few lit windows under a live sky (sky.js), nothing near the words. */
  function skies() {
    [].forEach.call(document.querySelectorAll('.ex__sky'), function (host, n) {
      var r = rng(101 + n * 17);
      var s = svgEl('svg', { viewBox: '0 0 1600 90', preserveAspectRatio: 'xMidYMax slice', 'aria-hidden': 'true' }, host);
      var x = -10;
      while (x < 1610) {
        var w = 28 + Math.floor(r() * 54), h = 12 + Math.floor(Math.pow(r(), 1.4) * 52);
        svgEl('rect', { x: x, y: 90 - h, width: w, height: h, fill: 'var(--facade)', stroke: 'var(--facade-edge)', 'stroke-width': 1 }, s);
        for (var j = 0; j < 3; j++) if (r() < 0.45) svgEl('rect', { x: x + 5 + Math.floor(r() * Math.max(1, w - 14)), y: 90 - h + 6 + Math.floor(r() * Math.max(1, h - 14)), width: 5, height: 4, fill: r() < 0.25 ? 'var(--window-you)' : 'var(--window-working)', opacity: '.5', 'data-sky-emit': '1' }, s);
        x += w + 4 + Math.floor(r() * 16);
      }
    });
  }

  /* Holocene Auto: sunrise over a road, behind the car screen. */
  function dawnArt() {
    var a = document.getElementById('ha-wind'); if (!a) return;
    var defs = svgEl('defs', {}, a);
    var gr = svgEl('linearGradient', { id: 'dawn-sky', x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
    [[0, 'var(--dawn-1)'], [0.62, 'var(--dawn-2)'], [1, 'var(--dawn-3)']].forEach(function (s) { svgEl('stop', { offset: s[0], style: 'stop-color:' + s[1] }, gr); });
    svgEl('rect', { width: 600, height: 220, fill: 'url(#dawn-sky)' }, a);
    svgEl('circle', { cx: 430, cy: 150, r: 34, fill: 'var(--dawn-sun)' }, a);
    svgEl('path', { d: 'M0 160 70 140 130 152 210 128 290 150 360 134 440 156 520 138 600 150V220H0z', fill: 'var(--dawn-hills)', opacity: '.55' }, a);
    svgEl('path', { d: 'M0 220 270 150h60L600 220z', fill: 'var(--dawn-road)' }, a);
    svgEl('path', { d: 'M300 156v8M300 172v12M300 194v18', stroke: 'var(--dawn-line)', 'stroke-width': 4, 'stroke-linecap': 'round' }, a);
  }

  /* The live sky (sky.js) behind every night drawing: the hero building gets the whole show (a distant city on its horizon,
     meteors, sparks from its windows), each skyline strip its own stars and sparks, the PJangler crane a quiet sky. Without
     sky.js the drawings stand on the plain ground, which is how they looked before. */
  function nightSky() {
    var S = window.G33Sky; if (!S) return;
    var hero = document.querySelector('.hero__art');
    /* The hero's sky reaches past the drawing to the page's right edge and up to the header, and dissolves before it
       reaches the words: beside them on a wide screen (two columns), above them on a phone. */
    var wide = function () { try { return matchMedia('(min-width: 900px) and (min-aspect-ratio: 1/1)').matches; } catch (e) { return false; } };
    var room = function (host, r) {
      var top = Math.max(0, r.top - (document.getElementById('top').getBoundingClientRect().top + hdrH()));
      var right = Math.max(0, root.clientWidth - r.right);
      return wide() ? [top, right, 0, Math.round(r.width * 0.3)] : [Math.min(top, 22), right, 0, Math.max(0, r.left)];
    };
    if (hero) S.mount(hero, { seed: 33, density: 520, max: 420, skyline: 2, meteors: 6, motes: 8, bleed: room,
      fade: function (host, r) { var b = room(host, r); return wide() ? [Math.min(90, b[0]), 0, 0, b[3] + Math.round(r.width * 0.12)] : [b[0] + 12, 0, 0, 0]; } });
    /* a strip's sky also fills the empty room above it, up to the exhibit's last line (never behind it) */
    var above = function (host, r) {
      var prev = host.previousElementSibling; if (!prev) return [0, 0, 0, 0];
      var pr = prev.getBoundingClientRect(), pad = parseFloat(getComputedStyle(prev).paddingBottom) || 0;
      return [Math.round(clamp(r.top - pr.bottom + pad - 6, 0, 140)), 0, 0, 0];
    };
    [].forEach.call(document.querySelectorAll('.ex__sky'), function (host, n) {
      S.mount(host, { seed: 40 + n, density: 420, max: 240, band: 0.9, meteors: 1.5, motes: 3, bleed: above,
        fade: function (h, r) { return [Math.round(above(h, r)[0] * 0.8), 0, 0, 0]; } });
    });
    var pj = document.querySelector('.pj__sky');
    if (pj) S.mount(pj, { seed: 9, density: 380, max: 90, pointer: false });
  }

  function waves() {
    [['hm-wave', 11], ['ha-wave', 12]].forEach(function (p) {
      var w = document.getElementById(p[0]); if (!w) return;
      var r = rng(p[1]);
      for (var i = 0; i < 48; i++) {
        var b = document.createElement('i');
        b.style.setProperty('--h', String(Math.round(20 + r() * 80)));
        b.style.setProperty('--d', String(i));
        w.appendChild(b);
      }
    });
  }

  /* ---------- the sky field behind the five exhibits, then the drivers ---------- */
  var exs = [], navs = [], bars = [], pieces = [], tickLis = [], geo = [], hdrEl, navEl, probe, lastKey = '', hdrNow = 56;

  function svh() { var h = probe ? probe.offsetHeight : 0; return h > 0 ? h : innerHeight; }
  function hdrH() { return hdrEl ? hdrEl.offsetHeight : 56; }

  /* Geometry is read here, once per layout change (measure, a resize of the page body), never per scroll frame: the
     frame() below is then pure arithmetic on scrollY, with no layout read to force a style recalc between its writes. */
  var dirty = true, landing = '';
  function geom() {
    hdrNow = hdrH();
    var sy = scrollY;
    exs.forEach(function (ex, i) {
      var r = ex.getBoundingClientRect(), pr = pieces[i].getBoundingClientRect();
      geo[i] = { top: r.top + sy, h: r.height, run: ex.offsetHeight - ex.firstElementChild.offsetHeight, pc: pr.top + sy + pr.height / 2 };
    });
    if (window.G33Sky) window.G33Sky.place();
    dirty = true;
    req();
  }

  /* Pin an exhibit only if its whole stage fits the visible height. The stage is measured unpinned, so the answer
     never depends on whether it is pinned now. */
  function measure() {
    var avail = svh() - hdrH();
    var key = innerWidth + 'x' + avail;
    exs.forEach(function (ex) {
      ex.classList.remove('is-pinned');
      if (flat) return;
      var need = ex.firstElementChild.getBoundingClientRect().height;
      ex.dataset.need = Math.round(need);
      if (need <= avail + 0.5) ex.classList.add('is-pinned');
    });
    root.style.setProperty('--avail', avail + 'px');
    lastKey = key;
    geom();
    /* a deep link (#f-holocene-auto) lands before late fonts re-pin the exhibits above it, which moves it by thousands of
       pixels on a wide screen; until the reader touches the page, every re-measure lands it again */
    if (landing) go(landing, true);
  }

  function gateway(ex, step) {
    var st = F.flagships[1].piece.states;
    ex.querySelectorAll('.pool').forEach(function (li) {
      var n = +li.dataset.pool, s = li.querySelector('.pool__state'), on = step === 0 ? 1 : 2;
      li.classList.toggle('on', n === on);
      li.classList.toggle('dry', n === 1 && step > 0);
      var txt = '';
      if (n === 1) txt = step > 0 ? st.spent : st.drawing;
      else if (n === 2) txt = step > 0 ? st.drawing : st.waiting;
      else if (n === 3) txt = st.waiting;
      else if (n === 4) txt = st.backstop;
      else txt = step > 1 ? st.grown : st.scouting;
      s.textContent = txt;
      var w = n === 1 ? (step > 0 ? 4 : 46) : n === 2 ? (step > 0 ? 66 : 88) : n === 3 ? 100 : n === 4 ? 62 : step > 1 ? 100 : 0;
      li.querySelector('.meter i').style.width = w + '%';
    });
    ex.querySelectorAll('.gw__wires path').forEach(function (p) {
      var n = +p.dataset.w, on = step === 0 ? 1 : 2;
      p.classList.toggle('hot', n === on);
      p.style.opacity = n === 5 && step < 2 ? '0' : n === 1 && step > 0 ? '.35' : '1';
    });
  }

  var ticking = false, lastActive = -2, lastY = -1, lastVh = -1, saveT = 0, barF = [];
  function req() { if (!ticking) { ticking = true; requestAnimationFrame(frame); } }

  /* the scroll position is remembered for a reload, but only once scrolling settles: a storage write per frame is a main-thread stall */
  function save() {
    saveT = 0;
    try { sessionStorage.setItem('front.y', String(Math.round(scrollY))); } catch (e) { /* private window */ }
  }

  function frame() {
    ticking = false;
    var sy = scrollY, vh = innerHeight;
    if (!dirty && sy === lastY && vh === lastVh) return;
    dirty = false; lastY = sy; lastVh = vh;
    var hdr = hdrNow, mid = hdr + (vh - hdr) * 0.5, active = -1;
    exs.forEach(function (ex, i) {
      var g = geo[i], top = g.top - sy, p = 1;
      if (!flat) {
        if (ex.classList.contains('is-pinned')) {
          p = g.run > 0 ? clamp((hdr - top) / g.run) : 0;
        } else {
          var c = g.pc - sy, a = vh * 0.85, b = hdr + (vh - hdr) * 0.45;
          p = clamp((a - c) / (a - b));
        }
      }
      var steps = +ex.dataset.steps || 3, step = flat ? steps - 1 : Math.min(steps - 1, Math.floor(p * steps));
      if (ex.dataset.step !== String(step)) {
        ex.dataset.step = String(step);
        if (ex.dataset.flag === 'gateway') gateway(ex, step);
      }
      var n = +ex.dataset.ticks;
      if (n) {
        var done = flat ? n : Math.min(n, Math.floor(p * n * 1.25) + 1);
        if (ex._done !== done) {
          ex._done = done;
          tickLis[i].forEach(function (li, k) { li.classList.toggle('done', k < done); });
        }
      }
      if (top <= mid && top + g.h > mid) active = i;
      if (bars[i]) {
        var f = top > mid ? '0' : clamp((mid - top) / Math.max(1, g.h)).toFixed(3);
        if (barF[i] !== f) { barF[i] = f; bars[i].style.setProperty('--f', f); }
      }
    });
    if (active !== lastActive) {
      lastActive = active;
      navs.forEach(function (a, i) { if (i === active) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current'); });
      /* a phone's flagship strip may scroll sideways: keep the current one in view (never the page) */
      var cur = navs[active];
      if (cur && navEl && navEl.scrollWidth > navEl.clientWidth + 1) {
        var to = cur.offsetLeft - (navEl.clientWidth - cur.offsetWidth) / 2;
        try { navEl.scrollTo({ left: to, behavior: flat ? 'auto' : 'smooth' }); } catch (e) { navEl.scrollLeft = to; }
      }
    }
    if (!saveT) saveT = setTimeout(save, 250);
  }

  function go(id, instant) {
    var el = id === 'top' ? null : document.getElementById(id);
    if (id !== 'top' && !el) return false;
    var y = id === 'top' ? 0 : el.getBoundingClientRect().top + scrollY - (el.classList.contains('hero') ? 0 : hdrH());
    scrollTo({ top: Math.max(0, y), behavior: flat || instant ? 'auto' : 'smooth' });
    return true;
  }

  function wire() {
    addEventListener('scroll', req, { passive: true });
    addEventListener('pagehide', save);
    /* a resize re-measures (pinning depends on the width and the visible height); coalesced to once per frame, since a phone's address bar fires it on every scroll tick */
    var rz = 0;
    addEventListener('resize', function () {
      if (rz) return;
      rz = requestAnimationFrame(function () {
        rz = 0;
        var avail = svh() - hdrH();
        if (innerWidth + 'x' + avail !== lastKey) measure(); else { dirty = true; req(); }
      });
    });
    /* anything that moves the exhibits without a resize (a late font, the sign-up form swapping for its thanks): read the geometry again */
    if (window.ResizeObserver) { var ro = new ResizeObserver(function () { geom(); }); ro.observe(document.getElementById('front')); }
    /* the endless little animations (the live wire, the call's waveform) only run while they are on screen */
    var anim = [].slice.call(document.querySelectorAll('.wave, .gw__wires'));
    if (window.IntersectionObserver) {
      var io = new IntersectionObserver(function (es) { es.forEach(function (e) { e.target.classList.toggle('is-live', e.isIntersecting); }); }, { rootMargin: '80px 0px' });
      anim.forEach(function (el) { io.observe(el); });
    } else anim.forEach(function (el) { el.classList.add('is-live'); });
    /* demo videos: muted loops that play only while at least half on screen (never by themselves under reduced motion);
       the button plays or pauses, and a pause by hand sticks until the next press */
    [].forEach.call(document.querySelectorAll('.demo'), function (fig) {
      var v = fig.querySelector('video'), b = fig.querySelector('.demo__play');
      fig._want = !flat;
      function sync() { var on = !v.paused; fig.classList.toggle('is-playing', on); b.setAttribute('aria-label', on ? b.dataset.pause : b.dataset.play); }
      function play() { var pr = v.play(); if (pr && pr.catch) pr.catch(function (er) { if (er && er.name === 'NotAllowedError') fig._want = false; sync(); });  /* only a refusal (autoplay blocked, low power) stops it for good; an AbortError is our own off-screen pause */ }
      v.addEventListener('play', sync); v.addEventListener('pause', sync);
      b.addEventListener('click', function () { if (v.paused) { fig._want = true; play(); } else { fig._want = false; v.pause(); } });
      if (window.IntersectionObserver) {
        new IntersectionObserver(function (es) {
          es.forEach(function (e) { if (e.isIntersecting && fig._want && !document.hidden) play(); else if (!e.isIntersecting && !v.paused) v.pause(); });
        }, { threshold: 0.5 }).observe(fig.querySelector('.demo__frame'));
      }
    });
    addEventListener('orientationchange', function () { setTimeout(measure, 250); });
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(measure);
      if (document.fonts.addEventListener) document.fonts.addEventListener('loadingdone', measure);
    }
    document.addEventListener('click', function (e) {
      var a = e.target.closest && e.target.closest('a[href^="#"]');
      if (!a) return;
      var id = a.getAttribute('href').slice(1);
      if (!go(id)) return;
      e.preventDefault();
      try { history.replaceState(null, '', id === 'top' ? location.pathname + location.search : '#' + id); } catch (er) { /* no history */ }
    });
    var form = document.getElementById('ask-form');
    if (form) form.addEventListener('submit', function (e) {
      e.preventDefault();
      var input = document.getElementById('em'), btn = form.querySelector('button'), hp = form.elements._hp;
      var email = input.value.trim();
      if (!email || btn.disabled) return;
      btn.disabled = true; input.disabled = true; form.setAttribute('aria-busy', 'true');
      var label = btn.textContent; btn.textContent = F.ask.sending;
      var old = document.getElementById('ask-err'); if (old) old.remove();
      /* the same sign-up the tour posts: forms.js -> /_forms/briefing -> form-intake */
      var post = window.G33Forms ? window.G33Forms.submit('briefing', { email: email, _hp: hp ? hp.value : '' }) : Promise.resolve({ ok: false, error: F.ask.error });
      post.then(function (r) {
        if (r.ok) {
          var p = document.createElement('p');
          p.className = 'ask__done'; p.setAttribute('role', 'status');
          p.textContent = F.ask.done;
          form.replaceWith(p);
          return;
        }
        btn.disabled = false; input.disabled = false; btn.textContent = label; form.removeAttribute('aria-busy');
        var er = document.createElement('p');
        er.id = 'ask-err'; er.className = 'ask__err'; er.setAttribute('role', 'alert');
        er.textContent = r.error || F.ask.error;
        form.after(er);
      });
    });
  }

  /* ---------- boot ---------- */
  function boot() {
    var want = ''; try { want = decodeURIComponent(location.hash.slice(1)); } catch (e) { want = ''; }
    /* an old tour link: a #beat names a tour section, so the tour answers it */
    if (want && M.beats.some(function (b) { return b.id === want; })) { location.replace('tour.html' + location.search + location.hash); return; }
    TOTAL = M.beats.length;
    document.title = F.title;
    var host = document.getElementById('front');
    host.innerHTML = '<a class="skip" href="#flagships">' + esc(F.aria.skip) + '</a>' + header() + '<main>' + hero() + F.flagships.map(function (f, i) { return exhibit(f, i) + (F.shelfHead && f.id === F.shelfHead.after ? shelf() : ''); }).join('') + orgBand() + well() + ask() + '</main>' + footer();
    heroArt(); pjArt(); skies(); dawnArt(); waves();
    exs = [].slice.call(document.querySelectorAll('.ex'));
    navs = [].slice.call(document.querySelectorAll('.nav a'));
    bars = [].slice.call(document.querySelectorAll('.prog i'));
    pieces = exs.map(function (ex) { return ex.querySelector('.ex__piece'); });
    tickLis = exs.map(function (ex) { return ex.dataset.tickSel ? [].slice.call(ex.querySelectorAll(ex.dataset.tickSel)) : []; });
    hdrEl = document.getElementById('hdr'); navEl = document.getElementById('nav');
    nightSky();
    probe = document.createElement('div');
    probe.setAttribute('aria-hidden', 'true');
    probe.style.cssText = 'position:fixed;left:0;top:0;width:0;height:100svh;visibility:hidden;pointer-events:none';
    document.body.appendChild(probe);
    try { if ('scrollRestoration' in history) history.scrollRestoration = 'manual'; } catch (e) { /* ignore */ }
    wire();
    measure();
    var nt = ''; try { nt = (performance.getEntriesByType('navigation')[0] || {}).type || ''; } catch (e) { nt = ''; }
    if (want && document.getElementById(want)) {
      landing = want; go(want, true);
      var settle = function () { landing = ''; };
      ['wheel', 'touchstart', 'keydown', 'mousedown'].forEach(function (ev) { addEventListener(ev, settle, { passive: true, once: true }); });
      setTimeout(settle, 4000);
    }
    else if (nt === 'reload' || nt === 'back_forward') {
      var y = 0; try { y = +sessionStorage.getItem('front.y') || 0; } catch (e) { y = 0; }
      if (y) scrollTo(0, y);
    }
    root.classList.add('ready');
    req();
  }

  fetch('manifest.json', { cache: 'no-cache' }).then(function (r) {
    if (!r.ok) throw new Error('manifest.json: HTTP ' + r.status);
    return r.json();
  }).then(function (m) {
    M = m; F = m.front;
    if (!F) throw new Error('manifest.json has no "front" record');
    boot();
  }).catch(function (e) { fail(e && e.message ? e.message : String(e)); });
})();
