const materialState = { items: [], filter: '' };

async function loadMaterials() {
  const response = await fetch('/api/admin/materials');
  if (!response.ok) throw new Error('materials load failed');
  const data = await response.json();
  materialState.items = data.items;
  renderMaterials();
}

function formatCost(value) {
  return Number(value || 0).toLocaleString('tr-TR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function materialLabel(item) {
  return `${item.name} ${item.option_name} ${item.unit}`.toLocaleLowerCase('tr-TR');
}

function renderMaterials() {
  const body = document.querySelector('#materials-body');
  const filter = materialState.filter.trim().toLocaleLowerCase('tr-TR');
  const items = filter
    ? materialState.items.filter((item) => materialLabel(item).includes(filter))
    : materialState.items;

  if (!items.length) {
    body.innerHTML = '<tr><td colspan="6">Malzeme bulunamadi.</td></tr>';
    return;
  }

  body.innerHTML = items.map((item) => `
    <tr data-id="${item.id}">
      <td>#${item.id}</td>
      <td><strong>${item.name}</strong></td>
      <td>${item.option_name}</td>
      <td>${item.unit}</td>
      <td>
        <input class="cost-input" type="number" min="0" step="0.01" value="${item.average_unit_cost}">
        <small>Mevcut: ${formatCost(item.average_unit_cost)} TL / ${item.unit}</small>
      </td>
      <td><button class="save-material" type="button">Kaydet</button></td>
    </tr>
  `).join('');

  for (const button of document.querySelectorAll('.save-material')) {
    button.addEventListener('click', () => saveMaterial(button.closest('tr')));
  }
}

async function saveMaterial(row) {
  const id = Number(row.dataset.id);
  const input = row.querySelector('.cost-input');
  const button = row.querySelector('.save-material');
  const value = Number(input.value || 0);

  button.disabled = true;
  button.textContent = 'Kaydediliyor...';
  clearMessage();

  const response = await fetch(`/api/admin/materials/${id}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ average_unit_cost: value }),
  });

  if (!response.ok) {
    button.disabled = false;
    button.textContent = 'Kaydet';
    showMessage('Fiyat kaydedilemedi.', 'error');
    return;
  }

  const data = await response.json();
  const index = materialState.items.findIndex((item) => item.id === id);
  if (index >= 0) materialState.items[index] = data.item;
  showMessage('Fiyat guncellendi.', 'success');
  renderMaterials();
}

function showMessage(text, type) {
  document.querySelector('#materials-message').innerHTML = `<p class="${type}">${text}</p>`;
}

function clearMessage() {
  document.querySelector('#materials-message').innerHTML = '';
}

document.querySelector('#material-search')?.addEventListener('input', (event) => {
  materialState.filter = event.currentTarget.value;
  renderMaterials();
});

loadMaterials().catch((error) => {
  console.error(error);
  document.querySelector('#materials-body').innerHTML = '<tr><td colspan="6">Malzemeler yuklenemedi.</td></tr>';
});
