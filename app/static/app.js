const state = { parts: [], selected: null, cart: [], lastFocus: null, cartFocus: null };

function customerText(value) {
  return String(value || '')
    .replaceAll('Buyuk', 'Büyük')
    .replaceAll('Kucuk', 'Küçük')
    .replaceAll('Yukseklik', 'Yükseklik')
    .replaceAll('Gecis', 'Geçiş')
    .replaceAll('Giris', 'Giriş')
    .replaceAll('Cikis', 'Çıkış')
    .replaceAll('Kaciklik', 'Kaçıklık')
    .replaceAll('Kirikli', 'Kırıklı')
    .replaceAll('Egrili', 'Eğrili')
    .replaceAll('Reduksiyon', 'Redüksiyon')
    .replaceAll('Yuvarlaga', 'Yuvarlağa')
    .replaceAll('Kelepce', 'Kelepçe')
    .replaceAll('Kortapa', 'Kör Tapa')
    .replaceAll('Sapka', 'Şapka')
    .replaceAll('Istavroz', 'İstavroz')
    .replaceAll('Manson', 'Manşon')
    .replaceAll('Govde', 'Gövde')
    .replaceAll('Uzunlugu', 'Uzunluğu')
    .replaceAll('Derinligi', 'Derinliği')
    .replaceAll('Radyusu', 'Radyüsü')
    .replaceAll('Agiz', 'Ağız')
    .replaceAll('Capi', 'Çapı')
    .replaceAll('Cap', 'Çap');
}

function sortSelectOptions(select) {
  const selectedValue = select.value;
  const options = Array.from(select.options);
  const placeholders = options.filter(option => option.value === '');
  const values = options.filter(option => option.value !== '');
  values.sort((a, b) => a.textContent.localeCompare(b.textContent, 'tr', { numeric: true, sensitivity: 'base' }));
  select.replaceChildren(...placeholders, ...values);
  select.value = selectedValue;
}

function staticAssetUrl(path) {
  const version = window.APP_ASSET_VERSION || '';
  const suffix = version ? `?v=${encodeURIComponent(version)}` : '';
  return `/static/${path}${suffix}`;
}

function showToast(message, kind = 'info') {
  const el = document.querySelector('#toast');
  el.textContent = message;
  el.className = `toast ${kind}`;
  el.hidden = false;
  setTimeout(() => { el.hidden = true; }, 3000);
}

async function loadParts() {
  const response = await fetch('/api/parts');
  const data = await response.json();
  state.parts = data.items;
  renderParts();
}

function renderParts() {
  const root = document.querySelector('#parts');
  const tabsRoot = document.querySelector('#part-tabs');
  root.innerHTML = '';
  tabsRoot.innerHTML = '';
  const groups = [
    { key: 'kare', label: 'KARE' },
    { key: 'yuvarlak', label: 'YUVARLAK' },
  ];
  const available = groups.filter(g => state.parts.some(p => p.group === g.key));
  const activeTab = root.dataset.activeTab || (available.length ? available[0].key : null);
  const tabBar = document.createElement('div');
  tabBar.className = 'parts-tabs';
  for (const g of available) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'parts-tab' + (g.key === activeTab ? ' active' : '');
    btn.textContent = g.label;
    btn.addEventListener('click', () => {
      root.dataset.activeTab = g.key;
      renderParts();
    });
    tabBar.appendChild(btn);
  }
  tabsRoot.appendChild(tabBar);
  const grid = document.createElement('div');
  grid.className = 'parts-grid';
  for (const part of state.parts.filter(p => p.group === activeTab)) {
    const card = document.createElement('button');
    card.type = 'button';
    card.className = 'part-card';
    const image = part.image ? staticAssetUrl(`parcalar/${part.image}`) : '';
    card.innerHTML = `
      ${image ? `<img class="part-image" src="${image}" alt="${customerText(part.title)}" loading="lazy">` : ''}
      <div class="part-card-body">
        <div class="group">${part.group}</div>
        <h3>${customerText(part.title)}</h3>
      </div>
    `;
    card.setAttribute('aria-label', `${customerText(part.title)} ölçülerini gir`);
    card.addEventListener('click', () => openModal(part));
    grid.appendChild(card);
  }
  root.appendChild(grid);
}

function dimensionMarker(fieldName) {
  return (state.selected?.dimension_markers || []).find(marker => marker.field === fieldName);
}

function updateDimensionBadge(fieldName) {
  const marker = dimensionMarker(fieldName);
  if (!marker) return;
  const input = document.querySelector('#part-form').elements.namedItem(fieldName);
  const badge = document.querySelector(`.dimension-badge[data-field="${fieldName}"]`);
  if (!(input instanceof HTMLInputElement) || !(badge instanceof HTMLButtonElement)) return;
  const value = input.value.trim();
  const valueEl = badge.querySelector('.dimension-badge-value');
  valueEl.textContent = value ? `${value} ${marker.unit}` : '';
  badge.classList.toggle('has-value', Boolean(value));
}

function updateAllDimensionBadges() {
  for (const marker of state.selected?.dimension_markers || []) updateDimensionBadge(marker.field);
}

function updateComputedFields(sourceFieldName = null) {
  const form = document.querySelector('#part-form');
  for (const definition of state.selected?.computed_fields || []) {
    if (sourceFieldName && definition.source !== sourceFieldName) continue;
    const source = form.elements.namedItem(definition.source);
    const target = form.elements.namedItem(definition.field);
    if (!(source instanceof HTMLInputElement) || !(target instanceof HTMLInputElement)) continue;
    const sourceValue = Number.parseFloat(source.value);
    const computedValue = sourceValue * Number(definition.factor);
    if (!Number.isFinite(computedValue)) {
      target.value = '';
    } else {
      const decimals = Number.isInteger(definition.decimals) ? definition.decimals : 2;
      target.value = computedValue.toFixed(decimals).replace(/\.?0+$/, '');
    }
    updateDimensionBadge(definition.field);
  }
}

function activateDimensionField(fieldName) {
  state.activeDimensionField = fieldName;
  for (const element of document.querySelectorAll('[data-dimension-field]')) {
    element.classList.toggle('active', element.dataset.dimensionField === fieldName);
  }
  for (const badge of document.querySelectorAll('.dimension-badge')) {
    badge.classList.toggle('active', badge.dataset.field === fieldName);
  }
  updateDimensionBadge(fieldName);
}

function renderDimensionMarkers(part) {
  const svg = document.querySelector('#modal-dimension-lines');
  const badges = document.querySelector('#modal-dimension-badges');
  const help = document.querySelector('#modal-preview-help');
  const visualStage = document.querySelector('#modal-visual-stage');
  svg.innerHTML = '';
  badges.innerHTML = '';
  visualStage.classList.toggle('focus-dimension-markers', part.marker_display === 'focus');
  document.querySelector('#equal-arms-visual').hidden = true;
  const markers = part.dimension_markers || [];
  help.textContent = markers.length
    ? 'Bir ölçü alanına dokunun; görselde ilgili kesit vurgulansın.'
    : 'Ölçüleri girin; seçtiğiniz parça doğrudan sepetinize eklensin.';

  const svgNs = 'http://www.w3.org/2000/svg';
  for (const marker of markers) {
    const group = document.createElementNS(svgNs, 'g');
    group.classList.add('dimension-line-group');
    group.dataset.dimensionField = marker.field;
    const segments = marker.segments?.length ? marker.segments : [marker.line];
    const dotCoordinates = [];
    for (const segment of segments) {
      const line = document.createElementNS(svgNs, 'line');
      line.classList.add('dimension-line');
      line.setAttribute('x1', segment[0]);
      line.setAttribute('y1', segment[1]);
      line.setAttribute('x2', segment[2]);
      line.setAttribute('y2', segment[3]);
      group.appendChild(line);
      dotCoordinates.push([segment[0], segment[1]], [segment[2], segment[3]]);
    }
    if (marker.path) {
      const path = document.createElementNS(svgNs, 'path');
      path.classList.add('dimension-line', 'dimension-arc');
      path.setAttribute('d', marker.path);
      group.appendChild(path);
    }
    const uniqueDots = new Map(dotCoordinates.map(point => [point.join(','), point]));
    for (const [cx, cy] of uniqueDots.values()) {
      const dot = document.createElementNS(svgNs, 'circle');
      dot.classList.add('dimension-dot');
      dot.setAttribute('cx', cx);
      dot.setAttribute('cy', cy);
      dot.setAttribute('r', '1.15');
      group.appendChild(dot);
    }
    svg.appendChild(group);

    const badge = document.createElement('button');
    badge.type = 'button';
    badge.className = 'dimension-badge';
    badge.dataset.field = marker.field;
    badge.style.left = `${marker.label[0]}%`;
    badge.style.top = `${marker.label[1]}%`;
    const field = part.fields.find(item => item.name === marker.field);
    badge.setAttribute('aria-label', `${customerText(field?.label || marker.symbol)} alanına git`);
    badge.title = customerText(field?.label || marker.symbol);
    badge.innerHTML = `<span class="dimension-badge-symbol">${marker.symbol}</span><span class="dimension-badge-value"></span>`;
    badge.addEventListener('click', () => {
      const input = document.querySelector('#part-form').elements.namedItem(marker.field);
      if (input instanceof HTMLInputElement) input.focus();
    });
    badges.appendChild(badge);
  }
}

function applyEqualArms(enabled) {
  const pairs = state.selected?.equal_arm_pairs || [];
  const form = document.querySelector('#part-form');
  for (const pair of pairs) {
    const source = form.elements.namedItem(pair.source);
    const target = form.elements.namedItem(pair.target);
    if (!(source instanceof HTMLInputElement) || !(target instanceof HTMLInputElement)) continue;
    target.readOnly = enabled;
    target.required = !enabled;
    target.closest('label')?.classList.toggle('equal-arm-target-hidden', enabled);
    if (enabled) target.value = source.value;
  }
  document.querySelector('#equal-arms-visual').hidden = !enabled;
  updateAllDimensionBadges();
}

function openModal(part) {
  state.selected = part;
  state.lastFocus = document.activeElement;
  document.querySelector('#modal-title').textContent = customerText(part.title);
  const group = document.querySelector('#modal-part-group');
  group.textContent = part.group === 'kare' ? 'Kare Parça' : 'Yuvarlak Parça';
  const image = document.querySelector('#modal-part-image');
  const fallback = document.querySelector('#modal-image-fallback');
  const visualStage = document.querySelector('#modal-visual-stage');
  if (part.image) {
    visualStage.hidden = false;
    image.hidden = false;
    fallback.hidden = true;
    image.alt = `${customerText(part.title)} görseli`;
    image.src = staticAssetUrl(`parcalar/${part.image}`);
    image.onerror = () => {
      visualStage.hidden = true;
      image.hidden = true;
      fallback.hidden = false;
    };
  } else {
    visualStage.hidden = true;
    image.hidden = true;
    image.removeAttribute('src');
    fallback.hidden = false;
  }
  renderDimensionMarkers(part);
  const fields = document.querySelector('#dynamic-fields');
  fields.innerHTML = '';
  for (const field of part.fields) {
    const label = document.createElement('label');
    label.dataset.fieldName = field.name;
    const computedDefinition = (part.computed_fields || []).find(item => item.field === field.name);
    if (computedDefinition) label.classList.add('computed-field');
    const caption = document.createElement('span');
    caption.className = 'field-caption';
    const marker = dimensionMarker(field.name);
    if (marker) {
      const symbol = document.createElement('span');
      symbol.className = 'field-dimension-symbol';
      symbol.textContent = marker.symbol;
      caption.appendChild(symbol);
    }
    const captionText = document.createElement('span');
    captionText.textContent = customerText(field.label);
    caption.appendChild(captionText);
    if (computedDefinition) {
      const automatic = document.createElement('span');
      automatic.className = 'automatic-field-badge';
      automatic.textContent = 'Otomatik';
      caption.appendChild(automatic);
    }
    label.appendChild(caption);
    const input = document.createElement('input');
    input.name = field.name;
    input.type = 'number';
    input.step = '0.01';
    input.required = !computedDefinition;
    input.readOnly = Boolean(computedDefinition);
    if (computedDefinition) input.placeholder = 'Çapa göre hesaplanır';
    label.appendChild(input);
    fields.appendChild(label);
  }
  document.querySelector('#dynamic-fields').querySelectorAll('input').forEach((el) => { el.value = ''; });
  updateComputedFields();
  document.querySelector('#quantity').value = 1;
  document.querySelector('#quantity-option').hidden = part.code === 'spiro_boru';
  document.querySelector('#boya_ekle').checked = false;
  document.querySelector('#boya_ekle').value = 'on';
  document.querySelector('#izolasyon_ozellik_id').value = '';
  const equalArmsOption = document.querySelector('#equal-arms-option');
  const equalArmsCheckbox = document.querySelector('#kollar_esit');
  equalArmsCheckbox.checked = false;
  equalArmsOption.hidden = !(part.equal_arm_pairs?.length);
  applyEqualArms(false);
  const modal = document.querySelector('#part-modal');
  modal.classList.add('open');
  modal.setAttribute('aria-hidden', 'false');
  document.body.classList.add('modal-open');
  requestAnimationFrame(() => fields.querySelector('input')?.focus());
}

function closeModal() {
  const modal = document.querySelector('#part-modal');
  modal.classList.remove('open');
  modal.setAttribute('aria-hidden', 'true');
  document.body.classList.remove('modal-open');
  if (state.lastFocus instanceof HTMLElement) state.lastFocus.focus();
}

function openCart() {
  const modal = document.querySelector('#cart-modal');
  state.cartFocus = document.activeElement;
  modal.classList.add('open');
  modal.setAttribute('aria-hidden', 'false');
  document.body.classList.add('modal-open');
  requestAnimationFrame(() => modal.querySelector('.cart-close')?.focus());
}

function closeCart() {
  const modal = document.querySelector('#cart-modal');
  modal.classList.remove('open');
  modal.setAttribute('aria-hidden', 'true');
  document.body.classList.remove('modal-open');
  if (state.cartFocus instanceof HTMLElement) state.cartFocus.focus();
}

function updateCartMenu() {
  const count = (state.cart.items || []).reduce((total, item) => total + Number(item.quantity || 0), 0);
  const badge = document.querySelector('#cart-menu-count');
  const menu = document.querySelector('#cart-menu');
  if (badge) badge.textContent = count;
  if (menu) menu.setAttribute('aria-label', `Sepetim, ${count} ürün`);
}

function renderCart() {
  const root = document.querySelector('#cart');
  const btn = document.querySelector('#quote-btn');
  updateCartMenu();
  if (!state.cart.items?.length) {
    root.innerHTML = '<p class="muted">Henüz kalem yok.</p>';
    btn.disabled = true;
    return;
  }
  const items = [...state.cart.items].sort((a, b) => {
    const partOrder = customerText(a.part_name).localeCompare(customerText(b.part_name), 'tr', { sensitivity: 'base' });
    return partOrder || customerText(a.display).localeCompare(customerText(b.display), 'tr', { numeric: true, sensitivity: 'base' });
  }).map((item, index) => {
    const isSpiro = item.part_code === 'spiro_boru';
    const totalMetres = Number(item.inputs?.uzunluk || 0) * Number(item.quantity || 0);
    const measure = isSpiro ? customerText(item.display).replace(/\s*L:[^\s]+m/, '') : customerText(item.display);
    const quantityControl = isSpiro
      ? `<span class="cart-quantity-label">Metre</span><input class="cart-metre-input" type="number" min="0.01" step="0.01" value="${totalMetres}"><button class="cart-update" type="button">Güncelle</button>`
      : `<span class="cart-quantity-label">Adet</span><input class="cart-qty" type="number" min="1" value="${item.quantity}"><button class="cart-update" type="button">Güncelle</button>`;
    return `
      <div class="cart-item" data-id="${item.id}">
        <div class="cart-item-details">
          <strong>${index + 1}. ${customerText(item.part_name)}</strong>
          ${measure ? `<div class="cart-item-measure">${measure}</div>` : ''}
          ${item.options?.length ? `<div class="cart-item-options">${item.options.map(option => `<span>${customerText(option)}</span>`).join('')}</div>` : ''}
        </div>
        <div class="cart-item-actions">
          ${quantityControl}
          <button class="cart-delete" type="button">Sil</button>
        </div>
      </div>
    `;
  }).join('');
  root.innerHTML = items;
  btn.disabled = false;
  attachCartEvents();
}

function formatMoney(value) {
  return Number(value || 0).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' TL';
}

function attachCartEvents() {
  for (const btn of document.querySelectorAll('.cart-update')) {
    btn.addEventListener('click', async () => {
      const row = btn.closest('.cart-item');
      const id = Number(row.dataset.id);
      const item = state.cart.items.find(cartItem => Number(cartItem.id) === id);
      const metreInput = row.querySelector('.cart-metre-input');
      const isSpiro = item?.part_code === 'spiro_boru';
      const qty = isSpiro ? 1 : Number(row.querySelector('.cart-qty').value);
      const inputs = isSpiro ? { ...item.inputs, uzunluk: metreInput.value } : {};
      const res = await fetch('/api/cart/items/' + id, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ part_code: isSpiro ? 'spiro_boru' : '', inputs, quantity: qty, profit_rate: 0 }),
      });
      if (res.ok) {
        state.cart = (await res.json()).cart;
        renderCart();
      }
    });
  }
  for (const btn of document.querySelectorAll('.cart-delete')) {
    btn.addEventListener('click', async () => {
      const id = Number(btn.closest('.cart-item').dataset.id);
      const res = await fetch('/api/cart/items/' + id, { method: 'DELETE' });
      if (res.ok) {
        state.cart = (await res.json()).cart;
        renderCart();
      }
    });
  }
}

async function refreshCart() {
  const response = await fetch('/api/cart');
  state.cart = await response.json();
  renderCart();
}

document.querySelector('#part-form')?.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!state.selected) return;
  if (document.querySelector('#kollar_esit')?.checked) applyEqualArms(true);
  const form = new FormData(event.currentTarget);
  const entries = Object.fromEntries(form.entries());
  const quantity = Number(entries.quantity || 1);
  entries.boya_ekle = document.querySelector('#boya_ekle')?.checked || false;
  delete entries.quantity;
  const response = await fetch('/api/cart/items', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ part_code: state.selected.code, inputs: entries, quantity, profit_rate: 0 }),
  });
  if (!response.ok) {
    showToast('Kalem eklenemedi. Lütfen ölçüleri kontrol edin.', 'error');
    return;
  }
  const data = await response.json();
  state.cart = data.cart;
  closeModal();
  renderCart();
  showToast('Parça sepete eklendi.', 'success');
});

document.querySelector('#quote-btn')?.addEventListener('click', async () => {
  const name = prompt('Müşteri / Firma Adı:') || '';
  if (!name.trim()) {
    showToast('Lütfen bir isim girin.', 'error');
    return;
  }
  const response = await fetch('/api/quotes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ customer_name: name, shipping_amount: 0 }),
  });
  if (!response.ok) {
    showToast('Teklif talebi oluşturulamadı. Sepet boş olabilir.', 'error');
    return;
  }
  const data = await response.json();
  document.querySelector('#cart').innerHTML = `<p class="success">Teklif talebiniz alındı. Teklif No: #${data.quote_id}</p>`;
  document.querySelector('#quote-btn').disabled = true;
  state.cart = { items: [], total: 0 };
  updateCartMenu();
  showToast(`Teklif talebiniz oluşturuldu. Teklif No: #${data.quote_id}`, 'success');
});

document.querySelector('.modal-close')?.addEventListener('click', closeModal);
document.querySelector('#cart-menu')?.addEventListener('click', openCart);
document.querySelector('.cart-close')?.addEventListener('click', closeCart);
document.querySelector('#kollar_esit')?.addEventListener('change', (event) => {
  applyEqualArms(event.currentTarget.checked);
});
document.querySelector('#dynamic-fields')?.addEventListener('focusin', (event) => {
  if (event.target instanceof HTMLInputElement) activateDimensionField(event.target.name);
});
document.querySelector('#dynamic-fields')?.addEventListener('input', (event) => {
  if (!(event.target instanceof HTMLInputElement)) return;
  updateDimensionBadge(event.target.name);
  updateComputedFields(event.target.name);
  if (!document.querySelector('#kollar_esit')?.checked) return;
  const pairs = state.selected?.equal_arm_pairs || [];
  const pair = pairs.find(item => item.source === event.target.name);
  if (!pair) return;
  const target = document.querySelector('#part-form').elements.namedItem(pair.target);
  if (target instanceof HTMLInputElement) {
    target.value = event.target.value;
    updateDimensionBadge(pair.target);
  }
});
document.querySelector('#part-modal')?.addEventListener('click', (event) => {
  if (event.target === event.currentTarget) closeModal();
});
document.querySelector('#cart-modal')?.addEventListener('click', (event) => {
  if (event.target === event.currentTarget) closeCart();
});
document.addEventListener('keydown', (event) => {
  if (event.key !== 'Escape') return;
  if (document.querySelector('#cart-modal')?.classList.contains('open')) closeCart();
  else closeModal();
});

async function loadIzolasyonOptions() {
  const sel = document.querySelector('#izolasyon_ozellik_id');
  if (!sel) return;
  try {
    const res = await fetch('/api/material-options/izolasyon');
    const data = await res.json();
    for (const opt of data.items) {
      const el = document.createElement('option');
      el.value = opt.id;
      el.textContent = opt.option_name;
      sel.appendChild(el);
    }
    sortSelectOptions(sel);
  } catch { /* ignore */ }
}

async function loadSacOptions() {
  const sel = document.querySelector('#sac_kalinlik_mm');
  if (!sel) return;
  const selectedValue = sel.value;
  const res = await fetch('/api/material-options/sac');
  const data = await res.json();
  sel.innerHTML = '';
  if (!data.items.length) {
    sel.innerHTML = '<option value="">Sac stokta yok</option>';
    sel.disabled = true;
    return;
  }
  for (const opt of data.items) {
    const value = String(opt.option_name).trim().split(/\s+/)[0].replace(',', '.');
    const el = document.createElement('option');
    el.value = value;
    el.textContent = opt.option_name;
    sel.appendChild(el);
  }
  sortSelectOptions(sel);
  sel.value = Array.from(sel.options).some(option => option.value === selectedValue) ? selectedValue : sel.options[0].value;
  sel.disabled = false;
}

if (document.querySelector('#parts')) {
  loadParts().catch((error) => {
    console.error(error);
    document.querySelector('#parts').innerHTML = '<p>Parça listesi yüklenemedi.</p>';
  });
  loadIzolasyonOptions().catch(console.error);
  loadSacOptions().catch(console.error);
  refreshCart().catch(console.error);
}
