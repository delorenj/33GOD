/* @ds-bundle: {"format":4,"namespace":"Overnight","components":[{"name":"Window"},{"name":"Building"},{"name":"Clock"},{"name":"Nameplate"},{"name":"Caption"},{"name":"LogLine"}]} */
(function () {
  'use strict';
  var React = window.React;
  var h = React.createElement;

  var WINDOW_STATES = ['dark', 'lit', 'working', 'shipped', 'overtime', 'broken', 'you'];
  var STATE_WORDS = { dark: 'Dark', lit: 'Lit', working: 'Working', shipped: 'Shipped', overtime: 'Overtime', broken: 'Broken', you: 'Yours' };

  function cx() {
    return Array.prototype.filter.call(arguments, Boolean).join(' ');
  }
  function stateOf(s) {
    return WINDOW_STATES.indexOf(s) >= 0 ? s : 'dark';
  }

  function Window(props) {
    var state = stateOf(props.state);
    return h('span', {
      className: cx('on-window', 'on-window--' + state, props.size === 'lg' && 'on-window--lg', props.className),
      role: 'img',
      'aria-label': props.label || STATE_WORDS[state] + ' window',
      title: props.title
    });
  }

  // A deterministic pattern, so a building lights the same way on every render.
  function patternState(i, perFloor, lit, working) {
    var r = (i * 37 + Math.floor(i / perFloor) * 13 + (i % perFloor) * Math.floor(i / perFloor) * 7) % 100;
    if (r < working * 100) return 'working';
    if (r < (working + lit) * 100) return 'lit';
    return 'dark';
  }

  function Building(props) {
    var floors = props.floors || 6;
    var perFloor = props.perFloor || 8;
    var states = props.states || null;
    var lit = props.lit == null ? 0.6 : props.lit;
    var working = props.working == null ? 0 : props.working;
    var cells = [];
    for (var i = 0; i < floors * perFloor; i++) {
      var s = props.you === i ? 'you' : states ? (states[i] || 'dark') : patternState(i, perFloor, lit, working);
      if (props.you === i && props.youLit === false) s = 'dark';
      cells.push(h(Window, { key: i, state: s, size: props.size }));
    }
    return h('div', {
      className: cx('on-building', props.size === 'lg' && 'on-building--lg', props.className),
      role: 'img',
      'aria-label': props.label || 'A building of ' + floors + ' floors at night',
      style: { gridTemplateColumns: 'repeat(' + perFloor + ', auto)' }
    }, cells);
  }

  function Clock(props) {
    var time = props.time || '18:02';
    return h('div', { className: cx('on-clock', props.className) },
      h('time', { className: 'on-clock__time', 'aria-label': props.label || 'The clock reads ' + time },
        time,
        props.precise ? h('span', { className: 'on-clock__ms' }, ':' + props.precise) : null),
      props.staged ? h('span', { className: 'on-clock__staged' }, props.stagedLabel || 'A night, staged') : null);
  }

  function Nameplate(props) {
    var state = props.state ? stateOf(props.state) : null;
    return h('div', { className: cx('on-nameplate', props.className) },
      h('span', { className: 'on-nameplate__name' }, props.name),
      props.line ? h('span', { className: 'on-nameplate__line' }, props.line) : null,
      state ? h('span', { className: 'on-nameplate__state' }, h(Window, { state: state }), STATE_WORDS[state]) : null);
  }

  function Caption(props) {
    var beat = props.beat || props;
    var tags = beat.tags || [];
    return h('div', { className: cx('on-caption', props.align === 'center' && 'on-caption--center', props.className) },
      beat.kicker ? h('p', { className: 'on-caption__kicker' }, beat.kicker) : null,
      beat.title ? h(props.as || 'h3', { className: 'on-caption__title' }, beat.title) : null,
      beat.body ? h('p', { className: 'on-caption__body' }, beat.body) : null,
      tags.length ? h('p', { className: 'on-caption__tags' }, tags.join(' · ')) : null);
  }

  function LogLine(props) {
    return h('div', { className: cx('on-log', props.className) },
      h('span', { className: 'on-log__time' }, props.time),
      h('span', { className: 'on-log__subject' }, props.subject),
      props.note ? h('span', { className: 'on-log__note' }, props.note) : null);
  }

  window.Overnight = {
    Window: Window,
    Building: Building,
    Clock: Clock,
    Nameplate: Nameplate,
    Caption: Caption,
    LogLine: LogLine,
    WINDOW_STATES: WINDOW_STATES
  };
})();
