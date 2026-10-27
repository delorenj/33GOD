(() => {
  document.documentElement.classList.add('js');
  const stages = {
    source: ['Start at the source.', 'The file belongs to the project; the directory points to it.'],
    index: ['Make it findable.', 'PJangler registers the known file location and refreshes its indexed facts.'],
    use: ['Look it up.', 'Commands and connected tools can find the same project identity.']
  };
  const buttons = document.querySelectorAll('[data-show]');
  const panels = document.querySelectorAll('[data-stage]');
  const title = document.getElementById('stage-title');
  const description = document.getElementById('stage-description');
  if (buttons.length && title && description) {
    function show(stage) {
      if (!Object.prototype.hasOwnProperty.call(stages, stage)) return;
      buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.show === stage)));
      panels.forEach(panel => panel.classList.toggle('is-active', panel.dataset.stage === stage));
      [title.textContent, description.textContent] = stages[stage];
    }
    buttons.forEach(button => button.addEventListener('click', () => show(button.dataset.show)));
    show('source');
  }
  const feedback = document.getElementById('copy-feedback');
  document.querySelectorAll('[data-copy]').forEach(button => {
    button.addEventListener('click', async () => {
      const command = button.dataset.copy;
      try {
        if (!navigator.clipboard || !window.isSecureContext) throw new Error('Clipboard unavailable');
        await navigator.clipboard.writeText(command);
        if (feedback) feedback.textContent = `Copied “${command}”. This page did not run it.`;
      } catch (_) {
        if (feedback) feedback.textContent = `Copy unavailable here. Select the command text manually; nothing was run.`;
      }
    });
  });
})();
