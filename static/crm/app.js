document.addEventListener('DOMContentLoaded', () => {
  const serviceFavoriteToggle = document.getElementById('service-favorite-toggle');
  const addToFavorites = document.getElementById('add-to-favorites');
  serviceFavoriteToggle?.addEventListener('click', () => {
    const selected = addToFavorites.value !== '1';
    addToFavorites.value = selected ? '1' : '0';
    serviceFavoriteToggle.classList.toggle('is-selected', selected);
    serviceFavoriteToggle.setAttribute('aria-pressed', String(selected));
  });

  const modeToggle = document.getElementById('color-mode-toggle');
  if (modeToggle) {
    modeToggle.addEventListener('click', async () => {
      if (modeToggle.disabled) return;
      const html = document.documentElement;
      const previous = html.dataset.colorMode || 'light';
      const next = previous === 'dark' ? 'light' : 'dark';
      html.dataset.colorMode = next;
      modeToggle.disabled = true;
      try {
        const csrfToken = document.querySelector('[name="csrfmiddlewaretoken"]')?.value || '';
        const body = new URLSearchParams({csrfmiddlewaretoken: csrfToken, color_mode: next});
        const response = await fetch(modeToggle.dataset.url, {
          method: 'POST', body, headers: {'X-Requested-With': 'XMLHttpRequest'},
        });
        if (!response.ok) throw new Error('Mode update failed');
      } catch (error) {
        html.dataset.colorMode = previous;
      } finally {
        modeToggle.disabled = false;
      }
    });
  }

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

  const themeCards = document.querySelectorAll('.theme-card');
  themeCards.forEach(card => {
    const radio = card.querySelector('input[name="theme"]');
    radio?.addEventListener('change', () => {
      themeCards.forEach(item => item.classList.toggle(
        'selected', item.querySelector('input[name="theme"]')?.checked,
      ));
    });
  });
  const modeCards = document.querySelectorAll('.mode-card');
  modeCards.forEach(card => {
    const radio = card.querySelector('input[name="color_mode"]');
    radio?.addEventListener('change', () => {
      modeCards.forEach(item => item.classList.toggle(
        'selected', item.querySelector('input[name="color_mode"]')?.checked,
      ));
    });
  });

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

  const serviceForm = document.getElementById('service-create-form');
  const duplicateModal = document.getElementById('duplicate-service-modal');
  const duplicateList = document.getElementById('duplicate-service-list');
  const duplicateConfirmed = document.getElementById('duplicate-confirmed');
  const duplicateSkipTypes = document.getElementById('duplicate-skip-types');
  if (serviceForm && duplicateModal && duplicateList && duplicateConfirmed && duplicateSkipTypes) {
    let checkingDuplicate = false;
    let currentDuplicateTypes = [];
    let currentSelectedTypes = [];
    const closeDuplicate = () => window.closeCrmModal(duplicateModal);
    duplicateModal.addEventListener('click', event => {
      if (event.target.closest('[data-duplicate-dismiss]')) closeDuplicate();
    });
    document.getElementById('duplicate-service-confirm')?.addEventListener('click', () => {
      duplicateConfirmed.value = '1';
      duplicateSkipTypes.value = '';
      closeDuplicate();
      serviceForm.submit();
    });
    document.getElementById('duplicate-service-new-only')?.addEventListener('click', () => {
      duplicateConfirmed.value = '1';
      duplicateSkipTypes.value = currentDuplicateTypes.join(',');
      closeDuplicate();
      serviceForm.submit();
    });
    serviceForm.addEventListener('submit', async event => {
      if (duplicateConfirmed.value === '1' || checkingDuplicate) return;
      event.preventDefault();
      checkingDuplicate = true;
      const submitButton = serviceForm.querySelector('[type="submit"]');
      if (submitButton) submitButton.disabled = true;
      const payload = new URLSearchParams();
      payload.append('csrfmiddlewaretoken', serviceForm.elements.csrfmiddlewaretoken.value);
      payload.append('vehicle_id', serviceForm.elements.existing_vehicle?.value || '');
      payload.append('plate_number', serviceForm.elements.plate_number?.value || '');
      payload.append('service_types', serviceForm.dataset.serviceType);
      currentSelectedTypes = [serviceForm.dataset.serviceType];
      serviceForm.querySelectorAll('[data-additional-service]').forEach(card => {
        const enabled = card.querySelector('input[type="checkbox"]');
        const type = card.querySelector('input[type="hidden"]');
        if (enabled?.checked && type?.value) {
          payload.append('service_types', type.value);
          currentSelectedTypes.push(type.value);
        }
      });
      try {
        const response = await fetch(serviceForm.dataset.duplicateCheckUrl, {
          method: 'POST', body: payload,
          headers: {'X-Requested-With': 'XMLHttpRequest'},
        });
        if (!response.ok) throw new Error('Duplicate check failed');
        const data = await response.json();
        if (!data.duplicates?.length) {
          serviceForm.submit();
          return;
        }
        currentDuplicateTypes = data.duplicates.map(item => item.service_type);
        duplicateList.innerHTML = '';
        data.duplicates.forEach(item => {
          const row = document.createElement('div');
          row.className = 'duplicate-service-item';
          const heading = document.createElement('strong');
          heading.textContent = `${item.service_name} · ${item.plate_number}`;
          const details = document.createElement('span');
          details.textContent = `${item.client_name} · оформлена ${item.issued_on}${item.expires_on ? ` · действует до ${item.expires_on}` : ' · без срока'}`;
          row.append(heading, details);
          duplicateList.appendChild(row);
        });
        const newOnlyButton = document.getElementById('duplicate-service-new-only');
        if (newOnlyButton) {
          const newCount = currentSelectedTypes.filter(type => !currentDuplicateTypes.includes(type)).length;
          newOnlyButton.hidden = newCount === 0;
          newOnlyButton.textContent = newCount === 1 ? 'Добавить только новую услугу' : `Добавить только новые (${newCount})`;
        }
        window.openCrmModal(duplicateModal);
      } catch (error) {
        serviceForm.submit();
      } finally {
        checkingDuplicate = false;
        if (submitButton) submitButton.disabled = false;
      }
    });
  }

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

document.addEventListener('DOMContentLoaded', () => {
  const opener = document.getElementById('open-user-create');
  const modal = document.getElementById('user-create-modal');
  const form = document.getElementById('user-create-form');
  if (!opener || !modal || !form) return;
  const close = () => window.closeCrmModal(modal);
  opener.addEventListener('click', () => {
    form.reset();
    window.openCrmModal(modal);
    window.setTimeout(() => form.elements.username?.focus(), 0);
  });
  modal.addEventListener('click', event => {
    if (event.target.closest('[data-user-modal-close]')) close();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !modal.hidden) close();
  });
});
