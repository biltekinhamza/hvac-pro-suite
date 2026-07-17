var state = { items: [], partFilter: '', capFilter: '' };

var PART_NAMES = {
  spiro_boru: 'Spiro Boru (m)',
  yuvarlak_dirsek_90: '90 Dirsek',
  yuvarlak_dirsek_45: '45 Dirsek',
  yuvarlak_te: 'T',
  yuvarlak_reduksiyon: 'Reduksiyon',
  yuvarlak_mason: 'Manson',
  yuvarlak_kelepce: 'Kelepce',
  yuvarlak_klape: 'Klape',
  yuvarlak_jetkap: 'Jetkap',
  kortapa: 'Kortapa',
  yuvarlak_saplama: 'Saplama',
  yuvarlak_sapka: 'Sapka',
};

async function loadPrices() {
  var res = await fetch('/api/admin/round-prices');
  if (!res.ok) throw new Error('Yukleme basarisiz');
  var data = await res.json();
  state.items = data.items;
  renderTable();
  populateFilter();
}

function populateFilter() {
  var sel = document.querySelector('#filter-part');
  if (!sel) return;
  var codes = [];
  for (var i = 0; i < state.items.length; i++) {
    if (codes.indexOf(state.items[i].part_code) === -1) codes.push(state.items[i].part_code);
  }
  codes.sort();
  var html = '<option value="">Tum Parcalar</option>';
  for (var j = 0; j < codes.length; j++) {
    html += '<option value="' + codes[j] + '">' + (PART_NAMES[codes[j]] || codes[j]) + '</option>';
  }
  sel.innerHTML = html;
}

function renderTable() {
  var body = document.querySelector('#prices-body');
  if (!body) return;
  var filtered = state.items;
  if (state.partFilter) filtered = filtered.filter(function (i) { return i.part_code === state.partFilter; });
  if (state.capFilter) filtered = filtered.filter(function (i) { return String(i.cap_mm).indexOf(state.capFilter) !== -1; });

  if (!filtered.length) {
    body.innerHTML = '<tr><td colspan="4">Fiyat bulunamadi.</td></tr>';
    return;
  }

  body.innerHTML = filtered.map(function (item) {
    return '<tr data-part="' + item.part_code + '" data-cap="' + item.cap_mm + '">' +
      '<td><strong>' + (PART_NAMES[item.part_code] || item.part_code) + '</strong></td>' +
      '<td>' + item.cap_mm + ' mm</td>' +
      '<td><input class="price-input" type="number" min="0" step="0.01" value="' + item.price + '"></td>' +
      '<td><button class="save-round-price" type="button">Kaydet</button></td>' +
      '</tr>';
  }).join('');

  for (var btn of document.querySelectorAll('.save-round-price')) {
    btn.addEventListener('click', function () { savePrice(this.closest('tr')); });
  }
}

async function savePrice(row) {
  var partCode = row.dataset.part;
  var capMm = Number(row.dataset.cap);
  var input = row.querySelector('.price-input');
  var button = row.querySelector('.save-round-price');
  var value = Number(input ? input.value : 0);

  if (button) { button.disabled = true; button.textContent = 'Kaydediliyor...'; }

  try {
    var res = await fetch('/api/admin/round-prices/' + encodeURIComponent(partCode) + '/' + capMm, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ average_unit_cost: value }),
    });
    if (!res.ok) throw new Error('error');
    for (var i = 0; i < state.items.length; i++) {
      if (state.items[i].part_code === partCode && state.items[i].cap_mm === capMm) { state.items[i].price = value; break; }
    }
    if (button) { button.disabled = false; button.textContent = 'Kaydet'; }
  } catch (err) {
    if (button) { button.disabled = false; button.textContent = 'Kaydet'; }
    alert('Fiyat kaydedilemedi.');
  }
}

document.querySelector('#filter-part')?.addEventListener('change', function (e) {
  state.partFilter = e.currentTarget.value;
  renderTable();
});

document.querySelector('#filter-cap')?.addEventListener('input', function (e) {
  state.capFilter = e.currentTarget.value;
  renderTable();
});

document.querySelector('#btn-upload')?.addEventListener('click', async function () {
  var input = document.querySelector('#csv-file');
  var file = input ? input.files[0] : null;
  if (!file) { alert('Lutfen bir CSV dosyasi secin.'); return; }

  var btn = document.querySelector('#btn-upload');
  var msg = document.querySelector('#upload-message');
  if (btn) { btn.disabled = true; btn.textContent = 'Yukleniyor...'; }
  if (msg) msg.innerHTML = '';

  var form = new FormData();
  form.append('file', file);

  try {
    var res = await fetch('/api/admin/round-prices/upload', { method: 'POST', body: form });
    if (!res.ok) throw new Error('Yukleme basarisiz');
    var data = await res.json();
    if (msg) msg.innerHTML = '<p class="success">' + data.count + ' fiyat basariyla guncellendi.</p>';
    await loadPrices();
  } catch (err) {
    if (msg) msg.innerHTML = '<p class="error">Hata: ' + err.message + '</p>';
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Yukle ve Guncelle'; }
    if (input) input.value = '';
  }
});

loadPrices().catch(function (err) {
  console.error(err);
  var el = document.querySelector('#prices-body');
  if (el) el.innerHTML = '<tr><td colspan="4">Fiyatlar yuklenemedi.</td></tr>';
});
