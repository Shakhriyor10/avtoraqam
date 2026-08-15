document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('delete-client-modal');
  const form = document.getElementById('delete-client-form');
  const summary = document.getElementById('delete-client-summary');
  const error = document.getElementById('delete-client-error');
  if (!modal || !form) return;
  let activeButton = null;
  const close = () => {
    window.closeCrmModal(modal, () => { activeButton = null; });
  };
  document.addEventListener('click', event => {
    const button = event.target.closest('.delete-client-link');
    if (button) {
      activeButton = button;
      form.action = button.dataset.deleteUrl;
      form.reset();
      error.textContent = '';
      summary.textContent = button.dataset.client || '';
      window.openCrmModal(modal);
      setTimeout(() => form.elements.password.focus(), 0);
    }
    if (event.target.closest('[data-delete-client-dismiss]')) close();
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
        error.textContent = data.error || 'Не удалось удалить клиента.';
        return;
      }
      if (activeButton?.dataset.clientDetail === 'true') {
        window.location.assign(data.redirect_url);
        return;
      }
      const row = activeButton?.closest('tr');
      const body = row?.parentElement;
      row?.remove();
      if (body && !body.querySelector('tr')) body.innerHTML = '<tr><td colspan="5" class="empty">Клиенты не найдены.</td></tr>';
      close();
    } catch (requestError) {
      error.textContent = 'Ошибка соединения. Попробуйте ещё раз.';
    } finally {
      submit.disabled = false;
    }
  });
});
