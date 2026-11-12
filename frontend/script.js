const form = document.getElementById('upload-form');
const fileInput = document.getElementById('receipt');
const dropzone = document.getElementById('dropzone');
const fileName = document.getElementById('file-name');
const submitButton = document.getElementById('submit-button');
const message = document.getElementById('message');
const resultPanel = document.getElementById('result');
const recommendationsPanel = document.getElementById('recommendations');
const emptyState = document.getElementById('empty-state');

const acceptedTypes = new Set(['image/jpeg', 'image/png', 'image/webp']);
const formatPrice = (price) => Number(price).toLocaleString(undefined, {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function showMessage(text, kind = 'error') {
  message.textContent = text;
  message.classList.toggle('success', kind === 'success');
  message.classList.remove('hidden');
}

function clearMessage() {
  message.textContent = '';
  message.classList.add('hidden');
  message.classList.remove('success');
}

function setFile(file) {
  if (!file) return;
  const isAccepted = acceptedTypes.has(file.type) || /\.(jpe?g|png|webp)$/i.test(file.name);
  if (!isAccepted) {
    fileInput.value = '';
    fileName.textContent = 'Choose a receipt image';
    showMessage('Please choose a JPG, PNG, or WebP image.');
    return;
  }
  if (file.size > 8 * 1024 * 1024) {
    fileInput.value = '';
    fileName.textContent = 'Choose a receipt image';
    showMessage('This image is larger than 8 MB. Choose a smaller one.');
    return;
  }
  fileName.textContent = file.name;
  clearMessage();
}

fileInput.addEventListener('change', () => setFile(fileInput.files[0]));

['dragenter', 'dragover'].forEach((eventName) => {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.add('is-dragging');
  });
});
['dragleave', 'drop'].forEach((eventName) => {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.remove('is-dragging');
  });
});
dropzone.addEventListener('drop', (event) => {
  const file = event.dataTransfer.files[0];
  if (!file) return;
  const transfer = new DataTransfer();
  transfer.items.add(file);
  fileInput.files = transfer.files;
  setFile(file);
});

function renderItems(items) {
  const list = document.getElementById('items-list');
  list.replaceChildren();
  let total = 0;

  items.forEach((item) => {
    const row = document.createElement('div');
    row.className = 'item-row';
    const name = document.createElement('span');
    name.className = 'item-name';
    const bullet = document.createElement('span');
    bullet.className = 'item-bullet';
    bullet.setAttribute('aria-hidden', 'true');
    const label = document.createElement('span');
    label.textContent = item.name;
    name.append(bullet, label);
    const price = document.createElement('span');
    price.className = 'item-price';
    price.textContent = formatPrice(item.price);
    row.append(name, price);
    list.append(row);
    total += Number(item.price) || 0;
  });

  document.getElementById('item-count').textContent = `${items.length} ${items.length === 1 ? 'ITEM' : 'ITEMS'}`;
  document.getElementById('receipt-total').textContent = formatPrice(total);
  resultPanel.classList.remove('hidden');
  emptyState.classList.add('hidden');
}

function renderRecommendations(recommendations) {
  const list = document.getElementById('recommendation-list');
  list.replaceChildren();
  recommendations.forEach((recommendation) => {
    const chip = document.createElement('span');
    chip.className = 'recommendation-chip';
    chip.textContent = recommendation;
    list.append(chip);
  });
  recommendationsPanel.classList.toggle('hidden', recommendations.length === 0);
}

function renderHistory(items) {
  const body = document.getElementById('history-list');
  body.replaceChildren();
  if (!items.length) {
    const row = document.createElement('tr');
    row.className = 'history-empty';
    const cell = document.createElement('td');
    cell.colSpan = 3;
    cell.textContent = 'Your shopping history will show up here after your first scan.';
    row.append(cell);
    body.append(row);
    return;
  }

  items.forEach((item) => {
    const row = document.createElement('tr');
    const name = document.createElement('td');
    name.textContent = item.item;
    const date = document.createElement('td');
    const parsedDate = new Date(item.timestamp ? String(item.timestamp).replace(' ', 'T') : '');
    date.textContent = Number.isNaN(parsedDate.getTime())
      ? item.timestamp
      : new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(parsedDate);
    const price = document.createElement('td');
    price.className = 'price-cell';
    price.textContent = formatPrice(item.price);
    row.append(name, date, price);
    body.append(row);
  });
}

async function loadHistory() {
  try {
    const response = await fetch('/api/history');
    if (!response.ok) return;
    const data = await response.json();
    renderHistory(Array.isArray(data.items) ? data.items : []);
  } catch (error) {
    console.warn('Could not load grocery history.', error);
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const file = fileInput.files[0];
  if (!file) {
    showMessage('Choose a receipt image to get started.');
    return;
  }

  clearMessage();
  submitButton.disabled = true;
  submitButton.querySelector('span:first-child').textContent = 'Reading your receipt…';
  submitButton.setAttribute('aria-busy', 'true');

  try {
    const formData = new FormData();
    formData.append('receipt', file);
    const response = await fetch('/upload', { method: 'POST', body: formData });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'We couldn’t scan that receipt. Please try again.');

    const items = Array.isArray(data.items) ? data.items : [];
    renderItems(items);
    renderRecommendations(Array.isArray(data.recommendations) ? data.recommendations : []);
    if (items.length) {
      showMessage('Your list is ready, and your shopping history has been updated.', 'success');
      await loadHistory();
    } else {
      showMessage('No grocery items were found. Try a closer, brighter photo.');
    }
  } catch (error) {
    showMessage(error.message || 'Something went wrong while scanning the receipt.');
  } finally {
    submitButton.disabled = false;
    submitButton.querySelector('span:first-child').textContent = 'Build my grocery list';
    submitButton.removeAttribute('aria-busy');
  }
});

loadHistory();
