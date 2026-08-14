document.addEventListener('DOMContentLoaded', () => {
  const opener = document.getElementById('open-vehicle-create');
  const modal = document.getElementById('vehicle-create-modal');
  const form = document.getElementById('vehicle-create-form');
  const list = document.getElementById('client-vehicle-list');
  if (!opener || !modal || !form || !list) return;
  const close = () => { modal.hidden = true; document.body.classList.remove('modal-open'); };
  opener.addEventListener('click', event => { event.preventDefault(); form.reset(); modal.hidden = false; document.body.classList.add('modal-open'); setTimeout(() => form.elements.plate_number.focus(), 0); });
  modal.addEventListener('click', event => { if (event.target.closest('[data-create-modal-close]')) close(); });
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && !modal.hidden) close(); });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    form.querySelectorAll('[data-error-for]').forEach(item => item.textContent = '');
    const submit = form.querySelector('[type="submit"]'); submit.disabled = true;
    try {
      const response = await fetch(form.action, {method: 'POST', body: new FormData(form), headers: {'X-Requested-With': 'XMLHttpRequest'}});
      const data = await response.json();
      if (!response.ok) { Object.entries(data.errors || {}).forEach(([name, errors]) => { const target = form.querySelector(`[data-error-for="${name}"]`); if (target) target.textContent = errors.join(' '); }); return; }
      document.getElementById('no-client-vehicles')?.remove();
      const row = document.createElement('div'); row.className = 'vehicle vehicle-new';
      const plate = document.createElement('strong'); plate.textContent = data.plate_number;
      row.append(plate); list.prepend(row); close();
    } finally { submit.disabled = false; }
  });
});
