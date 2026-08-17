var pendingCarts = [];
var partConfigs = {};
var quoteCustomerCartId = null;
var contactSearchTimer = null;

function escapeHtml(value) {
  return String(value || '').replace(/[&<>'"]/g, function(char) {
    return {'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char];
  });
}

function renderPendingCarts(carts) {
  var root = document.querySelector('#pending-carts');
  if (!root) return;
  if (!carts.length) {
    root.innerHTML = '<p class="muted">Bekleyen sepet yok.</p>';
    return;
  }
  root.innerHTML = carts.map(function(cart) {
    var owner = cart.customer_name || cart.whatsapp_phone || 'Tarayıcı oturumu';
    var items = cart.items.map(function(item) {
      var quantity = ['spiro_boru', 'dikdortgen_kanal'].includes(item.part_code)
        ? '<span>' + escapeHtml(item.sales_quantity_text) + ' ' + escapeHtml(item.sales_unit_label) + '</span>'
        : '<span>' + item.quantity + ' adet</span>';
      return '<li data-cart-id="' + cart.id + '" data-item-id="' + item.id + '"><strong>' + escapeHtml(item.part_name) + '</strong><small>' + escapeHtml(item.measure) + '</small>' + quantity + '<div class="pending-item-actions"><button class="edit-cart-item" type="button">Düzenle</button><button class="delete-cart-item" type="button">Sil</button></div><form class="pending-item-editor" hidden></form></li>';
    }).join('');
    return '<article class="pending-cart-card" data-cart-id="' + cart.id + '"><header><div><span class="cart-admin-id">Sepet #' + cart.id + '</span><h3>' + escapeHtml(owner) + '</h3><small>' + escapeHtml(cart.created_at) + ' · ' + cart.item_count + ' kalem</small></div><div class="pending-cart-actions"><button class="quote-cart" type="button">Teklif Oluştur</button><button class="delete-cart" type="button">Sepeti Sil</button></div></header><ul>' + items + '</ul></article>';
  }).join('');
  attachCartActions();
}

async function loadPendingCarts() {
  var root = document.querySelector('#pending-carts');
  try {
    var responses = await Promise.all([fetch('/api/admin/carts'), fetch('/api/parts')]);
    if (!responses[0].ok || !responses[1].ok) throw Error();
    pendingCarts = (await responses[0].json()).items;
    partConfigs = {};
    (await responses[1].json()).items.forEach(function(part) { partConfigs[part.code] = part; });
    renderPendingCarts(pendingCarts);
  } catch (error) {
    root.innerHTML = '<p class="error">Sepetler yüklenemedi.</p>';
  }
}

function findCartItem(cartId, itemId) {
  var cart = pendingCarts.find(function(row) { return row.id === cartId; });
  return cart ? cart.items.find(function(item) { return item.id === itemId; }) : null;
}

function openItemEditor(row) {
  var cartId = Number(row.dataset.cartId);
  var item = findCartItem(cartId, Number(row.dataset.itemId));
  var form = row.querySelector('.pending-item-editor');
  var config = item && partConfigs[item.part_code];
  if (!item || !config || !form) return;
  var fields = config.fields.map(function(field) {
    return '<label>' + escapeHtml(field.label) + '<input name="' + escapeHtml(field.name) + '" type="number" step="0.01" value="' + escapeHtml(item.inputs[field.name] || '') + '" required></label>';
  }).join('');
  var quantity = '<label>Adet<input name="quantity" type="number" min="1" value="' + item.quantity + '" required></label>';
  form.innerHTML = '<div class="pending-editor-fields">' + fields + quantity + '</div><div><button type="submit">Kaydet</button><button class="close-item-editor" type="button">Vazgeç</button></div>';
  form.hidden = false;
  form.querySelector('.close-item-editor').addEventListener('click', function() { form.hidden = true; });
  form.addEventListener('submit', function(event) { event.preventDefault(); saveItemEditor(form); }, {once:true});
}

async function saveItemEditor(form) {
  var row = form.closest('li');
  var cartId = Number(row.dataset.cartId);
  var item = findCartItem(cartId, Number(row.dataset.itemId));
  var data = new FormData(form);
  var inputs = Object.assign({}, item.inputs);
  Object.keys(partConfigs[item.part_code].fields.reduce(function(result, field) { result[field.name] = true; return result; }, {})).forEach(function(name) { inputs[name] = data.get(name); });
  var quantity = Number(data.get('quantity'));
  var res = await fetch('/api/admin/carts/' + cartId + '/items/' + item.id, { method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({part_code:item.part_code, inputs:inputs, quantity:quantity, profit_rate:0}) });
  if (!res.ok) { alert('Kalem kaydedilemedi.'); return; }
  loadPendingCarts();
}

async function loadParasutContacts(query) {
  var options = document.querySelector('#parasut-customer-options');
  var status = document.querySelector('#parasut-contact-status');
  if (!options || !status) return;
  status.className = 'muted';
  status.textContent = 'Paraşüt müşterileri aranıyor...';
  try {
    var response = await fetch('/api/admin/parasut/contacts?q=' + encodeURIComponent(query || ''));
    if (!response.ok) throw Error();
    var contacts = (await response.json()).items || [];
    options.innerHTML = contacts.map(function(contact) {
      var detail = [contact.tax_number ? 'VKN/TCKN: ' + contact.tax_number : '', contact.phone || ''].filter(Boolean).join(' · ');
      return '<option value="' + escapeHtml(contact.name) + '" label="' + escapeHtml(detail) + '"></option>';
    }).join('');
    status.textContent = contacts.length ? contacts.length + ' Paraşüt müşterisi bulundu.' : 'Eşleşen Paraşüt müşterisi bulunamadı; yeni ad yazabilirsiniz.';
  } catch (error) {
    options.innerHTML = '';
    status.className = 'error';
    status.textContent = 'Paraşüt müşteri listesi alınamadı. Firma adını elle yazabilirsiniz.';
  }
}

function openCustomerPicker(card) {
  var modal = document.querySelector('#customer-picker-modal');
  var input = document.querySelector('#customer-picker-input');
  var currentName = card.querySelector('h3').textContent.trim();
  quoteCustomerCartId = Number(card.dataset.cartId);
  input.value = currentName === 'Tarayıcı oturumu' ? '' : currentName;
  modal.hidden = false;
  document.body.classList.add('modal-open');
  loadParasutContacts(input.value);
  setTimeout(function() { input.focus(); input.select(); }, 0);
}

function closeCustomerPicker() {
  document.querySelector('#customer-picker-modal').hidden = true;
  document.body.classList.remove('modal-open');
  quoteCustomerCartId = null;
}

async function createQuoteForCustomer(event) {
  event.preventDefault();
  var input = document.querySelector('#customer-picker-input');
  var button = document.querySelector('#customer-picker-submit');
  var name = input.value.trim();
  if (!name || !quoteCustomerCartId) return;
  button.disabled = true;
  button.textContent = 'Oluşturuluyor...';
  try {
    var response = await fetch('/api/admin/carts/' + quoteCustomerCartId + '/quote', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({customer_name:name, shipping_amount:0}),
    });
    if (!response.ok) throw Error();
    var data = await response.json();
    closeCustomerPicker();
    alert('Teklif #' + data.quote_id + ' oluşturuldu.');
    loadPendingCarts();
  } catch (error) {
    alert('Teklif oluşturulamadı.');
  } finally {
    button.disabled = false;
    button.textContent = 'Teklif Oluştur';
  }
}

function attachCartActions() {
  document.querySelectorAll('.edit-cart-item').forEach(function(button) { button.addEventListener('click', function() { openItemEditor(button.closest('li')); }); });
  document.querySelectorAll('.delete-cart-item').forEach(function(button) { button.addEventListener('click', async function() { var row = button.closest('li'); if (!confirm('Bu kalem silinsin mi?')) return; var res = await fetch('/api/admin/carts/' + row.dataset.cartId + '/items/' + row.dataset.itemId, {method:'DELETE'}); if (!res.ok) { alert('Kalem silinemedi.'); return; } loadPendingCarts(); }); });
  document.querySelectorAll('.delete-cart').forEach(function(button) { button.addEventListener('click', async function() { var card = button.closest('.pending-cart-card'); if (!confirm('Bu sepet silinsin mi?')) return; var res = await fetch('/api/admin/carts/' + card.dataset.cartId, {method:'DELETE'}); if (!res.ok) { alert('Sepet silinemedi.'); return; } loadPendingCarts(); }); });
  document.querySelectorAll('.quote-cart').forEach(function(button) { button.addEventListener('click', function() { openCustomerPicker(button.closest('.pending-cart-card')); }); });
}

document.querySelector('#refresh-carts')?.addEventListener('click', loadPendingCarts);
document.querySelector('#customer-picker-form')?.addEventListener('submit', createQuoteForCustomer);
document.querySelector('#customer-picker-close')?.addEventListener('click', closeCustomerPicker);
document.querySelector('#customer-picker-cancel')?.addEventListener('click', closeCustomerPicker);
document.querySelector('#customer-picker-modal')?.addEventListener('click', function(event) { if (event.target.dataset.close) closeCustomerPicker(); });
document.querySelector('#customer-picker-input')?.addEventListener('input', function(event) {
  var query = event.currentTarget.value.trim();
  clearTimeout(contactSearchTimer);
  contactSearchTimer = setTimeout(function() { loadParasutContacts(query); }, 300);
});
document.addEventListener('keydown', function(event) { if (event.key === 'Escape' && !document.querySelector('#customer-picker-modal')?.hidden) closeCustomerPicker(); });
loadPendingCarts();
