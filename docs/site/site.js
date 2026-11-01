'use strict';
document.documentElement.classList.add('js');
const zh = document.documentElement.lang.startsWith('zh');
const toggle = document.getElementById('nav-toggle');
const nav = document.getElementById('doc-nav');
toggle?.addEventListener('click', () => {
  const expanded = toggle.getAttribute('aria-expanded') !== 'true';
  toggle.setAttribute('aria-expanded', String(expanded));
  nav.classList.toggle('is-open', expanded);
});
const filter = document.getElementById('skill-filter');
if (filter) {
  const entries = [...document.querySelectorAll('[data-skill]')];
  filter.addEventListener('input', () => {
    const terms = filter.value.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
    let visible = 0;
    for (const entry of entries) {
      entry.hidden = !terms.every(term => entry.dataset.skill.toLocaleLowerCase().includes(term));
      if (!entry.hidden) visible++;
    }
    for (const group of document.querySelectorAll('.skill-group')) {
      group.hidden = ![...group.querySelectorAll('[data-skill]')].some(entry => !entry.hidden);
    }
    document.getElementById('filter-count').textContent = `${visible} / ${entries.length} ${zh ? '个技能' : 'skills'}`;
    document.getElementById('filter-empty').hidden = visible !== 0;
  });
}
if (navigator.clipboard?.writeText) {
  for (const pre of document.querySelectorAll('pre')) {
    const code = pre.querySelector('code');
    if (!code) continue;
    const button = document.createElement('button');
    button.className = 'copy-code';
    button.type = 'button';
    button.textContent = zh ? '复制' : 'Copy';
    button.setAttribute('aria-label', zh ? '复制代码' : 'Copy code');
    button.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(code.textContent);
        button.textContent = zh ? '已复制' : 'Copied';
      } catch {
        button.textContent = zh ? '请手动选择复制' : 'Select and copy';
      }
      setTimeout(() => { button.textContent = zh ? '复制' : 'Copy'; }, 2000);
    });
    pre.append(button);
  }
}
