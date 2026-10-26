/* Read-only Wikipedia-inspired history UI. Never inserts server content as HTML. */
(() => {
  const $ = id => document.getElementById(id);
  const q = new URLSearchParams(location.search);
  const space = q.get('space') || '';
  const page = q.get('page') || '';
  let rows = [];
  let selectedOld = null;
  let selectedNew = null;
  let nextOffset = null;
  let total = 0;

  function status(message, error = false) {
    $('notice').textContent = message;
    $('notice').classList.toggle('error', error);
    $('notice').hidden = !message;
  }
  async function api(method, params) {
    const url = '/api/method/wiki_history.api.' + method + '?'
      + new URLSearchParams(params).toString();
    const response = await fetch(url, { credentials: 'same-origin', headers: { Accept:'application/json' } });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.exc) {
      throw Error(payload.message && typeof payload.message === 'string'
        ? payload.message : 'Could not load Wiki history (' + response.status + ')');
    }
    return payload.message;
  }
  function el(tag, css, text) {
    const node = document.createElement(tag);
    if (css) node.className = css;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }
  function append(parent, tag, css, text) {
    const node = el(tag, css, text);
    parent.appendChild(node);
    return node;
  }
  function label(row) {
    return row.date + (row.author ? ' · ' + row.author : '');
  }
  function renderRows() {
    const table = $('revision-rows');
    table.replaceChildren();
    for (const row of rows) {
      const tr = append(table, 'tr');
      for (const [group, selected, setter] of [
        ['old', selectedOld, value => selectedOld = value],
        ['new', selectedNew, value => selectedNew = value],
      ]) {
        const cell = append(tr, 'td');
        const input = append(cell, 'input');
        input.type = 'radio';
        input.name = group;
        input.value = row.revision;
        input.checked = selected === row.revision;
        input.setAttribute('aria-label', group + ' version ' + label(row));
        input.addEventListener('change', () => { setter(row.revision); renderRows(); });
      }
      const revisionCell = append(tr, 'td');
      append(revisionCell, 'span', 'rev-date', row.date || 'Unknown date');
      append(revisionCell, 'span', 'small', row.author || 'Unknown author');
      const links = append(revisionCell, 'span', 'rev-links');
      const view = append(links, 'a', '', 'View');
      view.href = '#revision=' + encodeURIComponent(row.revision);
      view.addEventListener('click', event => {
        event.preventDefault(); showRevision(row.revision);
      });
      const prev = append(links, 'a', '', 'prev');
      prev.href = '#compare=' + encodeURIComponent(row.parent_revision || 'initial') + ':' + encodeURIComponent(row.revision);
      prev.addEventListener('click', event => {
        event.preventDefault(); compare(row.parent_revision || '', row.revision);
      });
      const description = append(tr, 'td');
      append(description, 'span', 'kind', row.kind || 'edited');
      append(description, 'span', 'rev-comment', row.message || 'No edit summary');
      append(description, 'span', 'small', (row.fields || []).map(s => s === 'content_blob' ? 'content' : s).join(', '));
    }
    $('compare-selected').disabled = !selectedOld || !selectedNew || selectedOld === selectedNew;
    $('load-more').hidden = nextOffset === null;
    $('count').textContent = rows.length + ' of ' + total + ' page-changing revisions';
  }
  async function loadMore() {
    status('Loading history…');
    try {
      const pageData = await api('get_page_history', {
        space, page, offset: nextOffset === null ? 0 : nextOffset, limit: 30,
      });
      $('page-title').textContent = pageData.page.title || pageData.page.doc_key;
      $('back').href = '/wiki-app/spaces/' + encodeURIComponent(space)
        + '/page/' + encodeURIComponent(pageData.page.name || page);
      nextOffset = pageData.next_offset;
      total = pageData.total;
      rows.push(...pageData.rows);
      if (!selectedNew && rows.length) selectedNew = rows[0].revision;
      if (!selectedOld && rows.length > 1) selectedOld = rows[1].revision;
      $('history-section').hidden = false;
      renderRows();
      status(total === 0 ? 'No saved revisions changed this page.' : '');
    } catch (error) { status(error.message, true); }
  }
  function section(title, heading, text) {
    $(title).textContent = heading;
    $(text).textContent = '';
  }
  async function showRevision(revision) {
    status('Loading revision…');
    try {
      const data = await api('get_page_revision', { space, page, revision });
      $('detail').hidden = false;
      $('detail-title').textContent = 'Saved revision ' + revision;
      $('detail-subtitle').textContent = [data.date, data.author, data.message].filter(Boolean).join(' · ');
      $('snapshot').textContent = data.content || '';
      $('snapshot-view').hidden = false;
      $('diff-view').hidden = true;
      $('metadata').hidden = true;
      status('');
      $('detail').scrollIntoView({ behavior: 'smooth', block:'start' });
    } catch (error) { status(error.message, true); }
  }
  async function compare(oldRevision, newRevision) {
    status('Comparing revisions…');
    try {
      const data = await api('compare_page_revisions', {
        space, page, old: oldRevision || '', new: newRevision,
      });
      $('detail').hidden = false;
      $('detail-title').textContent = 'Comparison: ' + (oldRevision || 'page creation') + ' → ' + newRevision;
      $('detail-subtitle').textContent = data.truncated
        ? 'Diff is truncated; large page exceeds the maximum displayed lines.' : '';
      $('snapshot-view').hidden = true;
      const metadata = $('metadata-rows');
      metadata.replaceChildren();
      for (const change of data.metadata_changes) {
        const item = append(metadata, 'div', 'property');
        append(item, 'strong', '', change.field.replaceAll('_',' '));
        append(item, 'span', 'old', JSON.stringify(change.old ?? '—'));
        append(item, 'span', 'new', JSON.stringify(change.new ?? '—'));
      }
      $('metadata').hidden = data.metadata_changes.length === 0;
      const target = $('diff-rows');
      target.replaceChildren();
      for (const line of data.lines) {
        const tr = append(target, 'tr', line.kind);
        if (line.kind === 'separator') {
          const gap = append(tr, 'td');
          gap.colSpan = 3;
          continue;
        }
        append(tr, 'td', 'num', line.old ?? '');
        append(tr, 'td', 'num', line.new ?? '');
        append(tr, 'td', 'text', (line.kind === 'add' ? '+ ' : line.kind === 'remove' ? '− ' : '  ') + line.text);
      }
      $('diff-view').hidden = false;
      status('');
      $('detail').scrollIntoView({ behavior:'smooth', block:'start' });
    } catch (error) { status(error.message, true); }
  }

  $('compare-selected').addEventListener('click', () => {
    if (selectedNew && selectedOld && selectedNew !== selectedOld) compare(selectedOld, selectedNew);
  });
  $('load-more').addEventListener('click', loadMore);
  $('close-detail').addEventListener('click', () => { $('detail').hidden = true; });
  if (!space || !page) status('Missing page or Wiki Space identifier in the URL.', true);
  else loadMore();
})();
