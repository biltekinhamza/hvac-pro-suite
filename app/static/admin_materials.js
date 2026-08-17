var materialItems = [];
var materialFilter = '';

async function loadLaborRates() {
  var res = await fetch('/api/admin/labor-rates');
  if (!res.ok) throw new Error('labor rates load failed');
  var data = await res.json();
  var fitting = document.querySelector('#fitting-labor-rate');
  var squareDuct = document.querySelector('#square-duct-labor-rate');
  var spiro = document.querySelector('#spiro-labor-rate');
  if (fitting) fitting.value = data.fitting;
  if (squareDuct) squareDuct.value = data.square_duct;
  if (spiro) spiro.value = data.spiro;
}

async function saveLaborRates() {
  var fitting = Number(document.querySelector('#fitting-labor-rate').value);
  var squareDuct = Number(document.querySelector('#square-duct-labor-rate').value);
  var spiro = Number(document.querySelector('#spiro-labor-rate').value);
  var btn = document.querySelector('#btn-save-labor-rates');
  var message = document.querySelector('#labor-rates-message');
  if ([fitting, squareDuct, spiro].some(function(rate) { return !Number.isFinite(rate) || rate < 0; })) {
    if (message) message.innerHTML = '<p class="error">Oranlar sıfır veya pozitif olmalıdır.</p>';
    return;
  }
  if (btn) { btn.disabled = true; btn.textContent = 'Kaydediliyor...'; }
  try {
    var res = await fetch('/api/admin/labor-rates', {
      method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({fitting: fitting, square_duct: squareDuct, spiro: spiro})
    });
    if (!res.ok) throw Error();
    if (message) message.innerHTML = '<p class="success">İşçilik oranları kaydedildi. Yeni hesaplamalarda uygulanır.</p>';
  } catch(e) {
    if (message) message.innerHTML = '<p class="error">İşçilik oranları kaydedilemedi.</p>';
  }
  if (btn) { btn.disabled = false; btn.textContent = 'Kaydet'; }
}

async function loadMaterials() {
  var res = await fetch('/api/admin/materials');
  if (!res.ok) throw new Error('materials load failed');
  var data = await res.json();
  materialItems = data.items;
  renderMaterials();
}

function renderMaterials() {
  var body = document.querySelector('#materials-body');
  if (!body) return;
  var f = materialFilter.trim().toLocaleLowerCase('tr-TR');
  var items = f ? materialItems.filter(function(it) { return (it.name + ' ' + it.option_name + ' ' + it.unit).toLocaleLowerCase('tr-TR').indexOf(f) !== -1; }) : materialItems;

  if (!items.length) { body.innerHTML = '<tr><td colspan="8">Malzeme bulunamadi.</td></tr>'; return; }

  body.innerHTML = items.map(function(it) {
    var stockManaged = it.name.indexOf('SAC') !== -1 || it.name.indexOf('IZOLASYON') !== -1;
    var availability = stockManaged
      ? '<td><label class="stock-toggle"><input class="material-availability" type="checkbox"' + (it.is_available ? ' checked' : '') + '> Stokta</label></td>'
      : '<td>-</td>';
    return '<tr data-id="' + it.id + '">' +
      '<td>#' + it.id + '</td>' +
      '<td><strong>' + it.name + '</strong></td>' +
      '<td>' + it.option_name + '</td>' +
      '<td>' + it.unit + '</td>' +
      availability +
      '<td><input class="cost-input" type="number" min="0" step="0.01" value="' + it.average_unit_cost + '"> <small>' +
      Number(it.average_unit_cost).toLocaleString('tr-TR', {minimumFractionDigits:2}) + ' TL / ' + it.unit + '</small></td>' +
      '<td><button class="save-material" type="button">Kaydet</button></td>' +
      '<td><button class="delete-material" type="button">Sil</button></td></tr>';
  }).join('');

  var saveButtons = document.querySelectorAll('.save-material');
  for (var i = 0; i < saveButtons.length; i++) {
    saveButtons[i].addEventListener('click', function() { saveMaterial(this.closest('tr')); });
  }
  var deleteButtons = document.querySelectorAll('.delete-material');
  for (var j = 0; j < deleteButtons.length; j++) {
    deleteButtons[j].addEventListener('click', function() { deleteMaterial(this.closest('tr')); });
  }
  var availabilityInputs = document.querySelectorAll('.material-availability');
  for (var k = 0; k < availabilityInputs.length; k++) {
    availabilityInputs[k].addEventListener('change', function() { saveAvailability(this.closest('tr'), this); });
  }
}

async function saveAvailability(row, input) {
  var id = Number(row.dataset.id);
  input.disabled = true;
  try {
    var res = await fetch('/api/admin/materials/' + id + '/availability', {
      method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({is_available: input.checked})
    });
    if (!res.ok) throw Error();
    var data = await res.json();
    for (var i = 0; i < materialItems.length; i++) { if (materialItems[i].id === id) { materialItems[i] = data.item; break; } }
    showMsg(input.checked ? 'Malzeme siparişe açıldı.' : 'Malzeme siparişe kapatıldı.', 'success');
  } catch(e) {
    input.checked = !input.checked;
    showMsg('Stok durumu kaydedilemedi.', 'error');
  }
  input.disabled = false;
}

async function saveMaterial(row) {
  var id = Number(row.dataset.id);
  var input = row.querySelector('.cost-input');
  var btn = row.querySelector('.save-material');
  var val = Number(input ? input.value : 0);
  if (btn) { btn.disabled = true; btn.textContent = 'Kaydediliyor...'; }
  try {
    var res = await fetch('/api/admin/materials/' + id, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({average_unit_cost:val}) });
    if (!res.ok) throw Error();
    var data = await res.json();
    for (var j = 0; j < materialItems.length; j++) { if (materialItems[j].id === id) { materialItems[j] = data.item; break; } }
    showMsg('Fiyat guncellendi.', 'success');
  } catch(e) { showMsg('Fiyat kaydedilemedi.', 'error'); }
  if (btn) { btn.disabled = false; btn.textContent = 'Kaydet'; }
}

async function deleteMaterial(row) {
  var id = Number(row.dataset.id);
  var name = row.children[1] ? row.children[1].textContent.trim() : '';
  var option = row.children[2] ? row.children[2].textContent.trim() : '';
  if (!confirm(name + ' / ' + option + ' silinsin mi?')) return;

  var btn = row.querySelector('.delete-material');
  if (btn) { btn.disabled = true; btn.textContent = 'Siliniyor...'; }
  try {
    var res = await fetch('/api/admin/materials/' + id, { method:'DELETE' });
    if (!res.ok) throw Error();
    materialItems = materialItems.filter(function(it) { return it.id !== id; });
    renderMaterials();
    showMsg('Malzeme silindi.', 'success');
  } catch(e) {
    showMsg('Malzeme silinemedi.', 'error');
    if (btn) { btn.disabled = false; btn.textContent = 'Sil'; }
  }
}

function showMsg(text, type) {
  var el = document.querySelector('#materials-message');
  if (el) el.innerHTML = '<p class="' + type + '">' + text + '</p>';
}

document.querySelector('#material-search')?.addEventListener('input', function(e) {
  materialFilter = e.currentTarget.value;
  renderMaterials();
});

document.querySelector('#btn-save-labor-rates')?.addEventListener('click', saveLaborRates);

// --- Add material ---
document.querySelector('#btn-add-material')?.addEventListener('click', async function() {
  var nameEl = document.querySelector('#add-material-name');
  var optEl = document.querySelector('#add-option-name');
  var costEl = document.querySelector('#add-unit-cost');

  var materialName = (nameEl ? nameEl.value : '').trim().toUpperCase();
  var optionName = optEl ? optEl.value.trim() : '';
  var unitCost = Number(costEl ? costEl.value : 0);

  if (!materialName) { alert('Malzeme adi gerekli.'); return; }
  if (!optionName) { alert('Secenek adi gerekli.'); return; }
  if (unitCost <= 0) { alert('Gecerli birim maliyet girin.'); return; }

  var btn = document.querySelector('#btn-add-material');
  var msg = document.querySelector('#add-message');
  if (btn) { btn.disabled = true; btn.textContent = 'Ekleniyor...'; }
  if (msg) msg.innerHTML = '';

  try {
    var res = await fetch('/api/admin/materials', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ material_name: materialName, option_name: optionName, average_unit_cost: unitCost })
    });
    if (!res.ok) throw Error('Eklenemedi');
    var data = await res.json();
    materialItems.push(data.item);
    if (msg) msg.innerHTML = '<p class="success">Malzeme eklendi.</p>';
    if (nameEl) nameEl.value = '';
    if (optEl) optEl.value = '';
    if (costEl) costEl.value = '';
    renderMaterials();
  } catch(err) {
    if (msg) msg.innerHTML = '<p class="error">Hata: ' + err.message + '</p>';
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Ekle'; }
  }
});

Promise.all([loadMaterials(), loadLaborRates()]).catch(function(err) {
  console.error(err);
  var el = document.querySelector('#materials-body');
  if (el) el.innerHTML = '<tr><td colspan="8">Malzemeler yuklenemedi.</td></tr>';
});
