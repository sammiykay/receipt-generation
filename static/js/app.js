const state = {
  latestReceipt: null,
  modalAction: null,
  settingsSnapshot: null,
  historyRows: [],
  currencySymbol: '₦',
};

const el = {
  navLinks: Array.from(document.querySelectorAll('.nav-link')),
  views: {
    history: document.getElementById('view-history'),
    create: document.getElementById('view-create'),
    success: document.getElementById('view-success'),
    settings: document.getElementById('view-settings'),
  },
  mobileMenuBtn: document.getElementById('mobile-menu-btn'),
  mobileMenu: document.getElementById('mobile-menu'),

  receiptForm: document.getElementById('receipt-form'),
  expensesList: document.getElementById('expenses-list'),
  expenseTemplate: document.getElementById('expense-row-template'),
  addExpenseBtn: document.getElementById('add-expense-btn'),
  clearFormBtn: document.getElementById('clear-form-btn'),
  subtotalAmount: document.getElementById('subtotal-amount'),
  taxAmount: document.getElementById('tax-amount'),
  totalAmount: document.getElementById('total-amount'),
  currencyLabel: document.getElementById('currency-label'),

  successReceiptNo: document.getElementById('success-receipt-no'),
  successStudentName: document.getElementById('success-student-name'),
  successTotal: document.getElementById('success-total'),
  successDate: document.getElementById('success-date'),
  openPdfBtn: document.getElementById('open-pdf-btn'),
  printPdfBtn: document.getElementById('print-pdf-btn'),
  newReceiptBtn: document.getElementById('new-receipt-btn'),

  gotoCreateBtn: document.getElementById('goto-create-btn'),
  exportCsvBtn: document.getElementById('export-csv-btn'),
  historyWrap: document.getElementById('history-table-wrap'),
  historyDetail: document.getElementById('history-detail'),
  historySummary: document.getElementById('history-summary'),
  searchInput: document.getElementById('search-input'),
  dateFrom: document.getElementById('date-from'),
  dateTo: document.getElementById('date-to'),
  applyFiltersBtn: document.getElementById('apply-filters-btn'),

  settingsForm: document.getElementById('settings-form'),
  cancelSettingsBtn: document.getElementById('cancel-settings-btn'),
  statusMessage: document.getElementById('status-message'),

  footerTotal: document.getElementById('footer-total'),
  footerCount: document.getElementById('footer-count'),

  modal: document.getElementById('modal'),
  modalTitle: document.getElementById('modal-title'),
  modalMessage: document.getElementById('modal-message'),
  modalCancel: document.getElementById('modal-cancel'),
  modalConfirm: document.getElementById('modal-confirm'),

  toastContainer: document.getElementById('toast-container'),
};

function showToast(message, type = 'ok') {
  const node = document.createElement('div');
  node.className = `toast ${type === 'error' ? 'error' : ''}`;
  node.textContent = message;
  el.toastContainer.appendChild(node);
  setTimeout(() => node.remove(), 2800);
}

function formatMoney(value) {
  const num = Number(value || 0);
  return `${state.currencySymbol}${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function applyCurrencySymbol(symbol) {
  state.currencySymbol = (symbol || '').trim() || '₦';
  if (el.currencyLabel) el.currencyLabel.textContent = state.currencySymbol;
}

function api(path, options = {}) {
  return fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  }).then(async (res) => {
    if (!res.ok) {
      let detail = 'Request failed';
      try {
        const body = await res.json();
        detail = body.detail || detail;
      } catch (_) {
        detail = await res.text();
      }
      throw new Error(detail);
    }
    const contentType = res.headers.get('content-type') || '';
    return contentType.includes('application/json') ? res.json() : res.text();
  });
}

function hideAllViews() {
  Object.values(el.views).forEach((node) => node.classList.add('hidden'));
}

function setActiveNav(view) {
  el.navLinks.forEach((btn) => {
    const active = btn.dataset.view === view;
    if (active) {
      btn.classList.add('text-primary', 'font-bold');
      btn.classList.remove('text-slate-600', 'font-medium');
    } else {
      btn.classList.remove('text-primary', 'font-bold');
      btn.classList.add('text-slate-600', 'font-medium');
    }
  });
}

function setActiveView(view) {
  hideAllViews();
  if (!el.views[view]) return;
  el.views[view].classList.remove('hidden');
  setActiveNav(view);

  if (view === 'history') loadReceiptHistory();
  if (view === 'settings') loadSettings();
}

function setFieldError(input, message) {
  const group = input.closest('.floating-label-group, .space-y-1, .flex.flex-col.gap-2');
  const errorEl = group ? group.querySelector('.error-text') : null;
  input.classList.toggle('input-invalid', !!message);
  if (errorEl) {
    if (message) {
      errorEl.textContent = message;
      errorEl.classList.remove('hidden');
    } else {
      errorEl.textContent = '';
      errorEl.classList.add('hidden');
    }
  }
}

function validateRequired(input, label) {
  if (!input.value.trim()) {
    setFieldError(input, `${label} is required`);
    return false;
  }
  setFieldError(input, '');
  return true;
}

function validateAmount(input) {
  const raw = input.value.trim();
  const num = Number(raw);
  if (!raw) {
    setFieldError(input, 'Amount is required');
    return false;
  }
  if (Number.isNaN(num) || num < 0) {
    setFieldError(input, 'Amount must be 0 or greater');
    return false;
  }
  setFieldError(input, '');
  return true;
}

function recalcTotal() {
  const amounts = Array.from(el.expensesList.querySelectorAll('.expense-amount')).map((i) => Number(i.value || 0));
  const total = amounts.reduce((sum, n) => sum + (Number.isNaN(n) ? 0 : n), 0);
  el.subtotalAmount.textContent = formatMoney(total);
  if (el.taxAmount) el.taxAmount.textContent = formatMoney(0);
  el.totalAmount.textContent = formatMoney(total);
}

function collectExpenseRows() {
  return Array.from(el.expensesList.querySelectorAll('.expense-row')).map((row) => ({
    row,
    itemInput: row.querySelector('.expense-item'),
    amountInput: row.querySelector('.expense-amount'),
  }));
}

function openModal({ title, message, confirmLabel = 'Delete', onConfirm }) {
  state.modalAction = onConfirm;
  el.modalTitle.textContent = title;
  el.modalMessage.textContent = message;
  el.modalConfirm.textContent = confirmLabel;
  el.modal.classList.remove('hidden');
  el.modal.classList.add('flex');
}

function closeModal() {
  state.modalAction = null;
  el.modal.classList.remove('flex');
  el.modal.classList.add('hidden');
}

function addExpenseRow(initial = { item_name: '', amount: '' }) {
  const fragment = el.expenseTemplate.content.cloneNode(true);
  const row = fragment.querySelector('.expense-row');
  const itemInput = row.querySelector('.expense-item');
  const amountInput = row.querySelector('.expense-amount');
  const removeBtn = row.querySelector('.remove-expense');

  itemInput.value = initial.item_name || '';
  amountInput.value = initial.amount || '';

  itemInput.addEventListener('input', () => validateRequired(itemInput, 'Item name'));
  amountInput.addEventListener('input', () => {
    validateAmount(amountInput);
    recalcTotal();
  });

  removeBtn.addEventListener('click', () => {
    if (el.expensesList.children.length <= 1) {
      showToast('At least one expense row is required', 'error');
      return;
    }
    openModal({
      title: 'Delete Expense',
      message: 'Are you sure you want to remove this expense row?',
      confirmLabel: 'Delete',
      onConfirm: () => {
        row.remove();
        recalcTotal();
      },
    });
  });

  el.expensesList.appendChild(row);
  recalcTotal();
}

function resetReceiptForm() {
  el.receiptForm.reset();
  el.expensesList.innerHTML = '';
  addExpenseRow();
  recalcTotal();
}

function validateReceiptForm() {
  let ok = true;
  if (!validateRequired(document.getElementById('student-name'), 'Student name')) ok = false;
  if (!validateRequired(document.getElementById('student-class'), 'Class')) ok = false;

  collectExpenseRows().forEach(({ itemInput, amountInput }) => {
    if (!validateRequired(itemInput, 'Item name')) ok = false;
    if (!validateAmount(amountInput)) ok = false;
  });

  return ok;
}

function receiptPayload() {
  return {
    student_name: document.getElementById('student-name').value.trim(),
    student_class: document.getElementById('student-class').value.trim(),
    department: document.getElementById('department').value.trim(),
    items: collectExpenseRows().map(({ itemInput, amountInput }) => ({
      item_name: itemInput.value.trim(),
      amount: Number(amountInput.value || 0).toFixed(2),
    })),
  };
}

function showSuccess(data) {
  state.latestReceipt = data;
  const r = data.receipt;
  el.successReceiptNo.textContent = r.receipt_number;
  el.successStudentName.textContent = r.student_name;
  el.successTotal.textContent = formatMoney(r.total);
  el.successDate.textContent = new Date(r.created_at).toLocaleString();
  setActiveView('success');
}

async function submitReceipt(event) {
  event.preventDefault();
  if (!validateReceiptForm()) {
    showToast('Please fix form validation errors', 'error');
    return;
  }

  try {
    const result = await api('/api/receipts', {
      method: 'POST',
      body: JSON.stringify(receiptPayload()),
    });
    showSuccess(result);
    loadReceiptHistory();
    showToast('Receipt generated successfully');
  } catch (error) {
    showToast(error.message, 'error');
  }
}

async function loadReceiptHistory() {
  const params = new URLSearchParams();
  if (el.searchInput.value.trim()) params.set('search', el.searchInput.value.trim());
  if (el.dateFrom.value) params.set('date_from', el.dateFrom.value);
  if (el.dateTo.value) params.set('date_to', el.dateTo.value);

  try {
    const rows = await api(`/api/receipts?${params.toString()}`);
    state.historyRows = rows;
    renderHistoryTable(rows);
    updateHistoryFooter(rows);
    el.historyDetail.classList.add('hidden');
    el.historyDetail.innerHTML = '';
  } catch (error) {
    showToast(error.message, 'error');
  }
}

function renderHistoryTable(rows) {
  if (!rows.length) {
    el.historyWrap.innerHTML = '<div class="p-8 text-slate-500 text-sm">No receipts found.</div>';
    return;
  }

  const table = `
    <table class="w-full text-left border-collapse">
      <thead>
        <tr class="bg-slate-50 border-b border-slate-200">
          <th class="px-6 py-4 text-xs font-bold uppercase tracking-wider text-slate-500">Receipt No</th>
          <th class="px-6 py-4 text-xs font-bold uppercase tracking-wider text-slate-500">Student Name</th>
          <th class="px-6 py-4 text-xs font-bold uppercase tracking-wider text-slate-500">Class</th>
          <th class="px-6 py-4 text-xs font-bold uppercase tracking-wider text-slate-500">Total Amount</th>
          <th class="px-6 py-4 text-xs font-bold uppercase tracking-wider text-slate-500">Date Issued</th>
          <th class="px-6 py-4 text-xs font-bold uppercase tracking-wider text-slate-500 text-right">Actions</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-slate-100">
        ${rows
          .map((row) => {
            const initials = row.student_name
              .split(' ')
              .filter(Boolean)
              .slice(0, 2)
              .map((v) => v[0].toUpperCase())
              .join('') || 'ST';
            return `
              <tr class="hover:bg-slate-50 transition-colors">
                <td class="px-6 py-4"><button class="font-mono text-sm font-bold text-primary" data-action="details" data-id="${row.id}">#${row.receipt_number}</button></td>
                <td class="px-6 py-4">
                  <div class="flex items-center gap-3">
                    <div class="size-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-xs">${initials}</div>
                    <span class="text-sm font-medium text-slate-900">${row.student_name}</span>
                  </div>
                </td>
                <td class="px-6 py-4 text-sm text-slate-600">${row.student_class}</td>
                <td class="px-6 py-4 text-sm font-bold text-slate-900">${formatMoney(row.total)}</td>
                <td class="px-6 py-4 text-sm text-slate-500">${new Date(row.created_at).toLocaleDateString()}</td>
                <td class="px-6 py-4 text-right">
                  <div class="flex justify-end gap-2 flex-wrap">
                    <button data-action="view" data-id="${row.id}" class="inline-flex items-center justify-center rounded-lg h-8 px-3 text-xs font-bold text-primary bg-primary/10 hover:bg-primary hover:text-white transition-all">View</button>
                    <button data-action="regen" data-id="${row.id}" class="inline-flex items-center justify-center rounded-lg h-8 px-3 text-xs font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 transition-all">Re-gen</button>
                    <button data-action="export" data-id="${row.id}" class="inline-flex items-center justify-center rounded-lg h-8 px-3 text-xs font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 transition-all">JSON</button>
                    <button data-action="delete" data-id="${row.id}" class="inline-flex items-center justify-center rounded-lg h-8 px-3 text-xs font-bold text-red-700 bg-red-50 hover:bg-red-100 transition-all">Delete</button>
                  </div>
                </td>
              </tr>
            `;
          })
          .join('')}
      </tbody>
    </table>
  `;

  el.historyWrap.innerHTML = table;
}

function updateHistoryFooter(rows) {
  const count = rows.length;
  const total = rows.reduce((sum, r) => sum + Number(r.total || 0), 0);
  el.historySummary.textContent = `Showing ${count} receipt${count === 1 ? '' : 's'}`;
  el.footerCount.textContent = String(count);
  el.footerTotal.textContent = formatMoney(total);
}

async function loadReceiptDetails(id) {
  try {
    const r = await api(`/api/receipts/${id}`);
    const items = r.items.map((i) => `<tr><td class="py-2 pr-4">${i.item_name}</td><td class="py-2">${formatMoney(i.amount)}</td></tr>`).join('');
    el.historyDetail.innerHTML = `
      <h3 class="text-lg font-bold text-slate-900 mb-2">Receipt Details - ${r.receipt_number}</h3>
      <p class="text-sm text-slate-600 mb-4">${new Date(r.created_at).toLocaleString()} | ${r.student_name} (${r.student_class})</p>
      <div class="overflow-x-auto">
        <table class="w-full text-sm"><thead><tr><th class="text-left py-2">Item</th><th class="text-left py-2">Amount</th></tr></thead><tbody>${items}</tbody></table>
      </div>
      <p class="mt-4 font-bold">Total: ${formatMoney(r.total)}</p>
      <div class="mt-4 flex gap-2 flex-wrap">
        <button data-action="view" data-id="${r.id}" class="px-3 py-2 rounded-lg bg-primary text-white text-sm font-semibold">View PDF</button>
        <button data-action="regen" data-id="${r.id}" class="px-3 py-2 rounded-lg bg-slate-100 text-slate-700 text-sm font-semibold">Re-generate PDF</button>
        <button data-action="export" data-id="${r.id}" class="px-3 py-2 rounded-lg bg-slate-100 text-slate-700 text-sm font-semibold">Export JSON</button>
      </div>
    `;
    el.historyDetail.classList.remove('hidden');
  } catch (error) {
    showToast(error.message, 'error');
  }
}

async function handleHistoryAction(event) {
  const btn = event.target.closest('button[data-action]');
  if (!btn) return;

  const action = btn.dataset.action;
  const id = Number(btn.dataset.id);

  if (action === 'details') return loadReceiptDetails(id);
  if (action === 'view') return window.open(`/api/receipts/${id}/pdf`, '_blank');

  if (action === 'regen') {
    try {
      await api(`/api/receipts/${id}/regenerate`, { method: 'POST' });
      showToast('PDF regenerated successfully');
      loadReceiptHistory();
    } catch (error) {
      showToast(error.message, 'error');
    }
    return;
  }

  if (action === 'export') {
    try {
      const data = await api(`/api/receipts/${id}/export`);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${data.receipt_number}.json`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      showToast(error.message, 'error');
    }
    return;
  }

  if (action === 'delete') {
    openModal({
      title: 'Delete Receipt',
      message: 'This will remove the receipt record and its PDF file.',
      confirmLabel: 'Delete',
      onConfirm: async () => {
        try {
          await api(`/api/receipts/${id}`, { method: 'DELETE' });
          showToast('Receipt deleted');
          loadReceiptHistory();
        } catch (error) {
          showToast(error.message, 'error');
        }
      },
    });
  }
}

function exportCsv() {
  if (!state.historyRows.length) {
    showToast('No receipts to export', 'error');
    return;
  }
  const rows = [
    ['Receipt Number', 'Student Name', 'Class', 'Total', 'Created At'],
    ...state.historyRows.map((row) => [
      row.receipt_number,
      row.student_name,
      row.student_class,
      row.total,
      new Date(row.created_at).toISOString(),
    ]),
  ];

  const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'receipt-history.csv';
  link.click();
  URL.revokeObjectURL(url);
}

async function loadSettings() {
  try {
    const s = await api('/api/settings');
    document.getElementById('school-name').value = s.school_name || '';
    document.getElementById('school-contact').value = s.school_contact || '';
    document.getElementById('currency-symbol').value = s.currency_symbol || '₦';
    document.getElementById('school-address').value = s.school_address || '';
    document.getElementById('footer-text').value = s.footer_text || '';
    document.getElementById('default-pdf-folder').value = s.default_pdf_folder || '';
    applyCurrencySymbol(s.currency_symbol || '₦');
    recalcTotal();
    if (state.historyRows.length) {
      renderHistoryTable(state.historyRows);
      updateHistoryFooter(state.historyRows);
    }
    state.settingsSnapshot = JSON.stringify(s);
    el.statusMessage.classList.add('opacity-0');
  } catch (error) {
    showToast(error.message, 'error');
  }
}

function validateSettings() {
  const schoolName = document.getElementById('school-name');
  const currencySymbol = document.getElementById('currency-symbol');
  const nameOk = validateRequired(schoolName, 'School name');
  let currencyOk = validateRequired(currencySymbol, 'Currency symbol');
  if (currencyOk && currencySymbol.value.trim().length > 3) {
    setFieldError(currencySymbol, 'Currency symbol must be at most 3 characters');
    currencyOk = false;
  }
  return nameOk && currencyOk;
}

async function saveSettings(event) {
  event.preventDefault();
  if (!validateSettings()) {
    showToast('Please fix form validation errors', 'error');
    return;
  }

  const payload = {
    school_name: document.getElementById('school-name').value.trim(),
    school_contact: document.getElementById('school-contact').value.trim(),
    currency_symbol: (document.getElementById('currency-symbol').value.trim() || '₦').slice(0, 3),
    school_address: document.getElementById('school-address').value.trim(),
    footer_text: document.getElementById('footer-text').value.trim(),
    default_pdf_folder: document.getElementById('default-pdf-folder').value.trim(),
  };

  try {
    await api('/api/settings', { method: 'PUT', body: JSON.stringify(payload) });
    applyCurrencySymbol(payload.currency_symbol);
    recalcTotal();
    if (state.historyRows.length) {
      renderHistoryTable(state.historyRows);
      updateHistoryFooter(state.historyRows);
    }
    state.settingsSnapshot = JSON.stringify(payload);
    el.statusMessage.classList.remove('opacity-0');
    showToast('Settings saved successfully');
  } catch (error) {
    showToast(error.message, 'error');
  }
}

function bindEvents() {
  el.navLinks.forEach((btn) => {
    btn.addEventListener('click', () => {
      setActiveView(btn.dataset.view);
      el.mobileMenu.classList.add('hidden');
    });
  });

  el.mobileMenuBtn.addEventListener('click', () => el.mobileMenu.classList.toggle('hidden'));

  el.gotoCreateBtn.addEventListener('click', () => setActiveView('create'));
  el.exportCsvBtn.addEventListener('click', exportCsv);
  el.applyFiltersBtn.addEventListener('click', loadReceiptHistory);

  el.addExpenseBtn.addEventListener('click', () => addExpenseRow());
  el.clearFormBtn.addEventListener('click', resetReceiptForm);
  el.receiptForm.addEventListener('submit', submitReceipt);

  el.openPdfBtn.addEventListener('click', () => {
    if (!state.latestReceipt) return;
    window.open(state.latestReceipt.pdf_url, '_blank');
  });

  el.printPdfBtn.addEventListener('click', () => {
    if (!state.latestReceipt) return;
    const w = window.open(state.latestReceipt.pdf_url, '_blank');
    if (w) w.addEventListener('load', () => w.print());
  });

  el.newReceiptBtn.addEventListener('click', () => {
    resetReceiptForm();
    setActiveView('create');
  });

  el.historyWrap.addEventListener('click', handleHistoryAction);
  el.historyDetail.addEventListener('click', handleHistoryAction);

  el.settingsForm.addEventListener('submit', saveSettings);
  document.getElementById('currency-symbol').addEventListener('input', (event) => {
    const input = event.target;
    if (input.value.length > 3) {
      input.value = input.value.slice(0, 3);
    }
  });
  el.cancelSettingsBtn.addEventListener('click', () => {
    if (!state.settingsSnapshot) return loadSettings();
    const s = JSON.parse(state.settingsSnapshot);
    document.getElementById('school-name').value = s.school_name || '';
    document.getElementById('school-contact').value = s.school_contact || '';
    document.getElementById('currency-symbol').value = s.currency_symbol || '₦';
    document.getElementById('school-address').value = s.school_address || '';
    document.getElementById('footer-text').value = s.footer_text || '';
    document.getElementById('default-pdf-folder').value = s.default_pdf_folder || '';
    applyCurrencySymbol(s.currency_symbol || '₦');
    recalcTotal();
    if (state.historyRows.length) {
      renderHistoryTable(state.historyRows);
      updateHistoryFooter(state.historyRows);
    }
  });

  el.modalCancel.addEventListener('click', closeModal);
  el.modalConfirm.addEventListener('click', async () => {
    if (state.modalAction) await state.modalAction();
    closeModal();
  });
}

function init() {
  bindEvents();
  resetReceiptForm();
  loadSettings();
  setActiveView('history');
}

init();
