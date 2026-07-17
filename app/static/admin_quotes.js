const quotesState = { quotes: [], selectedId: null, selectedMergeIds: new Set(), parts: [], izolasyonOptions: [] };

async function loadQuotes() {
  const response = await fetch('/api/admin/quotes');
  const data = await response.json();
  quotesState.quotes = data.items;
  renderQuotes();
}

async function loadAdminFormData() {
  const [partsRes, izoRes] = await Promise.all([
    fetch('/api/parts'),
    fetch('/api/material-options/izolasyon'),
  ]);
  quotesState.parts = (await partsRes.json()).items || [];
  quotesState.izolasyonOptions = (await izoRes.json()).items || [];
}

function formatMoney(value) {
  return Number(value || 0).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' TL';
}

function renderQuotes() {
  const body = document.querySelector('#quotes-body');
  if (!quotesState.quotes.length) {
    body.innerHTML = '<tr><td colspan="6">Henüz teklif yok.</td></tr>';
    return;
  }
  body.innerHTML = quotesState.quotes.map((quote) => `
    <tr class="click-row ${quotesState.selectedId === quote.id ? 'selected' : ''}" data-id="${quote.id}">
      <td><input class="quote-merge-check" type="checkbox" data-id="${quote.id}" ${quotesState.selectedMergeIds.has(quote.id) ? 'checked' : ''} ${quote.status === 'merged' ? 'disabled' : ''}></td>
      <td>#${quote.id}</td>
      <td>${quote.customer_name}</td>
      <td><span class="status-pill">${quote.status}</span></td>
      <td>${formatMoney(quote.total_amount)}<br><small>Kâr: %${quote.profit_rate}</small></td>
      <td>${quote.created_at}</td>
    </tr>
  `).join('');
  for (const row of document.querySelectorAll('.click-row')) {
    row.addEventListener('click', () => loadQuoteDetail(Number(row.dataset.id)));
  }
  for (const check of document.querySelectorAll('.quote-merge-check')) {
    check.addEventListener('click', (event) => event.stopPropagation());
    check.addEventListener('change', () => {
      const id = Number(check.dataset.id);
      if (check.checked) quotesState.selectedMergeIds.add(id);
      else quotesState.selectedMergeIds.delete(id);
    });
  }
}

async function loadQuoteDetail(id) {
  quotesState.selectedId = id;
  renderQuotes();
  openQuoteDetailModal('<p class="muted">Teklif detayı yükleniyor...</p>');
  const response = await fetch(`/api/admin/quotes/${id}`);
  if (!response.ok) {
    document.querySelector('#quote-detail').innerHTML = '<p class="error">Teklif detayı alınamadı.</p>';
    return;
  }
  const data = await response.json();
  renderQuoteDetail(data);
}

function openQuoteDetailModal(content = '') {
  const modal = document.querySelector('#quote-detail-modal');
  if (!modal) return;
  if (content) document.querySelector('#quote-detail').innerHTML = content;
  modal.hidden = false;
  document.body.classList.add('modal-open');
}

function closeQuoteDetailModal() {
  const modal = document.querySelector('#quote-detail-modal');
  if (!modal) return;
  modal.hidden = true;
  document.body.classList.remove('modal-open');
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 3 });
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[ch]));
}

function izolasyonOptionsHtml(selected = '') {
  const current = String(selected || '');
  return '<option value="">İzolasyon yok</option>' + quotesState.izolasyonOptions.map((opt) => {
    const value = String(opt.id);
    return `<option value="${value}" ${value === current ? 'selected' : ''}>${escapeHtml(opt.option_name)}</option>`;
  }).join('');
}

function normalizeOptionNumber(value) {
  const number = Number(String(value || '').replace(',', '.'));
  return Number.isFinite(number) ? number.toFixed(2) : String(value || '');
}

function partOptionsHtml(selected = '') {
  return quotesState.parts.map((part) => `<option value="${escapeHtml(part.code)}" ${part.code === selected ? 'selected' : ''}>${escapeHtml(part.title)}</option>`).join('');
}

function partFieldsHtml(part, inputs = {}) {
  if (!part) return '';
  return part.fields.map((field) => `
    <label>
      ${escapeHtml(field.label)}
      <input name="${escapeHtml(field.name)}" type="number" step="0.01" value="${escapeHtml(inputs[field.name] ?? '')}" required>
    </label>
  `).join('');
}

function sharedQuoteFieldsHtml(prefix, inputs = {}, quantity = 1) {
  const selectedThickness = normalizeOptionNumber(inputs.sac_kalinlik_mm || '0.60');
  return `
    <label>
      Sac Kalınlığı (mm)
      <select name="sac_kalinlik_mm">
        ${['0.50', '0.60', '0.65', '0.70', '0.80'].map((v) => `<option value="${v}" ${selectedThickness === v ? 'selected' : ''}>${v} mm</option>`).join('')}
      </select>
    </label>
    <label>
      İzolasyon
      <select name="izolasyon_ozellik_id">${izolasyonOptionsHtml(inputs.izolasyon_ozellik_id)}</select>
    </label>
    <label class="boya-label">
      <input name="boya_ekle" type="checkbox" ${inputs.boya_ekle === true || String(inputs.boya_ekle).toLowerCase() === 'true' || String(inputs.boya_ekle).toLowerCase() === 'on' ? 'checked' : ''}>
      <span>Boya Ekle</span>
    </label>
    <label>
      Adet
      <input name="quantity" type="number" min="1" value="${escapeHtml(quantity)}" required>
    </label>
  `;
}

function collectFormInputs(form) {
  const data = Object.fromEntries(new FormData(form).entries());
  const quantity = Number(data.quantity || 1);
  data.boya_ekle = form.querySelector('[name="boya_ekle"]')?.checked || false;
  delete data.quantity;
  delete data.part_code;
  return { inputs: data, quantity };
}

function renderQuoteDetail(data) {
  const quote = data.quote;
  const summary = data.summary || { total_cut_m2: 0, total_kg: 0 };
  const title = document.querySelector('#quote-detail-title');
  if (title) title.textContent = `Teklif #${quote.id} - ${quote.customer_name}`;
  const items = data.items.map((item) => {
    const detailParts = Array.isArray(item.detail_parts) && item.detail_parts.length
      ? item.detail_parts
      : [`${item.quantity} adet`, item.display].filter(Boolean);
    const detailText = detailParts.map(escapeHtml).join(' · ');
    return `
    <div class="detail-item" data-item-id="${item.id}">
      <strong>${escapeHtml(item.display_name || item.part_name)}</strong>
      <small class="dim-readable">${detailText}</small>
      <span class="line-total"><strong>Tutar:</strong> ${formatMoney(item.line_total)}</span>
      <small class="dim-summary">${formatNumber(item.cut_area_m2 * item.quantity)} m² · ${formatNumber(item.weight_kg * item.quantity)} kg</small>
      <div class="quote-item-actions">
        <button class="edit-quote-item" type="button">Düzenle</button>
        <button class="delete-quote-item" type="button">Sil</button>
      </div>
    </div>
  `;
  }).join('');

  const sentInfo = quote.parasut_offer_id
    ? `<p class="success">Paraşüt teklif ID: ${quote.parasut_offer_id}</p>`
    : '';
  const sendButton = quote.parasut_offer_id
    ? '<button id="send-parasut" type="button" class="btn-warning">Paraşüt\'e Tekrar Gönder</button>'
    : '<button id="send-parasut" type="button">Paraşüt\'e Aktar</button>';

  document.querySelector('#quote-detail').innerHTML = `
    <div class="detail-head">
      <h3>#${quote.id} ${quote.customer_name}</h3>
      <p><strong>Durum:</strong> ${quote.status}</p>
      <p><strong>Kâr Oranı:</strong> %${quote.profit_rate}</p>
      <p><strong>Nakliye:</strong> ${formatMoney(quote.shipping_amount)}</p>
      <p><strong>Toplam:</strong> ${formatMoney(quote.total_amount)}</p>
      ${sentInfo}
    </div>
    <div class="dim-totals">
      <span><strong>Toplam Kesilen:</strong> ${formatNumber(summary.total_cut_m2)} m²</span>
      <span><strong>Toplam Ağırlık:</strong> ${formatNumber(summary.total_kg)} kg</span>
    </div>
    <form id="profit-form" class="form-stack quote-form">
      <label>
        Tüm Ürünlere Kâr Oranı (%)
        <input name="profit_rate" type="number" min="0" step="0.01" value="${quote.profit_rate}">
      </label>
      <button type="submit">Kârı Uygula</button>
    </form>
    <form id="shipping-form" class="form-stack quote-form">
      <label>
        Nakliye Tutarı (TL)
        <input name="shipping_amount" type="number" min="0" step="0.01" value="${quote.shipping_amount || 0}">
      </label>
      <button type="submit">Nakliyeyi Uygula</button>
    </form>
    <button id="open-add-item" type="button" class="quote-add-button">Kalem Ekle</button>
    <div id="quote-item-editor" class="quote-edit-form" hidden></div>
    <div class="detail-list">${items}</div>
    ${sendButton}
  `;
  attachQuoteItemEvents(quote, data.items || []);
  document.querySelector('#profit-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const response = await fetch(`/api/admin/quotes/${quote.id}/profit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profit_rate: Number(form.get('profit_rate') || 0) }),
    });
    if (!response.ok) return alert('Kâr oranı uygulanamadı.');
    const updated = await response.json();
    const index = quotesState.quotes.findIndex((item) => item.id === quote.id);
    if (index >= 0) quotesState.quotes[index] = updated.quote;
    renderQuotes();
    renderQuoteDetail({ quote: updated.quote, items: updated.items, summary: updated.summary });
  });
  document.querySelector('#shipping-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const response = await fetch(`/api/admin/quotes/${quote.id}/shipping`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ shipping_amount: Number(form.get('shipping_amount') || 0) }),
    });
    if (!response.ok) return alert('Nakliye tutarı uygulanamadı.');
    const updated = await response.json();
    const index = quotesState.quotes.findIndex((item) => item.id === quote.id);
    if (index >= 0) quotesState.quotes[index] = updated.quote;
    renderQuotes();
    renderQuoteDetail({ quote: updated.quote, items: updated.items, summary: updated.summary });
  });
  document.querySelector('#send-parasut')?.addEventListener('click', async () => {
    if (!confirm('Bu teklifi Paraşüt’e aktarmak istiyor musunuz?')) return;
    const button = document.querySelector('#send-parasut');
    button.disabled = true;
    button.textContent = 'Aktarılıyor...';
    const response = await fetch(`/api/admin/quotes/${quote.id}/send-to-parasut`, { method: 'POST' });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Aktarım başarısız.' }));
      alert(error.detail || 'Aktarım başarısız.');
      button.disabled = false;
      button.textContent = 'Paraşüt\'e Aktar';
      return;
    }
    const result = await response.json();
    alert(`Paraşüt teklif ID: ${result.parasut_offer_id}`);
    await loadQuotes();
    await loadQuoteDetail(quote.id);
  });
}

function renderQuoteItemEditor(quote, item = null) {
  const editor = document.querySelector('#quote-item-editor');
  if (!editor) return;
  const partCode = item?.part_code || quotesState.parts[0]?.code || '';
  const part = quotesState.parts.find((p) => p.code === partCode);
  const title = item ? 'Kalem Düzenle' : 'Kalem Ekle';
  editor.hidden = false;
  editor.innerHTML = `
    <form id="quote-item-editor-form" class="form-stack" data-item-id="${item?.id || ''}">
      <div class="quote-editor-head">
        <h4>${title}</h4>
        <button id="close-item-editor" type="button">Kapat</button>
      </div>
      <label>
        Parça
        <select id="quote-editor-part" name="part_code">${partOptionsHtml(partCode)}</select>
      </label>
      <div id="quote-editor-fields" class="quote-field-grid">
        ${partFieldsHtml(part, item?.inputs || {})}
        ${sharedQuoteFieldsHtml('editor', item?.inputs || {}, item?.quantity || 1)}
      </div>
      <button type="submit">${item ? 'Kalemi Güncelle' : 'Kalem Ekle'}</button>
    </form>
  `;
  editor.scrollIntoView({ behavior: 'smooth', block: 'start' });
  editor.querySelector('input, select')?.focus({ preventScroll: true });
  document.querySelector('#close-item-editor')?.addEventListener('click', () => { editor.hidden = true; editor.innerHTML = ''; });
  document.querySelector('#quote-editor-part')?.addEventListener('change', (event) => {
    const selectedPart = quotesState.parts.find((p) => p.code === event.currentTarget.value);
    const fields = document.querySelector('#quote-editor-fields');
    if (fields) fields.innerHTML = partFieldsHtml(selectedPart) + sharedQuoteFieldsHtml('editor', {}, 1);
  });
  document.querySelector('#quote-item-editor-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const selectedPartCode = form.querySelector('[name="part_code"]').value;
    const payload = collectFormInputs(form);
    const itemId = form.dataset.itemId;
    const response = await fetch(itemId ? `/api/admin/quotes/${quote.id}/items/${itemId}` : `/api/admin/quotes/${quote.id}/items`, {
      method: itemId ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ part_code: selectedPartCode, inputs: payload.inputs, quantity: payload.quantity, profit_rate: 0 }),
    });
    if (!response.ok) return alert(itemId ? 'Kalem güncellenemedi.' : 'Kalem eklenemedi. Ölçüleri kontrol edin.');
    const updated = await response.json();
    await loadQuotes();
    renderQuoteDetail(updated);
  });
}

function attachQuoteItemEvents(quote, items) {
  document.querySelector('#open-add-item')?.addEventListener('click', () => renderQuoteItemEditor(quote));

  for (const button of document.querySelectorAll('.edit-quote-item')) {
    button.addEventListener('click', () => {
      const row = button.closest('.detail-item');
      const item = items.find((current) => String(current.id) === String(row.dataset.itemId));
      if (item) renderQuoteItemEditor(quote, item);
    });
  }
  for (const button of document.querySelectorAll('.delete-quote-item')) {
    button.addEventListener('click', async () => {
      const row = button.closest('.detail-item');
      if (!confirm('Bu kalem silinsin mi?')) return;
      const response = await fetch(`/api/admin/quotes/${quote.id}/items/${row.dataset.itemId}`, { method: 'DELETE' });
      if (!response.ok) return alert('Kalem silinemedi.');
      const updated = await response.json();
      await loadQuotes();
      renderQuoteDetail(updated);
    });
  }
}

document.querySelector('#merge-quotes')?.addEventListener('click', async () => {
  const ids = Array.from(quotesState.selectedMergeIds);
  if (ids.length < 2) return alert('Birleştirmek için en az iki teklif seçin.');
  if (!confirm(`${ids.length} teklif birleştirilsin mi? Eski teklifler merged yapılacak.`)) return;
  const response = await fetch('/api/admin/quotes/merge', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ quote_ids: ids }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Birleştirme başarısız.' }));
    return alert(error.detail || 'Birleştirme başarısız.');
  }
  const merged = await response.json();
  quotesState.selectedMergeIds.clear();
  await loadQuotes();
  await loadQuoteDetail(merged.quote_id);
});

document.querySelector('#delete-quotes')?.addEventListener('click', async () => {
  const ids = Array.from(quotesState.selectedMergeIds);
  if (!ids.length) return alert('Silmek için en az bir teklif seçin.');
  if (!confirm(`${ids.length} teklif kalıcı olarak silinsin mi?`)) return;
  const response = await fetch('/api/admin/quotes/delete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ quote_ids: ids }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Silme başarısız.' }));
    return alert(error.detail || 'Silme başarısız.');
  }
  const selectedWasOpen = ids.includes(quotesState.selectedId);
  quotesState.selectedMergeIds.clear();
  if (selectedWasOpen) closeQuoteDetailModal();
  quotesState.selectedId = null;
  await loadQuotes();
});

document.querySelector('#quote-detail-close')?.addEventListener('click', closeQuoteDetailModal);
document.querySelector('#quote-detail-modal')?.addEventListener('click', (event) => {
  if (event.target?.dataset?.close === '1') closeQuoteDetailModal();
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') closeQuoteDetailModal();
});

loadAdminFormData().then(loadQuotes).catch((error) => {
  console.error(error);
  document.querySelector('#quotes-body').innerHTML = '<tr><td colspan="6">Teklifler yüklenemedi.</td></tr>';
});
