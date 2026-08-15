document.addEventListener('DOMContentLoaded', () => {
  function setupMoneyInputs(root = document) {
    root.querySelectorAll('.money-input').forEach(input => {
      if (input.dataset.moneyReady) return;
      input.dataset.moneyReady = '1';
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
  }
  setupMoneyInputs();

  const labelsNode = document.getElementById('additional-type-labels');
  const serviceLabels = labelsNode ? JSON.parse(labelsNode.textContent) : {};
  document.querySelectorAll('[data-additional-service]').forEach(card => {
    const enabled = card.querySelector('input[type="checkbox"]');
    const type = card.querySelector('input[type="hidden"]');
    const label = card.querySelector('[data-service-label]');
    if (label && type) label.textContent = serviceLabels[type.value] || type.value;
    const sync = () => card.classList.toggle('enabled', Boolean(enabled?.checked));
    enabled?.addEventListener('change', sync);
    sync();
  });

  const clientSelect = document.getElementById('id_existing_client');
  const vehicleSelect = document.getElementById('id_existing_vehicle');
  if (!clientSelect || !vehicleSelect) return;

  const ownersNode = document.getElementById('vehicle-owners');
  const clientVehiclesNode = document.getElementById('client-vehicles');
  const vehicleOwners = ownersNode ? JSON.parse(ownersNode.textContent) : {};
  const clientVehicles = clientVehiclesNode ? JSON.parse(clientVehiclesNode.textContent) : {};
  const allVehicles = Array.from(vehicleSelect.options).map(option => ({
    value: option.value,
    text: option.textContent,
    owner: vehicleOwners[option.value] ? String(vehicleOwners[option.value]) : '',
  }));
  let preferredVehicle = '';

  function normalize(value) { return String(value || '').toLowerCase().replace(/\s/g, ''); }

  function enhanceSelect(select, placeholder, searchText, onPick) {
    const wrapper = document.createElement('div');
    wrapper.className = 'searchable-select';
    const input = document.createElement('input');
    input.type = 'search'; input.autocomplete = 'off'; input.placeholder = placeholder;
    const results = document.createElement('div'); results.className = 'search-results';
    select.parentNode.insertBefore(wrapper, select); wrapper.append(input, select, results);
    function render() {
      const query = input.value.trim().toLowerCase(); results.innerHTML = '';
      Array.from(select.options).filter(option => option.value).filter(option =>
        !query || searchText(option).toLowerCase().includes(query) || normalize(searchText(option)).includes(normalize(query))
      ).slice(0, 30).forEach(option => {
        const button = document.createElement('button');
        button.type = 'button'; button.className = `search-option${option.selected ? ' selected' : ''}`;
        button.textContent = option.textContent;
        const plates = clientVehicles[String(option.value)] || [];
        if (select === clientSelect && plates.length) button.textContent += ` · ${plates.map(item => item.plate).join(', ')}`;
        button.addEventListener('mousedown', event => {
          event.preventDefault(); const typedQuery = input.value;
          select.value = option.value; input.value = option.textContent; results.classList.remove('open'); input.blur();
          if (onPick) onPick(option, typedQuery);
          select.dispatchEvent(new Event('change', {bubbles: true}));
        });
        results.appendChild(button);
      });
      results.classList.toggle('open', document.activeElement === input);
    }
    const selected = select.options[select.selectedIndex];
    if (selected?.value) input.value = selected.textContent;
    input.addEventListener('focus', render);
    input.addEventListener('input', () => { select.value = ''; render(); select.dispatchEvent(new Event('change', {bubbles: true})); });
    input.addEventListener('blur', () => setTimeout(() => results.classList.remove('open'), 120));
    return {
      input, render,
      showSelectedValue() { const option = select.options[select.selectedIndex]; input.value = option?.value ? option.textContent.trim() : ''; },
    };
  }

  const clientSearch = enhanceSelect(
    clientSelect,
    'Введите ФИО, телефон или госномер',
    option => `${option.textContent} ${(clientVehicles[String(option.value)] || []).map(item => item.plate).join(' ')}`,
    (option, query) => {
      const vehicles = clientVehicles[String(option.value)] || [];
      const matched = vehicles.find(item => normalize(item.plate).includes(normalize(query)));
      preferredVehicle = matched?.id || vehicles[0]?.id || '';
    },
  );
  const vehicleSearch = enhanceSelect(vehicleSelect, 'Введите госномер', option => option.textContent);
  const newClientFields = ['id_full_name', 'id_phone', 'id_passport_files'].map(id => document.getElementById(id));
  const newVehicleFields = ['id_plate_number'].map(id => document.getElementById(id));
  function disable(fields, state) { fields.forEach(field => { if (field) field.disabled = state; }); }

  function filterVehicles() {
    const clientId = clientSelect.value;
    const target = preferredVehicle || vehicleSelect.value;
    vehicleSelect.innerHTML = '';
    allVehicles.filter(item => !item.value || !clientId || item.owner === clientId).forEach(item => {
      vehicleSelect.add(new Option(item.text, item.value, false, item.value === target));
    });
    vehicleSelect.value = Array.from(vehicleSelect.options).some(option => option.value === target) ? target : '';
    preferredVehicle = '';
    vehicleSearch.showSelectedValue(); vehicleSearch.render();
  }
  function syncVehicle() {
    const vehicleId = vehicleSelect.value;
    const ownerId = vehicleOwners[vehicleId] ? String(vehicleOwners[vehicleId]) : '';
    if (vehicleId && ownerId && clientSelect.value !== ownerId) {
      clientSelect.value = ownerId; clientSearch.showSelectedValue(); disable(newClientFields, true);
      preferredVehicle = vehicleId; filterVehicles();
    }
    disable(newVehicleFields, Boolean(vehicleSelect.value));
  }
  function syncClient() {
    const existing = Boolean(clientSelect.value);
    disable(newClientFields, existing); filterVehicles();
    if (!existing) { vehicleSelect.value = ''; vehicleSearch.input.value = ''; }
    syncVehicle();
  }
  clientSelect.addEventListener('change', syncClient);
  vehicleSelect.addEventListener('change', syncVehicle);
  if (clientSelect.value && vehicleSelect.value) preferredVehicle = vehicleSelect.value;
  syncClient();
});

window.openCrmModal = modal => {
  if (!modal) return;
  modal.classList.remove('is-closing');
  modal.hidden = false;
  document.body.classList.add('modal-open');
};

window.closeCrmModal = (modal, afterClose) => {
  if (!modal || modal.hidden || modal.classList.contains('is-closing')) return;
  modal.classList.add('is-closing');
  window.setTimeout(() => {
    modal.hidden = true;
    modal.classList.remove('is-closing');
    document.body.classList.remove('modal-open');
    afterClose?.();
  }, 180);
};
