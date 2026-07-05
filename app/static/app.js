const state = { parts: [], selected: null, cart: [] };

async function loadParts() {
  const response = await fetch('/api/parts');
  const data = await response.json();
  state.parts = data.items;
  renderParts();
}

function renderParts() {
  const root = document.querySelector('#parts');
  root.innerHTML = '';
  for (const part of state.parts) {
    const card = document.createElement('button');
    card.type = 'button';
    card.className = 'part-card' + (state.selected?.code === part.code ? ' active' : '');
    const image = part.image ? `/static/parcalar/${part.image}` : '';
    card.innerHTML = `
      ${image ? `<img class="part-image" src="${image}" alt="${part.title}" loading="lazy">` : ''}
      <div class="part-card-body">
        <div class="group">${part.group}</div>
        <h3>${part.title}</h3>
      </div>
    `;
    card.addEventListener('click', () => selectPart(part));
    root.appendChild(card);
  }
}

function selectPart(part) {
  state.selected = part;
  document.querySelector('#selected-title').textContent = part.title;
  const fields = document.querySelector('#dynamic-fields');
  fields.innerHTML = '';
  for (const field of part.fields) {
    const label = document.createElement('label');
    label.textContent = field.label;
    const input = document.createElement('input');
    input.name = field.name;
    input.type = 'number';
    input.step = '0.01';
    input.required = true;
    label.appendChild(input);
    fields.appendChild(label);
  }
  renderParts();
  if (window.matchMedia('(max-width: 860px)').matches) {
    document.querySelector('#order-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

function renderCart() {
  const root = document.querySelector('#cart');
  if (!state.cart.items?.length) {
    root.innerHTML = '<h3>Sepet</h3><p class="muted">Henuz kalem yok.</p>';
    return;
  }
  const items = state.cart.items.map((item, index) => `
    <div class="cart-item">
      <strong>${index + 1}. ${item.part_name}</strong>
      <span>${item.quantity} adet</span>
    </div>
  `).join('');
  root.innerHTML = `<h3>Sepet</h3>${items}`;
}

async function refreshCart() {
  const response = await fetch('/api/cart');
  state.cart = await response.json();
  renderCart();
}

document.querySelector('#part-form')?.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!state.selected) return alert('Once parca secin.');
  const form = new FormData(event.currentTarget);
  const entries = Object.fromEntries(form.entries());
  const quantity = Number(entries.quantity || 1);
  delete entries.quantity;
  const response = await fetch('/api/cart/items', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ part_code: state.selected.code, inputs: entries, quantity, profit_rate: 0 }),
  });
  if (!response.ok) return alert('Kalem eklenemedi. Lutfen olculeri kontrol edin.');
  const data = await response.json();
  state.cart = data.cart;
  renderCart();
  for (const input of document.querySelectorAll('#dynamic-fields input')) input.value = '';
  document.querySelector('#quantity').value = 1;
});

document.querySelector('#quote-form')?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const response = await fetch('/api/quotes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ customer_name: form.get('customer_name') || '', shipping_amount: 0 }),
  });
  const root = document.querySelector('#cart');
  if (!response.ok) {
    root.insertAdjacentHTML('beforeend', '<p class="error">Teklif talebi olusturulamadi.</p>');
    return;
  }
  const data = await response.json();
  root.innerHTML = `<h3>Sepet</h3><p class="success">Teklif talebiniz alindi. Teklif No: #${data.quote_id}</p>`;
  state.cart = { items: [], total: 0 };
});

if (document.querySelector('#parts')) {
  loadParts().catch((error) => {
    console.error(error);
    document.querySelector('#parts').innerHTML = '<p>Parca listesi yuklenemedi.</p>';
  });
  refreshCart().catch(console.error);
}
