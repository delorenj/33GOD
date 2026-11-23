/* 33GOD tour: the phone layout ("flow view").
   Phones and small tablets (under 900px) get the same 21 sections as the film, one after another in a single column,
   each with its exhibit set inline and its words trimmed to what a thumb-sized screen can hold: a lead, a "More"
   disclosure, and a "Source and events" disclosure that keeps the provenance and the real event subjects.

   Everything is read from manifest.json and staged by the same score the film uses: an exhibit's beats are
   SC.minor(...) lookups at the section's own progress q. Where q comes from is the front page's rule: a section PINS
   (sticky, q off the scroll through its pinned run) only when its whole stage fits the small-viewport height minus the
   header, measured in JS; otherwise it flows, and q follows where the exhibit sits in the viewport. Either way the story
   advances off scroll position. Reduced motion never pins and shows every final state (q = 1).

   Loaded before overnight.js; overnight.js calls OvernightFlow.create(kit) once it has the manifest and the score. */
(function () {
  'use strict';
  var STEPS = 60;                                        // q is quantised so a section re-renders at most 60 times a pass
  var ACT_ACC = { I: 'arrival', II: 'bylaws', III: 'platform', IV: 'work', V: 'voice', VI: 'staff' };
  var ACT_ICON = { I: 'factory', II: 'org', III: 'clock', IV: 'lanes', V: 'wave', VI: 'cube' };
  var BEAT_ACC = { pjangler: 'pjangler', gateway: 'gateway', flume: 'flume', heyma: 'heyma', 'holocene-auto': 'holocene-auto', ask: 'ask' };
  var BEAT_ICON = {
    thesis: 'user', numbers: 'gauge', 'org-chart': 'org', bus: 'bus', 'runs-on-itself': 'crank', 'clock-records': 'clock', 'agents-desk': 'desk',
    pjangler: 'factory', flume: 'hire', 'pm-krebs': 'lanes', harvest: 'board', skillex: 'book', gateway: 'bolt', heyma: 'wave', wax: 'mic',
    speakers: 'wave', jev: 'review', 'holocene-auto': 'car', staff: 'cube', ask: 'monitor'
  };
  var NAV_ICON = { 'org-chart': 'org', 'clock-records': 'clock', pjangler: 'factory', heyma: 'wave', ask: 'monitor' };
  var FIG_ICON = ['cube', 'globe', 'schema', 'link', 'user'];
  var DEPT_ICON = { CANDYBAR: 'clock', CANDYSTORE: 'archive', HERMES: 'desk', 'HOOK-HUB': 'link', HINDSIGHT: 'book', ASM: 'gauge' };
  var CHECK_ICON = ['template', 'board', 'branch', 'user', 'book', 'rocket'];
  var PIPE_ICON = { hired: 'hire', onboarded: 'book', seated: 'desk', reviewed: 'review' };
  var PART_SYM = { WAX: 'p-wax', VINYL: 'p-vinyl', PHONOGRAPH: 'p-phono', SHORTWAVE: 'p-short' };
  var ROLE_ICON = ['org', 'lanes', 'user'];

  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function seg(v, a, b) { return clamp((v - a) / (b - a), 0, 1); }

  window.OvernightFlow = { create: create };

  function create(K) {
    var React = K.React, h = K.h, O = K.O, SC = K.SC, M = K.M, I = K.I;
    var useState = React.useState, useEffect = React.useEffect, useLayoutEffect = React.useLayoutEffect, useRef = React.useRef, useMemo = React.useMemo;
    var beats = M.beats, site = M.site, W = site.flow || {};
    var F = M.front || {};
    var flat = false;
    try { flat = window.matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) { flat = false; }

    /* ---------- small pieces ---------- */
    function ico(n, cls) { return h('svg', { className: 'fw-i' + (cls ? ' ' + cls : ''), 'aria-hidden': 'true', focusable: 'false' }, h('use', { href: '#i-' + n })); }
    function sym(id, cls) { return h('svg', { className: 'fw-i' + (cls ? ' ' + cls : ''), 'aria-hidden': 'true', focusable: 'false' }, h('use', { href: '#' + id })); }
    function win(state) { return h('span', { className: 'fw-win', 'aria-hidden': 'true' }, h(O.Window, { state: state })); }
    function accOf(b) { return BEAT_ACC[b.id] || ACT_ACC[b.act]; }
    // The first sentence or two is the lead; the rest of the prose waits behind "More".
    function sentences(t) { return (t || '').match(/[^.!?]+(?:[.!?]+["”')\]]*)(?:\s+|$)|[^.!?]+$/g) || [t || '']; }
    function leadOf(text, max) {
      var s = sentences(text), out = '', k = 0;
      while (k < s.length && (k === 0 || out.length + s[k].length <= max)) out += s[k++];
      return [out.trim(), s.slice(k).join('').trim()];
    }
    // "PJangler. The project factory." sets the first sentence in ink and the rest in the section's accent.
    function titleParts(t) {
      var s = sentences(t);
      return s.length > 1 ? [s[0].trim(), s.slice(1).join('').trim()] : [t, ''];
    }
    // An event subject is a chip that wraps: a break is offered after every dot, so even bloodbank.evt.agent.hook.updated never scrolls.
    function broken(t) { var out = []; t.split('.').forEach(function (part, n, a) { out.push(part + (n < a.length - 1 ? '.' : '')); if (n < a.length - 1) out.push(h('wbr', { key: n })); }); return out; }
    function Subject(p) {
      var m = K.BUS_PREFIX.exec(p.text);
      return h('code', { className: 'fw-subj' }, m ? h('span', { className: 'fw-subj__p' }, broken(m[0])) : null, broken(p.text.replace(K.BUS_PREFIX, '')));
    }
    function Disclosure(p) {
      return h('details', { className: 'fw-more ' + (p.cls || ''), open: p.open || undefined },
        h('summary', null, h('span', null, p.label), ico('down', 'fw-more__chev')),
        h('div', { className: 'fw-more__body' }, p.children));
    }

    /* ---------- the building: the whole company in a few dozen pixels, staged by the film's own windowStates ---------- */
    function Locator(p) {
      var b = p.b, i = p.i, q = p.q, ex = b.copy && b.copy.exhibit, focus = null;
      if (ex) { focus = {}; ex.seats.forEach(function (n) { focus[n] = true; }); }
      var floors = i > I.pjangler || (i === I.pjangler && q >= 0.06) ? K.FLOORS + 1 : K.FLOORS;
      var step = Math.floor(q * STEPS);
      var w = useMemo(function () {
        return K.windowStates({ q: q, step: step, I: I, i: i, seats: K.seats, floors: floors, submitted: !!p.submitted, focus: focus, live: !!(ex && ex.live) });
      }, [step, floors, !!p.submitted, i]);
      var deco = p.size === 'xs';
      return h('div', { className: 'fw-bldg fw-bldg--' + p.size, 'aria-hidden': deco ? 'true' : null },
        h(O.Building, { floors: floors, perFloor: K.PER, states: w.states, you: w.you, youLit: w.youLit, label: p.label || 'The company: a building of ' + floors + ' floors, one window per component.' }));
    }

    /* ---------- the exhibits ---------- */
    function Figures(p) {
      var c = p.b.copy;
      return h('ul', { className: 'fw-figs' }, c.figures.map(function (f, k) {
        var d = K.detailOf(f), you = !d && k === c.figures.length - 1;
        var face = [h('span', { key: 'i', className: 'fw-fig__ic' }, ico(FIG_ICON[k] || 'cube')), h('b', { key: 'n', className: 'fw-fig__n' }, f.n), h('span', { key: 'l', className: 'fw-fig__l' }, f.label)];
        return h('li', { key: k, className: 'fw-fig fw-rv' + (you ? ' fw-fig--you' : ''), style: { '--at': 0.04 + k * 0.1 } },
          d ? h('details', null, h('summary', { className: 'fw-fig__face' }, face, ico('down', 'fw-fig__chev')), h('p', { className: 'fw-fig__d' }, d)) : h('div', { className: 'fw-fig__face' }, face));
      }));
    }

    function Org(p) {
      var c = p.b.copy, icons = (F.org && F.org.icons) || {};
      return h('div', { className: 'fw-org' },
        h('figure', { className: 'fw-quote fw-rv', style: { '--at': 0 } }, h('blockquote', null, c.quote), h('figcaption', null, c.quoteSource)),
        h('ul', { className: 'fw-depts' }, c.departments.map(function (d, k) {
          var more = K.detailOf(d);
          return h('li', { key: d.name, className: 'fw-rv', style: { '--at': 0.05 + k * 0.05 } },
            h('details', { className: 'fw-dept' },
              h('summary', null, h('span', { className: 'fw-dept__ic' }, ico(icons[d.name] || 'cube')), h('b', null, d.name), h('span', { className: 'fw-dept__t' }, d.dept)),
              h('p', { className: 'fw-dept__line' }, d.line), more ? h('p', { className: 'fw-dept__more' }, more) : null));
        })),
        h('p', { className: 'fw-you fw-rv', style: { '--at': 0.7 } }, h('span', { className: 'fw-you__ic' }, ico('user')), h('b', null, c.you.label), h('span', null, c.you.line)));
    }

    function Bus(p) {
      var c = p.b.copy, q = p.q, at = [0.17, 0.38, 0.59, 0.8];
      return h('div', { className: 'fw-bus' },
        h('div', { className: 'fw-bus__event' }, win('lit'), h(Subject, { text: c.event })),
        h('ol', { className: 'fw-bus__list' }, c.listeners.map(function (l, k) {
          var heard = q > at[k];
          return h('li', { key: l.name, className: 'fw-bus__l' + (heard ? ' is-heard' : '') }, win(heard ? 'lit' : 'dark'), h('b', null, l.name), h('span', null, l.does));
        })),
        h('p', { className: 'fw-punch fw-rv', style: { '--at': 0.84 } }, c.punch),
        h('div', { className: 'fw-tape', 'aria-hidden': 'true' },
          h('div', { className: 'fw-tape__row fw-tape__row--a' }, c.tapeA.concat(c.tapeA).map(function (t, k) { return h('span', { key: k }, t.replace(K.BUS_PREFIX, '')); })),
          h('div', { className: 'fw-tape__row fw-tape__row--b' }, c.tapeB.concat(c.tapeB).map(function (t, k) { return h('span', { key: k }, t.replace(K.BUS_PREFIX, '')); }))));
    }

    function Loop(p) {
      var c = p.b.copy, lp = SC.minor('runs-on-itself', 'loop', p.q), passed = lp.p > 0 ? lp.step + 1 : 0, n = c.steps.length;
      var pips = c.steps.map(function (s, k) {
        var a = (k / n) * Math.PI * 2 - Math.PI / 2;
        return h('i', { key: k, className: 'fw-loop__pip' + (k < passed ? ' is-passed' : ''), style: { left: (50 + Math.cos(a) * 46) + '%', top: (50 + Math.sin(a) * 46) + '%' } });
      });
      return h('div', { className: 'fw-loop', style: { '--lp': lp.p.toFixed(3) } },
        h('div', { className: 'fw-loop__ring', 'aria-hidden': 'true' },
          h('svg', { viewBox: '0 0 100 100' }, h('circle', { cx: 50, cy: 50, r: 46, className: 'fw-loop__track' }), h('circle', { cx: 50, cy: 50, r: 46, className: 'fw-loop__drawn', pathLength: 1 })),
          pips,
          h('span', { className: 'fw-loop__dot' }, win('lit')),
          h('div', { className: 'fw-loop__core' }, h('b', null, c.count), h('span', null, c.countLabel))),
        h('ol', { className: 'fw-loop__steps' }, c.steps.map(function (s, k) {
          return h('li', { key: k, className: k < passed ? 'is-passed' : '' }, h('span', { className: 'fw-loop__n' }, k + 1), h('span', null, s));
        })));
    }

    function Dept(p) {
      var b = p.b, c = b.copy;
      return h('div', { className: 'fw-dept-card' },
        h('ul', { className: 'fw-members' }, c.members.map(function (m, k) {
          var more = K.detailOf(m);
          return h('li', { key: m.name, className: 'fw-member fw-rv', style: { '--at': 0.03 + k * 0.06 } },
            h('span', { className: 'fw-member__ic' }, ico(DEPT_ICON[m.name] || 'cube')),
            h('span', { className: 'fw-member__t' }, h('b', null, m.name), h('span', { className: 'fw-member__r' }, m.role), h('span', { className: 'fw-member__l' }, m.line), more ? h('span', { className: 'fw-member__l' }, more) : null));
        })),
        h('ul', { className: 'fw-figs fw-figs--dept' }, c.figures.map(function (f, k) {
          return h('li', { key: k, className: 'fw-fig fw-rv', style: { '--at': 0.2 + k * 0.08 } },
            h('details', null, h('summary', { className: 'fw-fig__face' }, h('b', { className: 'fw-fig__n' }, f.n), h('span', { className: 'fw-fig__l' }, f.label), ico('down', 'fw-fig__chev')), h('p', { className: 'fw-fig__d' }, f.detail)));
        })),
        c.events && c.events.length ? h('div', { className: 'fw-events fw-rv', style: { '--at': 0.55 } },
          h('p', { className: 'fw-label' }, c.eventsTitle),
          h('ul', null, c.events.map(function (e) { return h('li', { key: e.type }, h(Subject, { text: e.type }), h('b', null, e.n)); }))) : null);
    }

    function Pjangler(p) {
      var c = p.b.copy, done = K.checklistDone(p.q);
      return h('div', { className: 'fw-pj' },
        h(Locator, { b: p.b, i: p.i, q: p.q, size: 'md', label: 'The building grows a thirteenth floor.' }),
        h('div', { className: 'fw-check' },
          h('h3', null, c.cardTitle), h('p', { className: 'fw-label' }, c.cardNote),
          h('ol', null, c.checklist.map(function (s, k) {
            return h('li', { key: k, className: k < done ? 'is-done' : '' }, h('span', { className: 'fw-check__ic' }, ico(CHECK_ICON[k] || 'check')), h('span', { className: 'fw-check__t' }, s), ico('check', 'fw-check__tick'));
          }))));
    }

    function Flume(p) {
      var c = p.b.copy, q = p.q, stageN = SC.minor('flume', 'pipeline', q).step;
      var hired = q >= SC.range('flume', 'hire').from, shipped = SC.minor('flume', 'shipped', q).active;
      return h('div', { className: 'fw-flume' },
        h('p', { className: 'fw-label' }, c.rolesTitle),
        h('ul', { className: 'fw-roles' }, c.roles.map(function (r, k) {
          return h('li', { key: r.name, className: 'fw-role' }, h('span', { className: 'fw-role__ic' }, ico(ROLE_ICON[k] || 'user')), h('b', null, r.name), h('span', null, r.line));
        }).concat([
          h('li', { key: 'hire', className: 'fw-role fw-role--open' + (hired ? ' is-on' : '') + (shipped ? ' is-shipped' : '') },
            h('span', { className: 'fw-role__ic' }, win(shipped ? 'shipped' : hired ? 'lit' : 'dark')), h('b', null, c.hire.name), h('span', null, c.hire.line))
        ])),
        h('ol', { className: 'fw-pipe' }, c.pipeline.map(function (s, k) {
          return h('li', { key: s, className: k < stageN ? 'is-done' : '' }, ico(PIPE_ICON[s] || 'check'), h('span', null, s));
        })));
    }

    function Krebs(p) {
      var q = p.q, T = M.transcript;
      return h('div', { className: 'fw-krebs' },
        h(Locator, { b: p.b, i: p.i, q: q, size: 'md' }),
        h('ul', { className: 'fw-tickets' }, T.tickets.map(function (t, k) {
          return h('li', { key: k, className: 'fw-ticket' + (q > 0.42 + k * 0.07 ? ' is-in' : '') }, h('b', null, t.board), h('span', null, t.title));
        })));
    }

    // The conference-room glass: one illustrated transcript, read by Wax, Voice-ID, Jev and Pilot.
    function Transcript(p) {
      var id = p.b.id, q = p.q, T = M.transcript;
      var labelled = id === 'speakers' ? SC.minor('speakers', 'voices', q).step : id === 'jev' || id === 'harvest' ? 99 : 0;
      var found = id === 'jev' ? SC.minor('jev', 'judgments', q).step : id === 'harvest' ? 99 : 0;
      var peeled = id === 'harvest' ? SC.minor('harvest', 'tickets', q).step : 0;
      var pCount = 0;
      function text(t) {
        var out = [], re = /\{p:([^}]+)\}/g, last = 0, m, k = 0;
        while ((m = re.exec(t))) {
          if (m.index > last) out.push(t.slice(last, m.index));
          var on = pCount < found; pCount++;
          out.push(h('span', { key: k++, className: 'fw-tx__p' + (on ? ' is-found' : '') }, m[1]));
          last = m.index + m[0].length;
        }
        if (last < t.length) out.push(t.slice(last));
        return out;
      }
      var seen = {};
      var lines = T.lines.map(function (l, n) {
        var named = false;
        if (labelled > 0) { var order = Object.keys(seen).length; if (!(l.s in seen)) seen[l.s] = order; named = seen[l.s] < labelled; }
        var taken = l.ticket != null && l.ticket < peeled;
        var on = id !== 'wax' || q > 0.06 + n * 0.1;
        return h('li', { key: n, className: 'fw-tx__line' + (on ? ' is-on' : '') + (taken ? ' is-taken' : '') },
          h('span', { className: 'fw-tx__who' + (named ? ' is-named' : '') }, named ? T.speakers[l.s] : ''),
          h('p', null, text(l.text)));
      });
      var side;
      if (id === 'jev') {
        side = h('ul', { className: 'fw-side' }, T.judgments.map(function (j, n) {
          return h('li', { key: n, className: 'fw-judge' + (n < found ? ' is-in' : '') }, h('span', null, j.q), h('b', { className: j.a === 'yes' ? 'is-yes' : '' }, j.a));
        }));
      } else if (id === 'speakers') {
        side = h('ul', { className: 'fw-side fw-voices' }, T.speakers.map(function (s, n) {
          var on = n < labelled;
          return h('li', { key: n, className: 'fw-voice' + (on ? ' is-in' : '') },
            h('span', { className: 'fw-voice__print', 'aria-hidden': 'true' }, [3, 7, 5, 9, 4, 8, 6, 5, 8, 3].map(function (v, k) { return h('i', { key: k, style: { height: ((v * (n + 2) * 7) % 13 + 6) + 'px' } }); })),
            h('b', null, on ? s : ''));
        }));
      } else if (id === 'harvest') {
        side = h('ul', { className: 'fw-side fw-tickets' }, T.tickets.map(function (t, n) {
          return h('li', { key: n, className: 'fw-ticket' + (n < peeled ? ' is-in' : '') }, h('b', null, t.board), h('span', null, t.title));
        }));
      } else {
        side = h('div', { className: 'fw-side fw-waxnote fw-rv', style: { '--at': 0.5 } }, h('b', null, 'WAX'), h('span', null, K.seats.named.WAX.line));
      }
      var linesEl = h('ol', { className: 'fw-tx' }, lines);
      return h('div', { className: 'fw-glass' },
        h('div', { className: 'fw-glass__head' }, win('working'), h('span', null, T.room)),
        id === 'wax' ? [side, linesEl].reverse().map(function (el, k) { return h(React.Fragment, { key: k }, el); })
          : [h(React.Fragment, { key: 's' }, side), h(Disclosure, { key: 'd', label: W.transcript || 'Read the transcript', cls: 'fw-more--tx' }, linesEl)]);
    }

    function Gateway(p) {
      var c = p.b.copy, q = p.q, dn = c.decisions[K.decisionAt(q)], meters = K.gwMeters();
      var sw = K.gwAt('switch');
      return h('div', { className: 'fw-gw' },
        h('div', { className: 'fw-gw__head' }, ico('bolt'), h('code', null, c.cardTitle)),
        h('ul', { className: 'fw-pools' }, c.pools.map(function (pl, n) {
          var st = K.poolAt(n, q, c.states), mt = meters[n];
          return h('li', { key: n, className: 'fw-pool' + (st[0] === 'working' || st[0] === 'shipped' ? ' is-on' : st[0] === 'dark' ? ' is-out' : '') },
            h('div', { className: 'fw-pool__top' }, win(st[0]), h('b', null, pl.name), h('span', { className: 'fw-pool__state' }, st[1])),
            h('span', { className: 'fw-meter', 'aria-hidden': 'true' }, h('i', { style: { '--from': mt.from, '--to': mt.to, '--a': mt.a, '--b': mt.b } })));
        })),
        h('div', { key: 'd' + K.decisionAt(q), className: 'fw-decision', role: 'status' }, h('code', null, dn.route), h('span', null, dn.line)),
        h('p', { className: 'fw-punch fw-rv', style: { '--at': sw + 0.03 } }, c.punch));
    }

    function HeyMa(p) {
      var c = p.b.copy, q = p.q, call = c.call;
      var act = Math.min(c.parts.length - 1, Math.floor(q * c.parts.length));
      var on = function (id) { return q >= SC.beatQ('heyma', 'call', id) - K.RV; };
      return h('div', { className: 'fw-hm' },
        h('ul', { className: 'fw-parts' }, c.parts.map(function (pt, k) {
          return h('li', { key: pt.name, className: 'fw-part' + (k === act ? ' is-on' : '') }, sym(PART_SYM[pt.name] || 'i-cube'), h('b', null, pt.name), h('span', null, pt.line));
        })),
        h('div', { className: 'fw-phone' },
          h('div', { className: 'fw-phone__island', 'aria-hidden': 'true' }),
          h('p', { className: 'fw-label' }, ico('phone'), call.label),
          h('div', { className: 'fw-wave', 'aria-hidden': 'true' }, Array.from({ length: 36 }, function (_, k) { return h('i', { key: k, style: { '--h': 20 + ((k * 37) % 11) * 8, '--d': k } }); })),
          h('p', { className: 'fw-say fw-say--heard is-on', lang: 'pt' }, call.heard),
          h('p', { className: 'fw-say fw-say--en' + (on('translated') ? ' is-on' : '') }, call.translated),
          h('div', { className: 'fw-say fw-say--you' + (on('whisper') ? ' is-on' : '') }, h('small', null, call.whisperLabel), h('p', null, '“' + call.whisper + '”'))));
    }

    function DawnArt() {
      return h('svg', { className: 'fw-dawn', viewBox: '0 0 600 220', preserveAspectRatio: 'xMidYMid slice', 'aria-hidden': 'true' },
        h('defs', null, h('linearGradient', { id: 'fw-dawn-sky', x1: 0, y1: 0, x2: 0, y2: 1 },
          h('stop', { offset: 0, style: { stopColor: 'var(--dawn-1)' } }), h('stop', { offset: 0.62, style: { stopColor: 'var(--dawn-2)' } }), h('stop', { offset: 1, style: { stopColor: 'var(--dawn-3)' } }))),
        h('rect', { width: 600, height: 220, fill: 'url(#fw-dawn-sky)' }),
        h('circle', { cx: 430, cy: 150, r: 34, fill: 'var(--dawn-sun)' }),
        h('path', { d: 'M0 160 70 140 130 152 210 128 290 150 360 134 440 156 520 138 600 150V220H0z', fill: 'var(--dawn-hills)', opacity: '.55' }),
        h('path', { d: 'M0 220 270 150h60L600 220z', fill: 'var(--dawn-road)' }),
        h('path', { d: 'M300 156v8M300 172v12M300 194v18', stroke: 'var(--dawn-line)', strokeWidth: 4, strokeLinecap: 'round' }));
    }
    function Car(p) {
      var c = p.b.copy, s = c.screen, q = p.q;
      return h('div', { className: 'fw-car' },
        h('div', { className: 'fw-car__scene' }, h(DawnArt),
          h('div', { className: 'fw-car__screen' },
            h('div', { className: 'fw-car__top' }, h(K.Mark, { size: 16 }), h('span', null, s.product), h('span', { className: 'fw-car__sig' }, ico('speaker'), s.signal)),
            h('p', { className: 'fw-car__line' }, s.line),
            h('div', { className: 'fw-car__bot' }, h('b', null, ico('check'), s.count), h('span', null, s.sub)))),
        h('div', { className: 'fw-standup' },
          h('p', { className: 'fw-label' }, ico('car'), c.standupTitle),
          h('div', { className: 'fw-bars', 'aria-hidden': 'true' }, Array.from({ length: 28 }, function (_, k) { return h('i', { key: k, style: { height: (4 + Math.abs(Math.sin(k * 1.7 + q * 26)) * Math.abs(Math.sin(k * 0.45 + q * 9)) * 22).toFixed(1) + 'px' } }); })),
          h('ol', null, c.standup.map(function (line, n) {
            return h('li', { key: n, className: q >= SC.stopQ('holocene-auto', 'standup', n + 1) - K.RV ? 'is-on' : '' }, h('small', null, '0' + (n + 1)), h('span', null, line));
          }))));
    }

    function Staff(p) {
      var c = p.b.copy, st = useState(null), sel = st[0];
      var auto = Math.min(c.staff.length - 1, SC.minor('staff', 'roll', p.q).step);
      var k = sel != null ? sel : auto, cur = c.staff[k], more = K.detailOf(cur);
      return h('div', { className: 'fw-staff' },
        h('div', { className: 'fw-staff__now' }, h('span', { className: 'fw-staff__ic' }, ico('cube')), h('div', null, h('b', null, cur.name), h('span', null, cur.line), more ? h('span', { className: 'fw-staff__more' }, more) : null),
          h('small', null, K.pad2(k + 1) + ' / ' + c.staff.length)),
        h('ul', { className: 'fw-staff__list' }, c.staff.map(function (s, n) {
          return h('li', { key: s.name }, h('button', { type: 'button', className: 'fw-chip' + (n === k ? ' is-on' : sel == null && n < k ? ' is-past' : ''), 'aria-pressed': n === k ? 'true' : 'false', onClick: function () { st[1](n); } }, s.name));
        })),
        h('p', { className: 'fw-label' }, W.staffHint || ''), h('p', { className: 'fw-aside' }, c.more));
    }

    function Ask(p) {
      var b = p.b, c = b.copy;
      return h('div', { className: 'fw-ask' },
        h(Locator, { b: b, i: p.i, q: p.q, size: 'sm', submitted: p.submitted, label: p.submitted ? 'Your window, lit.' : 'The one window that stays dark is yours.' }),
        h(K.Watch, { M: M, copy: c }),
        h('p', { className: 'fw-lede' }, c.briefing),
        h(K.Ask, { id: 'ask-email-flow', copy: c, submitted: p.submitted, onSubmit: p.onSubmit }));
    }

    /* ---------- a section ---------- */
    // The sections whose exhibit plays through a timeline pin (when the whole stage fits); the static ones just flow.
    var PIN = { bus: 1, 'runs-on-itself': 1, pjangler: 1, flume: 1, 'pm-krebs': 1, harvest: 1, skillex: 1, gateway: 1, heyma: 1, wax: 1, speakers: 1, jev: 1, 'holocene-auto': 1, staff: 1 };
    var FIG_BEATS = { numbers: Figures, 'org-chart': Org, bus: Bus, 'runs-on-itself': Loop, 'clock-records': Dept, 'agents-desk': Dept, pjangler: Pjangler, flume: Flume, 'pm-krebs': Krebs,
      wax: Transcript, speakers: Transcript, jev: Transcript, harvest: Transcript, gateway: Gateway, heyma: HeyMa, 'holocene-auto': Car, staff: Staff, ask: Ask };

    function Piece(p) {
      var b = p.b, C = FIG_BEATS[b.id];
      if (C) return h(C, p);
      // thesis, skillex: the building is the exhibit
      var seat = b.id === 'skillex' ? K.seats.named.SKILLEX : null;
      return h('div', { className: 'fw-stand' }, h(Locator, { b: b, i: p.i, q: p.q, size: b.id === 'thesis' ? 'md' : 'md' }),
        seat && seat.line ? h('div', { className: 'fw-plate' }, h(O.Nameplate, { name: seat.name, line: seat.line, state: SC.minor('skillex', 'ship', p.q).beat < 1 ? 'working' : SC.minor('skillex', 'ship', p.q).beat < 2 ? 'shipped' : 'lit' })) : null);
    }

    function Source(p) {
      var b = p.b, c = b.copy || {};
      var notes = [c.stamp, c.tapeNote, c.cardNote, c.partsNote, c.stamp && c.stamp].filter(function (x, k, a) { return x && a.indexOf(x) === k; });
      return h(Disclosure, { label: W.source || 'Source and events', cls: 'fw-more--src' },
        notes.map(function (n, k) { return h('p', { key: k, className: 'fw-note' }, n); }),
        (b.log || []).map(function (l, k) {
          return h('div', { key: k, className: 'fw-evt' }, h(Subject, { text: l.subject }), l.note ? h('p', null, l.note) : null);
        }));
    }

    function Section(p) {
      var b = p.b, i = p.i, c = b.copy || {};
      var st = useState(flat ? STEPS : 0), step = st[0], q = Math.min(1, step / STEPS);
      useLayoutEffect(function () { p.reg[i] = st[1]; return function () { delete p.reg[i]; }; }, []);
      var badge = b.staged ? site.stagedLabel : (c.figures || c.stamp) && b.id !== 'bus' ? K.fmtTemplate(site.realLabel, { date: site.countedOn }) : '';
      var tp = titleParts(b.title), parts = leadOf(b.body, 150), asideLong = c.aside && c.aside.length > 90;
      var rest = parts[1], hasMore = rest || c.aside;
      var morning = b.id === 'holocene-auto';
      return h('section', { id: b.id, className: 'fw-s fw-s--' + b.id, 'data-i': i, 'data-acc': accOf(b), 'data-pin': PIN[b.id] ? '1' : null, 'data-theme': morning ? 'morning' : null, 'aria-labelledby': 'fw-h-' + b.id },
        h('div', { className: 'fw-stage' }, h('div', { className: 'fw-in' },
          h('header', { className: 'fw-head' },
            h('span', { className: 'fw-ic' }, ico(BEAT_ICON[b.id] || 'cube')),
            h('span', { className: 'fw-meta' }, h('span', { className: 'fw-n' }, K.pad2(i + 1) + ' · ' + b.where.trim()), badge ? h('span', { className: 'fw-pill' + (b.staged ? '' : ' fw-pill--real') }, badge) : null),
            h(Locator, { b: b, i: i, q: q, size: 'xs', submitted: p.submitted })),
          h('div', { className: 'fw-copy' },
            b.kicker ? h('p', { className: 'fw-kicker' }, b.kicker) : null,
            h('h2', { id: 'fw-h-' + b.id, className: 'fw-title' }, tp[0], tp[1] ? [' ', h('em', { key: 'e' }, tp[1])] : null),
            parts[0] ? h('p', { className: 'fw-lede' }, parts[0]) : null,
            hasMore ? h(Disclosure, { label: W.more || 'More', cls: 'fw-more--text' }, rest ? h('p', null, rest) : null, c.aside ? h('p', { className: 'fw-aside' }, c.aside) : null) : null),
          h('div', { className: 'fw-piece' }, h(Piece, { b: b, i: i, q: q, submitted: p.submitted, onSubmit: p.onSubmit })),
          b.tags && b.tags.length ? h('ul', { className: 'fw-tags', 'aria-label': 'Components' }, b.tags.map(function (t) { return h('li', { key: t }, t); })) : null,
          h(Source, { b: b }))));
    }

    function PartBand(p) {
      var b = p.b;
      return h('div', { className: 'fw-part-band', 'data-acc': ACT_ACC[b.act] },
        h('span', { className: 'fw-part-band__ic' }, ico(ACT_ICON[b.act] || 'cube')),
        h('div', null, h('p', { className: 'fw-part-band__k' }, 'Part ' + b.act + ' · ' + M.acts[b.act]), h('p', { className: 'fw-part-band__l' }, b.interlude.line)));
    }

    function Hero(p) {
      var b = beats[0], c = b.copy, tp = [b.title, b.titleTurn];
      var ws = useState(flat ? 1 : 0), wake = ws[0];
      useEffect(function () {
        if (flat) return;
        var t0 = performance.now(), raf = 0;
        function tick(now) { var t = Math.min(1, (now - t0) / 1800); ws[1](t); if (t < 1) raf = requestAnimationFrame(tick); }
        raf = requestAnimationFrame(tick);
        return function () { cancelAnimationFrame(raf); };
      }, []);
      var stepSt = useState(flat ? STEPS : 0); var sq = stepSt[0] / STEPS;
      useLayoutEffect(function () { p.reg[0] = stepSt[1]; return function () { delete p.reg[0]; }; }, []);
      var q = Math.max(wake, sq);
      return h('section', { id: 'premise', className: 'fw-s fw-hero', 'data-i': 0, 'data-acc': 'arrival', 'aria-labelledby': 'fw-h-premise' },
        h('div', { className: 'fw-hero__in' },
          h('div', { className: 'fw-hero__copy' },
            h('p', { className: 'fw-hero__kicker' }, b.kicker),
            h('h1', { id: 'fw-h-premise' }, tp[0], ' ', h('em', null, tp[1])),
            h('p', { className: 'fw-lede' }, leadOf(b.body, 170)[0]),
            h('div', { className: 'fw-hero__cta' },
              h('a', { className: 'fw-btn', href: '#ask', onClick: function (e) { e.preventDefault(); p.go('ask', false, true); } }, ico('mail'), site.cta),
              h('a', { className: 'fw-textlink', href: K.hrefOf(M, c.secondaryHref), target: '_blank', rel: 'noopener' }, c.secondary, ico('right')))),
          h('div', { className: 'fw-hero__art' }, h(Locator, { b: b, i: 0, q: q, size: 'hero' })),
          leadOf(b.body, 170)[1] ? h(Disclosure, { label: W.more || 'More', cls: 'fw-more--text' }, h('p', null, leadOf(b.body, 170)[1])) : null,
          h(Source, { b: b })));
    }

    /* ---------- header, footer ---------- */
    function Header(p) {
      var navs = site.nav;
      return h('header', { className: 'fw-hdr', id: 'fw-hdr' },
        h('div', { className: 'fw-hdr__in' },
          h('a', { className: 'fw-brand', href: 'index.html', 'aria-label': W.home || site.name, title: W.home || site.name }, h(K.Mark, { size: 22 }), h('b', null, site.name)),
          h('nav', { className: 'fw-nav', id: 'fw-nav', 'aria-label': 'The tour' }, navs.map(function (n) {
            var tb = beats[I[n.beat]];
            return h('a', { key: n.beat, href: '#' + n.beat, 'data-beat': n.beat, 'data-acc': accOf(tb), 'aria-label': n.label, title: n.label,
              onClick: function (e) { e.preventDefault(); p.go(n.beat); } }, ico(NAV_ICON[n.beat] || 'cube'), h('span', { className: 'fw-nav__l' }, n.label));
          })),
          h('a', { className: 'fw-cta', href: '#ask', 'aria-label': site.cta, onClick: function (e) { e.preventDefault(); p.go('ask', false, true); } }, ico('mail'), h('span', null, F.ctaShort || site.cta))),
        h('div', { className: 'fw-prog', 'aria-hidden': 'true' }, Object.keys(M.acts).map(function (a) { return h('i', { key: a, 'data-acc': ACT_ACC[a], 'data-act': a }); })));
    }

    function Footer(p) {
      var f = site.footer;
      return h('footer', { className: 'fw-foot' },
        h('span', { className: 'fw-foot__brand' }, h(K.Mark, { size: 20 }), h('b', null, site.name)),
        h('span', { className: 'fw-foot__by' }, f.byline, ' · ', h('a', { href: f.link.href }, f.link.label)),
        h('nav', { className: 'fw-foot__nav', 'aria-label': 'More' },
          h('a', { href: 'index.html' }, W.front || 'The front page', ico('right')),
          h('button', { type: 'button', onClick: p.toList }, site.viewLog, ico('right')),
          site.viewSimulationHref ? h('a', { href: site.viewSimulationHref, target: '_blank', rel: 'noopener' }, site.viewSimulation, ico('right')) : null),
        h('span', { className: 'fw-foot__c' }, f.colophon));
    }

    /* ---------- the view: layout, pinning, and the scroll that drives every exhibit ---------- */
    function FlowView(props) {
      var rootRef = useRef(null), reg = useRef({}).current;
      var hdrRef = useRef(null);

      // go(id): the section's head just under the header. go('ask', false, true): the briefing form itself, the thing the CTAs are for.
      function go(id, instant, toForm) {
        var el = document.getElementById(id); if (!el) return;
        var hd = hdrRef.current ? hdrRef.current.offsetHeight : 56;
        var form = toForm ? el.querySelector('.gate') : null;
        var y = (form || el).getBoundingClientRect().top + window.scrollY - hd - (form ? 24 : 0);
        window.scrollTo({ top: Math.max(0, y), behavior: flat || instant ? 'auto' : 'smooth' });
        try { history.replaceState(null, '', location.pathname + location.search + '#' + id); } catch (e) { /* no history */ }
      }

      useLayoutEffect(function () {
        var root = rootRef.current, doc = document.documentElement;
        doc.classList.add('fw-on');
        var oldSkip = document.querySelector('body > a.skip'); if (oldSkip) oldSkip.hidden = true;   // the static link points at the list view, which is not on the page
        if (flat) doc.classList.add('fw-flat');
        var secs = [].slice.call(root.querySelectorAll('.fw-s')), hdr = root.querySelector('.fw-hdr');
        hdrRef.current = hdr;
        var navs = [].slice.call(root.querySelectorAll('.fw-nav a')), bars = [].slice.call(root.querySelectorAll('.fw-prog i')), navEl = root.querySelector('.fw-nav');
        var probe = document.createElement('div');
        probe.setAttribute('aria-hidden', 'true');
        probe.style.cssText = 'position:fixed;left:0;top:0;width:0;height:100svh;visibility:hidden;pointer-events:none';
        document.body.appendChild(probe);
        var raf = 0, lastActive = -2, lastKey = '', lastHash = '';
        function svh() { var v = probe.offsetHeight; return v > 0 ? v : window.innerHeight; }
        function hdrH() { return hdr ? hdr.offsetHeight : 56; }

        // Pin a section only if its whole stage fits the visible height. Measured unpinned, so the answer never depends on being pinned.
        function measure() {
          var avail = svh() - hdrH();
          secs.forEach(function (s) {
            s.classList.remove('is-pinned');
            if (flat || !s.dataset.pin) return;
            var need = s.firstElementChild.getBoundingClientRect().height;
            s.dataset.need = Math.round(need);
            if (need <= avail + 0.5) s.classList.add('is-pinned');
          });
          doc.style.setProperty('--avail', avail + 'px');
          lastKey = window.innerWidth + 'x' + avail;
          req();
        }
        function req() { if (!raf) raf = requestAnimationFrame(frame); }
        function frame() {
          raf = 0;
          var vh = window.innerHeight, hd = hdrH(), mid = hd + (vh - hd) * 0.5, active = -1, actFrac = {};
          secs.forEach(function (s, k) {
            var rect = s.getBoundingClientRect(), p = 1;
            if (!flat) {
              if (s.classList.contains('is-pinned')) {
                var run = s.offsetHeight - s.firstElementChild.offsetHeight;
                p = run > 0 ? clamp((hd - rect.top) / run, 0, 1) : 0;
              } else {
                var pc = s.querySelector('.fw-piece, .fw-hero__art') || s, pr = pc.getBoundingClientRect();
                var vc = pr.top + Math.min(pr.height, (vh - hd) * 0.6) / 2, a = vh * 0.85, b = hd + (vh - hd) * 0.45;
                p = clamp((a - vc) / (a - b), 0, 1);
              }
            }
            var key = p.toFixed(3);
            if (s._p !== key) { s._p = key; s.style.setProperty('--q', key); }
            var step = Math.round(p * STEPS);
            if (s._step !== step) { s._step = step; if (reg[k]) reg[k](step); }
            if (rect.top <= mid && rect.bottom > mid) active = k;
            var act = s.dataset.i != null ? beats[+s.dataset.i].act : 'I';
            var f = rect.top > mid ? 0 : rect.bottom < mid ? 1 : clamp((mid - rect.top) / Math.max(1, rect.height), 0, 1);
            (actFrac[act] = actFrac[act] || []).push(f);
          });
          bars.forEach(function (bar) { var fs = actFrac[bar.dataset.act] || [0]; bar.style.setProperty('--f', (fs.reduce(function (x, y) { return x + y; }, 0) / fs.length).toFixed(3)); });
          if (active !== lastActive) {
            lastActive = active;
            // the nav item that names the last section at or before this one
            var cur = -1;
            navs.forEach(function (a, n) { var bi = I[a.dataset.beat]; if (active >= 0 && bi <= active) cur = n; });
            navs.forEach(function (a, n) { if (n === cur) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current'); });
            var curA = navs[cur];
            if (curA && navEl && navEl.scrollWidth > navEl.clientWidth + 1) {
              var to = curA.offsetLeft - (navEl.clientWidth - curA.offsetWidth) / 2;
              try { navEl.scrollTo({ left: to, behavior: flat ? 'auto' : 'smooth' }); } catch (e) { navEl.scrollLeft = to; }
            }
            var id = active > 0 ? beats[active].id : '';
            if (id !== lastHash) { lastHash = id; try { history.replaceState(null, '', location.pathname + location.search + (id ? '#' + id : '')); } catch (e) { /* no history */ } }
          }
          try { sessionStorage.setItem('flow.y', String(Math.round(window.scrollY))); } catch (e) { /* private window */ }
        }
        function onResize() { var avail = svh() - hdrH(); if (window.innerWidth + 'x' + avail !== lastKey) measure(); else req(); }
        // A disclosure opening can make a pinned stage too tall: measure again (toggle does not bubble, so capture it).
        function onToggle() { measure(); }
        window.addEventListener('scroll', req, { passive: true });
        window.addEventListener('resize', onResize);
        window.addEventListener('orientationchange', function () { setTimeout(measure, 250); });
        root.addEventListener('toggle', onToggle, true);
        if (document.fonts && document.fonts.ready) document.fonts.ready.then(measure);
        try { if ('scrollRestoration' in history) history.scrollRestoration = 'manual'; } catch (e) { /* ignore */ }
        measure();
        // Come back to the place the URL names, else (on a reload) the place this tab was.
        var want = ''; try { want = decodeURIComponent(location.hash.slice(1)); } catch (e) { want = ''; }
        var nt = ''; try { nt = (performance.getEntriesByType('navigation')[0] || {}).type || ''; } catch (e) { nt = ''; }
        var savedY = 0; try { savedY = +sessionStorage.getItem('flow.y') || 0; } catch (e) { savedY = 0; }
        if ((nt === 'reload' || nt === 'back_forward') && savedY) window.scrollTo(0, savedY);   // this tab's exact place beats the hash it wrote
        else if (want && document.getElementById(want)) go(want, true);
        root.dataset.ready = '1';
        req();
        return function () {
          doc.classList.remove('fw-on', 'fw-flat'); if (oldSkip) oldSkip.hidden = false;
          window.removeEventListener('scroll', req); window.removeEventListener('resize', onResize);
          root.removeEventListener('toggle', onToggle, true);
          cancelAnimationFrame(raf); if (probe.parentNode) probe.parentNode.removeChild(probe);
        };
      }, []);

      var out = [];
      beats.forEach(function (b, i) {
        if (i === 0) { out.push(h(Hero, { key: b.id, reg: reg, go: go })); return; }
        if (b.interlude) out.push(h(PartBand, { key: 'part-' + b.act, b: b }));
        out.push(h(Section, { key: b.id, b: b, i: i, reg: reg, submitted: props.submitted, onSubmit: props.onSubmit }));
      });
      return h('div', { className: 'fw', ref: rootRef },
        h('a', { className: 'skip', href: '#fw-main' }, W.skip || 'Skip to the tour'),
        h(Header, { go: go }),
        h('main', { id: 'fw-main' }, out),
        h(Footer, { toList: props.toList }));
    }

    return { FlowView: FlowView };
  }
})();
