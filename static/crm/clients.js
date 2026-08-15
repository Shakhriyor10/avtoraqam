document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('client-search');
  const body = document.getElementById('client-results');
  if (!form || !body) return;
  const input = form.querySelector('[name="q"]');
  const pagination = document.querySelector('.pagination');
  const modal = document.getElementById('vehicle-modal');
  const modalTitle = document.getElementById('vehicle-modal-title');
  const modalList = document.getElementById('vehicle-modal-list');
  let timer;
  const escapeHtml = value => String(value).replace(/[&<>'"]/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  }[char]));

  async function search() {
    try {
      const response = await fetch(`${form.dataset.searchUrl}?q=${encodeURIComponent(input.value.trim())}`, {
        headers: {'X-Requested-With': 'XMLHttpRequest'}
      });
      if (!response.ok) return;
      const data = await response.json();
      body.innerHTML = data.results.length ? data.results.map(client => `
        <tr><td><strong>${escapeHtml(client.name)}</strong></td><td>${escapeHtml(client.phone)}</td>
        <td><div class="vehicle-count">${client.vehicle_count}${client.vehicle_count ? `<button type="button" class="vehicle-eye" data-vehicles-url="${escapeHtml(client.vehicles_url)}" aria-label="Показать автомобили" title="Показать автомобили"><svg viewBox="0 0 24 24"><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg></button>` : ''}</div></td><td>${escapeHtml(client.created_at)}</td>
        <td><div class="row-actions"><a href="${escapeHtml(client.url)}">Открыть →</a><button type="button" class="delete-client-link" data-client="${escapeHtml(client.name)}" data-delete-url="${escapeHtml(client.delete_url)}" aria-label="Удалить клиента" title="Удалить клиента"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3m3 0-1 13H7L6 7m4 4v5m4-5v5"/></svg></button></div></td></tr>
      `).join('') : '<tr><td colspan="5" class="empty">Клиенты не найдены.</td></tr>';
      if (pagination) pagination.hidden = Boolean(input.value.trim());
    } catch (error) {
      // При сетевой ошибке остаётся доступен обычный серверный поиск.
    }
  }
  input.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(search, 250);
  });
  form.addEventListener('submit', event => {
    event.preventDefault();
    clearTimeout(timer);
    search();
  });

  document.addEventListener('click', async event => {
    const eye = event.target.closest('.vehicle-eye');
    if (eye && modal) {
      try {
        const response = await fetch(eye.dataset.vehiclesUrl, {headers: {'X-Requested-With': 'XMLHttpRequest'}});
        if (!response.ok) return;
        const data = await response.json();
        modalTitle.textContent = data.client;
        modalList.innerHTML = data.vehicles.map(vehicle => `
          <div class="modal-vehicle"><span class="plate-number">${escapeHtml(vehicle.plate_number)}</span></div>
        `).join('');
        window.openCrmModal(modal);
      } catch (error) {}
    }
    if (event.target.closest('[data-modal-close]') && modal) {
      window.closeCrmModal(modal);
    }
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && modal && !modal.hidden) {
      window.closeCrmModal(modal);
    }
  });
});
