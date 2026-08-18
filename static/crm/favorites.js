document.addEventListener('DOMContentLoaded', () => {
  const csrfToken = document.querySelector('[name="csrfmiddlewaretoken"]')?.value || '';
  const searchForm = document.getElementById('favorite-client-search');
  const resultsBody = document.getElementById('favorite-client-results');
  const escapeHtml = value => String(value).replace(/[&<>'"]/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  }[char]));
  let searchTimer;
  async function searchFavorites() {
    if (!searchForm || !resultsBody) return;
    const query = searchForm.elements.q.value.trim();
    try {
      const response = await fetch(`${searchForm.dataset.searchUrl}?favorites=1&q=${encodeURIComponent(query)}`, {headers: {'X-Requested-With': 'XMLHttpRequest'}});
      if (!response.ok) return;
      const data = await response.json();
      resultsBody.innerHTML = data.results.length ? data.results.map(client => `
        <tr data-favorite-row="${client.id}"><td><div class="client-name-with-favorite"><button type="button" class="favorite-button is-favorite" data-client-id="${client.id}" data-favorite-url="${escapeHtml(client.favorite_url)}" data-remove-row="true" aria-label="Убрать клиента из избранного"><svg viewBox="0 0 24 24"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.7-7.5 1.1-1.1a5.5 5.5 0 0 0 0-7.8Z"/></svg></button><strong>${escapeHtml(client.name)}</strong></div></td><td>${escapeHtml(client.phone)}</td><td>${client.vehicle_count}</td><td>${escapeHtml(client.created_at)}</td><td><div class="row-actions"><a href="${escapeHtml(client.url)}">Открыть →</a></div></td></tr>
      `).join('') : '<tr><td colspan="5" class="empty">Избранные клиенты не найдены.</td></tr>';
    } catch (error) {}
  }
  searchForm?.elements.q.addEventListener('input', () => {
    clearTimeout(searchTimer); searchTimer = window.setTimeout(searchFavorites, 250);
  });
  searchForm?.addEventListener('submit', event => {
    event.preventDefault(); clearTimeout(searchTimer); searchFavorites();
  });
  document.addEventListener('click', async event => {
    const button = event.target.closest('.favorite-button');
    if (!button || button.disabled) return;
    button.disabled = true;
    try {
      const body = new URLSearchParams({csrfmiddlewaretoken: csrfToken});
      const response = await fetch(button.dataset.favoriteUrl, {
        method: 'POST', body, headers: {'X-Requested-With': 'XMLHttpRequest'},
      });
      if (!response.ok) throw new Error('Favorite update failed');
      const data = await response.json();
      document.querySelectorAll(`.favorite-button[data-client-id="${data.client_id}"]`).forEach(item => {
        item.classList.toggle('is-favorite', data.favorite);
        item.title = data.favorite ? 'Убрать из избранного' : 'Добавить в избранное';
        item.setAttribute('aria-label', item.title);
      });
      if (!data.favorite && button.dataset.removeCard === 'true') {
        const card = button.closest('[data-favorite-card]');
        card?.classList.add('is-removing');
        window.setTimeout(() => {
          card?.remove();
          const grid = document.getElementById('favorite-client-grid');
          if (grid && !grid.querySelector('[data-favorite-card]')) {
            grid.innerHTML = '<div class="favorite-empty"><span>♡</span><h2>Избранных клиентов пока нет</h2><p>Нажмите на сердечко рядом с клиентом — он появится здесь.</p></div>';
          }
        }, 180);
      }
      if (!data.favorite && button.dataset.removeRow === 'true') {
        const row = button.closest('[data-favorite-row]');
        row?.classList.add('is-removing');
        window.setTimeout(() => {
          row?.remove();
          if (resultsBody && !resultsBody.querySelector('[data-favorite-row]')) {
            resultsBody.innerHTML = '<tr><td colspan="5" class="empty">Избранных клиентов пока нет.</td></tr>';
          }
        }, 180);
      }
    } catch (error) {
      button.classList.add('has-error');
      window.setTimeout(() => button.classList.remove('has-error'), 600);
    } finally {
      button.disabled = false;
    }
  });
});
