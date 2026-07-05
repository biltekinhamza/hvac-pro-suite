const quotesState = { quotes: [], selectedId: null };

async function loadQuotes() {
  const response = await fetch('/api/admin/quotes');
  const data = await response.json();
  quotesState.quotes = data.items;
  renderQuotes();
}

function formatMoney(value) {
  return Number(value || 0).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' TL';
}

function renderQuotes() {
  const body = document.querySelector('#quotes-body');
  if (!quotesState.quotes.length) {
    body.innerHTML = '<tr><td colspan="5">Henüz teklif yok.</td></tr>';
    return;
  }
  body.innerHTML = quotesState.quotes.map((quote) => `
    <tr class="click-row ${quotesState.selectedId === quote.id ? 'selected' : ''}" data-id="${quote.id}">
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
}

async function loadQuoteDetail(id) {
  quotesState.selectedId = id;
  renderQuotes();
  const response = await fetch(`/api/admin/quotes/${id}`);
  if (!response.ok) {
    document.querySelector('#quote-detail').innerHTML = '<p class="error">Teklif detayı alınamadı.</p>';
    return;
  }
  const data = await response.json();
  renderQuoteDetail(data);
}

function renderQuoteDetail(data) {
  const quote = data.quote;
  const items = data.items.map((item) => `
    <div class="detail-item">
      <strong>${item.part_name}</strong>
      <span>${item.quantity} adet | ${formatMoney(item.unit_price)} | ${formatMoney(item.line_total)}</span>
      <small>${Object.entries(item.inputs).filter(([key]) => !key.includes('ozellik') && !key.includes('ekle')).map(([key, value]) => `${key}: ${value}`).join(' · ')}</small>
    </div>
  `).join('');

  const sentInfo = quote.parasut_offer_id
    ? `<p class="success">Paraşüt teklif ID: ${quote.parasut_offer_id}</p>`
    : '';
  const sendButton = quote.parasut_offer_id
    ? '<button type="button" disabled>Paraşüt\'e Aktarıldı</button>'
    : '<button id="send-parasut" type="button">Paraşüt\'e Aktar</button>';

  document.querySelector('#quote-detail').innerHTML = `
    <div class="detail-head">
      <h3>#${quote.id} ${quote.customer_name}</h3>
      <p><strong>Durum:</strong> ${quote.status}</p>
      <p><strong>Kâr Oranı:</strong> %${quote.profit_rate}</p>
      <p><strong>Toplam:</strong> ${formatMoney(quote.total_amount)}</p>
      ${sentInfo}
    </div>
    <form id="profit-form" class="form-stack quote-form">
      <label>
        Tüm Ürünlere Kâr Oranı (%)
        <input name="profit_rate" type="number" min="0" step="0.01" value="${quote.profit_rate}">
      </label>
      <button type="submit">Kârı Uygula</button>
    </form>
    <div class="detail-list">${items}</div>
    ${sendButton}
  `;
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
    renderQuoteDetail({ quote: updated.quote, items: updated.items });
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

loadQuotes().catch((error) => {
  console.error(error);
  document.querySelector('#quotes-body').innerHTML = '<tr><td colspan="5">Teklifler yüklenemedi.</td></tr>';
});
