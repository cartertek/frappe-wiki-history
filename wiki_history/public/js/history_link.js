/* The only integration with Wiki's SPA. All history screens belong to wiki_history. */
(() => {
  const ID = 'wiki-history-page-link';
  const pagePattern = /^\/wiki-app\/spaces\/([^/]+)\/page\/([^/]+)\/?$/;
  const findActions = () => {
    const button = document.querySelector('#app button[aria-label="Page actions"]')
      || document.querySelector('#app button[title="Page actions"]')
      || document.querySelector('#app button[aria-label="Page settings"]');
    if (!button) return null;
    // WikiDocumentPanel's page-action row is the common ancestor of all actions.
    return button.closest('div.flex.shrink-0.items-center.gap-2') || button.parentElement;
  };
  function update() {
    const match = location.pathname.match(pagePattern);
    const existing = document.getElementById(ID);
    if (!match) { existing?.remove(); return; }
    const actions = findActions();
    if (!actions) { existing?.remove(); return; }

    const href = '/wiki-history?space=' + encodeURIComponent(match[1])
      + '&page=' + encodeURIComponent(match[2]);
    const link = existing || document.createElement('a');
    if (!existing) {
      link.id = ID;
      link.textContent = 'History';
      link.setAttribute('aria-label', 'View page revision history');
      link.title = 'View page revision history';
      link.style.cssText = 'display:inline-flex;align-items:center;justify-content:center;'
        + 'white-space:nowrap;padding:6px 9px;border-radius:6px;'
        + 'font-size:13px;font-weight:500;color:inherit;';
    }
    if (link.getAttribute('href') !== href) link.href = href;
    if (link.parentElement !== actions) actions.prepend(link);
  }
  let queued = false;
  function schedule() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => { queued = false; update(); });
  }
  // Vue's router uses pushState, which doesn't fire popstate. Observe the
  // actual page-action subtree to catch both initial render and client routing.
  const observer = new MutationObserver(schedule);
  observer.observe(document.getElementById('app') || document.body,
    { childList: true, subtree: true });
  window.addEventListener('popstate', schedule);
  window.addEventListener('hashchange', schedule);
  schedule();
})();
