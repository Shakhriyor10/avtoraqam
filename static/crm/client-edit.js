document.addEventListener('DOMContentLoaded', () => {
  const addButton = document.getElementById('add-vehicle-row');
  const rows = document.getElementById('vehicle-formset-rows');
  const template = document.getElementById('empty-vehicle-form');
  const totalForms = document.getElementById('id_vehicles-TOTAL_FORMS');
  if (!addButton || !rows || !template || !totalForms) return;

  addButton.addEventListener('click', () => {
    const index = Number(totalForms.value);
    const wrapper = document.createElement('div');
    wrapper.innerHTML = template.innerHTML.replaceAll('__prefix__', String(index)).trim();
    const row = wrapper.firstElementChild;
    if (!row) return;
    rows.appendChild(row);
    totalForms.value = String(index + 1);
    row.querySelector('input:not([type="hidden"])')?.focus();
  });
});
