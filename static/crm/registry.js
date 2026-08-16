document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('registry-filters');
  const body = document.getElementById('service-results');
  if (!form || !body) return;
  const pagination = document.querySelector('.pagination');
  const count = document.getElementById('registry-count');
  let timer;

  const escapeHtml = value => String(value).replace(/[&<>'"]/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  }[char]));

  async function updateResults() {
    const params = new URLSearchParams(new FormData(form));
    try {
      const response = await fetch(`${form.dataset.searchUrl}?${params}`, {
        headers: {'X-Requested-With': 'XMLHttpRequest'}
      });
      if (!response.ok) return;
      const data = await response.json();
      body.innerHTML = data.results.length ? data.results.map(item => `
        <tr><td><a href="${escapeHtml(item.client_url)}"><strong>${escapeHtml(item.client)}</strong><small>${escapeHtml(item.phone)}</small></a></td>
        <td>${escapeHtml(item.vehicle)}</td><td>${escapeHtml(item.service)}</td><td>${escapeHtml(item.expires_on)}</td>
        <td><span class="badge ${escapeHtml(item.status)}">${escapeHtml(item.status_label)}</span></td>
        <td><div class="row-actions">${item.closable ? `<a class="renew-service-link" href="${escapeHtml(item.renew_url)}">Продлить</a><a class="close-service-link" data-service="${escapeHtml(item.service)}" data-client="${escapeHtml(item.client)}" data-vehicle="${escapeHtml(item.vehicle)}" href="${escapeHtml(item.close_url)}">Закрыть</a>` : ''}<button type="button" class="delete-service-link" data-service="${escapeHtml(item.service)}" data-client="${escapeHtml(item.client)}" data-vehicle="${escapeHtml(item.vehicle)}" data-delete-url="${escapeHtml(item.delete_url)}" aria-label="Удалить услугу" title="Удалить услугу"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3m3 0-1 13H7L6 7m4 4v5m4-5v5"/></svg></button></div></td></tr>
      `).join('') : '<tr><td colspan="6" class="empty">Услуги не найдены.</td></tr>';
      if (pagination) pagination.hidden = true;
      if (count) count.textContent = `Найдено: ${data.results.length}`;
      const statTargets = {
        'stat-clients': data.stats.client_count,
        'stat-vehicles': data.stats.vehicle_count,
        'stat-services': data.stats.service_count,
        'stat-warning': data.stats.warning_count,
        'stat-expired': data.stats.expired_count,
        'stat-revenue': `${new Intl.NumberFormat('ru-RU').format(Number(data.stats.revenue_total)).replace(/\u00a0/g, ' ')} сум`,
      };
      Object.entries(statTargets).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) element.textContent = value;
      });
      const revenueLabel = document.getElementById('stat-revenue-label');
      if (revenueLabel) revenueLabel.textContent = params.get('date_from') || params.get('date_to') ? 'Сумма за период' : 'Сумма за сегодня';
    } catch (error) {
      // Оставляем серверный список, если соединение временно недоступно.
    }
  }
  form.querySelector('[name="q"]').addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(updateResults, 250);
  });
  form.querySelectorAll('select,input[type="date"]').forEach(field => field.addEventListener('change', updateResults));
});
