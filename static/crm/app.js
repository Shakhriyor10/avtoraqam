document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.money-input').forEach(input => {
    function formatMoney() {
      const cursorAtEnd = input.selectionStart === input.value.length;
      let value = input.value.replace(/\s/g, '').replace(/[^\d,.]/g, '').replace(',', '.');
      const parts = value.split('.');
      const integer = (parts.shift() || '').replace(/^0+(?=\d)/, '');
      const fraction = parts.join('').slice(0, 2);
      input.value = integer.replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + (value.includes('.') ? `.${fraction}` : '');
      if (cursorAtEnd) input.setSelectionRange(input.value.length, input.value.length);
    }
    input.addEventListener('input', formatMoney);
    formatMoney();
  });

  const clientSelect = document.getElementById('id_existing_client');
  const vehicleSelect = document.getElementById('id_existing_vehicle');
  if (!clientSelect || !vehicleSelect) return;

  const ownersNode = document.getElementById('vehicle-owners');
  const vehicleOwners = ownersNode ? JSON.parse(ownersNode.textContent) : {};
  const allVehicles = Array.from(vehicleSelect.options).map(option => ({
    value: option.value,
    text: option.textContent,
    owner: vehicleOwners[option.value] ? String(vehicleOwners[option.value]) : '',
  }));

  function enhanceSelect(select, placeholder) {
    const wrapper = document.createElement('div');
    wrapper.className = 'searchable-select';
    const input = document.createElement('input');
    input.type = 'search';
    input.autocomplete = 'off';
    input.placeholder = placeholder;
    const results = document.createElement('div');
    results.className = 'search-results';
    select.parentNode.insertBefore(wrapper, select);
    wrapper.append(input, select, results);

    function render() {
      const query = input.value.trim().toLowerCase();
      results.innerHTML = '';
      Array.from(select.options).filter(option => option.value).filter(option =>
        !query || option.textContent.toLowerCase().includes(query)
      ).slice(0, 30).forEach(option => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = `search-option${option.selected ? ' selected' : ''}`;
        button.textContent = option.textContent;
        button.addEventListener('mousedown', event => {
          event.preventDefault();
          select.value = option.value;
          input.value = option.textContent;
          results.classList.remove('open');
          input.blur();
          select.dispatchEvent(new Event('change', {bubbles: true}));
        });
        results.appendChild(button);
      });
      results.classList.toggle('open', document.activeElement === input);
    }
    const selected = select.options[select.selectedIndex];
    if (selected && selected.value) input.value = selected.textContent;
    input.addEventListener('focus', render);
    input.addEventListener('input', () => {
      select.value = '';
      render();
      select.dispatchEvent(new Event('change', {bubbles: true}));
    });
    input.addEventListener('blur', () => setTimeout(() => results.classList.remove('open'), 120));
    function showSelectedValue() {
      const option = select.options[select.selectedIndex];
      input.value = option && option.value ? option.textContent.trim() : '';
    }
    return {input, render, showSelectedValue};
  }

  const clientSearch = enhanceSelect(clientSelect, 'Начните вводить имя или телефон');
  const vehicleSearch = enhanceSelect(vehicleSelect, 'Начните вводить госномер');
  const newClientFields = ['id_full_name', 'id_phone', 'id_passport_files'].map(id => document.getElementById(id));
  const newVehicleFields = ['id_plate_number', 'id_make_model'].map(id => document.getElementById(id));

  function disable(fields, state) {
    fields.forEach(field => { if (field) field.disabled = state; });
  }
  function syncVehicle() {
    const vehicleId = vehicleSelect.value;
    const ownerId = vehicleOwners[vehicleId] ? String(vehicleOwners[vehicleId]) : '';
    if (vehicleId && ownerId) {
      clientSelect.value = ownerId;
      clientSearch.showSelectedValue();
      disable(newClientFields, true);
      filterVehicles();
      vehicleSelect.value = vehicleId;
      vehicleSearch.showSelectedValue();
    }
    disable(newVehicleFields, Boolean(vehicleSelect.value));
  }
  function filterVehicles() {
    const clientId = clientSelect.value;
    const oldValue = vehicleSelect.value;
    vehicleSelect.innerHTML = '';
    allVehicles.filter(item => !item.value || !clientId || item.owner === clientId).forEach(item => {
      vehicleSelect.add(new Option(item.text, item.value, false, item.value === oldValue));
    });
    if (!Array.from(vehicleSelect.options).some(option => option.value === oldValue)) {
      vehicleSelect.value = '';
      vehicleSearch.input.value = '';
    }
    vehicleSearch.render();
  }
  function syncClient() {
    const existing = Boolean(clientSelect.value);
    disable(newClientFields, existing);
    filterVehicles();
    if (!existing) {
      vehicleSelect.value = '';
      vehicleSearch.input.value = '';
    }
    syncVehicle();
  }

  clientSelect.addEventListener('change', syncClient);
  vehicleSelect.addEventListener('change', syncVehicle);
  syncClient();
});
