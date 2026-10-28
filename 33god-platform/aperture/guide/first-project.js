/* Static reading, clipboard, checklist and mascot enhancements; never executes shell commands. */
(() => {
  'use strict';
  document.documentElement.classList.add('js');
  const slides = [...document.querySelectorAll('.slide')];
  const current = document.querySelector('#current-step');
  const progress = document.querySelector('#reading-meter');
  const next = document.querySelector('#next-step');
  const chapterLinks = [...document.querySelectorAll('.rail nav a')];
  const topbar = document.querySelector('.topbar');
  function measureHeader() {
    document.documentElement.style.setProperty('--header-actual', `${Math.ceil(topbar.getBoundingClientRect().height)}px`);
  }
  measureHeader();
  if ('ResizeObserver' in window) new ResizeObserver(measureHeader).observe(topbar);
  else window.addEventListener('resize', measureHeader);
  // Hash positioning may run before the measured header exists, or before fonts settle.
  window.addEventListener('load', () => {
    measureHeader();
    if (location.hash) document.getElementById(decodeURIComponent(location.hash.slice(1)))?.scrollIntoView();
  }, { once:true });
  function updateProgress() {
    const threshold = Math.min(window.innerHeight * .36, 300);
    let index = 0;
    slides.forEach((slide, i) => { if (slide.getBoundingClientRect().top <= threshold) index = i; });
    current.textContent = String(index + 1).padStart(2, '0');
    progress.value = index + 1;
    next.href = '#' + slides[Math.min(index + 1, slides.length - 1)].id;
    next.textContent = index === slides.length - 1 ? 'Back to start ↑' : 'Next step →';
    if (index === slides.length - 1) next.href = '#start';
    const phase = slides[index].dataset.phase;
    chapterLinks.forEach(link => {
      if (link.dataset.phase === phase) link.setAttribute('aria-current', 'step');
      else link.removeAttribute('aria-current');
    });
  }
  let pending = false;
  window.addEventListener('scroll', () => {
    if (pending) return;
    pending = true;
    requestAnimationFrame(() => { updateProgress(); pending = false; });
  }, { passive:true });
  window.addEventListener('resize', updateProgress);
  updateProgress();
  document.querySelectorAll('[data-copy]').forEach(button => {
    button.addEventListener('click', async () => {
      const code = document.getElementById(button.dataset.copy);
      const feedback = document.getElementById(button.getAttribute('aria-describedby'));
      try {
        if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
        await navigator.clipboard.writeText(code.textContent);
        feedback.textContent = 'Copied. Paste into Terminal with Command + V, then press Return.';
        button.textContent = 'Copied';
      } catch {
        const range = document.createRange();
        range.selectNodeContents(code);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        feedback.textContent = 'Copy was blocked. The command is selected: press Command + C to copy it manually.';
        button.textContent = 'Copy command';
      }
    });
  });
  const antics = document.querySelector('#pause-antics');
  const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
  let anticsPaused = false;
  function refreshAnticsControl() {
    const paused = anticsPaused || motionQuery.matches;
    document.documentElement.classList.toggle('antics-paused', paused);
    antics.setAttribute('aria-pressed', String(paused));
    antics.textContent = motionQuery.matches ? 'Antics: reduced motion' : (paused ? 'Resume antics' : 'Pause antics');
    antics.disabled = motionQuery.matches;
  }
  antics.addEventListener('click', () => { anticsPaused = !anticsPaused; refreshAnticsControl(); });
  motionQuery.addEventListener('change', refreshAnticsControl);
  refreshAnticsControl();
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => entry.target.classList.toggle('in-view', entry.isIntersecting && entry.intersectionRatio >= .3));
    }, { threshold:[0,.3,.75] });
    document.querySelectorAll('.mascot').forEach(stage => observer.observe(stage));
  }
  const approval = document.querySelector('#upgrade-approved');
  const upgradeCopy = document.querySelector('[data-copy="cmd-upgrade"]');
  approval.addEventListener('change', () => { upgradeCopy.disabled = !approval.checked; });
  document.querySelectorAll('[data-achievement]').forEach(input => {
    const key = '33god-first-project-v1-' + input.dataset.achievement;
    try { input.checked = localStorage.getItem(key) === 'true'; } catch { /* The checklist remains usable without storage. */ }
    input.addEventListener('change', () => { try { localStorage.setItem(key, String(input.checked)); } catch { /* No persistence guarantee. */ } });
  });
})();
