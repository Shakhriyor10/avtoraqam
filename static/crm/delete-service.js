document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('delete-service-modal');
  const form = document.getElementById('delete-service-form');
  const summary = document.getElementById('delete-modal-summary');
  const error = document.getElementById('delete-service-error');
  if (!modal || !form) return;
  let activeButton = null;

  const close = () => {
    window.closeCrmModal(modal, () => { activeButton = null; });
  };
  document.addEventListener('click', event => {
    const button = event.target.closest('.delete-service-link');
    if (button) {
      activeButton = button;
      form.action = button.dataset.deleteUrl;
      form.reset();
      error.textContent = '';
      summary.textContent = [button.dataset.service, button.dataset.client, button.dataset.vehicle].filter(Boolean).join(' · ');
      window.openCrmModal(modal);
      setTimeout(() => form.elements.password.focus(), 0);
    }
    if (event.target.closest('[data-delete-modal-dismiss]')) close();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !modal.hidden) close();
  });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    error.textContent = '';
    const submit = form.querySelector('[type="submit"]');
    submit.disabled = true;
    try {
      const response = await fetch(form.action, {
        method: 'POST', body: new FormData(form),
        headers: {'X-Requested-With': 'XMLHttpRequest'},
      });
      const data = await response.json();
      if (!response.ok) {
        error.textContent = data.error || 'Не удалось удалить услугу.';
        return;
      }
      const row = activeButton?.closest('tr');
      const body = row?.parentElement;
      const columnCount = row?.closest('table')?.querySelectorAll('thead th').length || 6;
      row?.remove();
      if (body && !body.querySelector('tr')) body.innerHTML = `<tr><td colspan="${columnCount}" class="empty">Услуг пока нет.</td></tr>`;
      const decrement = id => {
        const node = document.getElementById(id);
        if (node) node.textContent = Math.max(0, Number(node.textContent) - 1);
      };
      decrement('stat-services');
      if (data.status === 'warning') decrement('stat-warning');
      if (data.status === 'expired') decrement('stat-expired');
      const count = document.getElementById('registry-count');
      const match = count?.textContent.match(/\d+/);
      if (count && match) count.textContent = `Найдено: ${Math.max(0, Number(match[0]) - 1)}`;
      close();
      const statusFilter = document.querySelector('#registry-filters [name="status"]');
      statusFilter?.dispatchEvent(new Event('change', {bubbles: true}));
    } catch (requestError) {
      error.textContent = 'Ошибка соединения. Попробуйте ещё раз.';
    } finally {
      submit.disabled = false;
    }
  });
});
