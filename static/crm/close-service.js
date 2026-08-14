document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('close-service-modal');
  const form = document.getElementById('close-service-form');
  const title = document.getElementById('close-modal-title');
  const summary = document.getElementById('close-modal-summary');
  const error = document.getElementById('close-service-error');
  if (!modal || !form) return;
  let activeLink = null;
  const close = () => { modal.hidden = true; document.body.classList.remove('modal-open'); activeLink = null; };

  document.addEventListener('click', event => {
    const link = event.target.closest('.close-service-link');
    if (link) {
      event.preventDefault(); activeLink = link; form.action = link.href; form.reset(); error.textContent = '';
      title.textContent = link.dataset.service || 'Закрыть услугу';
      summary.textContent = [link.dataset.client, link.dataset.vehicle].filter(Boolean).join(' · ');
      modal.hidden = false; document.body.classList.add('modal-open');
    }
    if (event.target.closest('[data-close-modal-dismiss]')) close();
  });
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && !modal.hidden) close(); });
  form.addEventListener('submit', async event => {
    event.preventDefault(); error.textContent = '';
    const submit = form.querySelector('[type="submit"]'); submit.disabled = true;
    try {
      const response = await fetch(form.action, {method: 'POST', body: new FormData(form), headers: {'X-Requested-With': 'XMLHttpRequest'}});
      const data = await response.json();
      if (!response.ok) { error.textContent = data.error || 'Не удалось закрыть предупреждение.'; return; }
      const row = activeLink?.closest('tr');
      const badge = row?.querySelector('.badge');
      const previousStatus = badge?.classList.contains('expired') ? 'expired' : 'warning';
      if (badge) { badge.className = 'badge closed'; badge.textContent = data.status_label; }
      activeLink?.closest('.row-actions')?.querySelector('.renew-service-link')?.remove();
      activeLink?.remove();
      const counterId = previousStatus === 'expired' ? 'stat-expired' : 'stat-warning';
      const counter = document.getElementById(counterId);
      if (counter) counter.textContent = Math.max(0, Number(counter.textContent) - 1);
      close();
    } catch (requestError) { error.textContent = 'Ошибка соединения. Попробуйте ещё раз.'; }
    finally { submit.disabled = false; }
  });
});
