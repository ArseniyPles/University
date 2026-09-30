const state = {
  expenses: [],
  analysis: null,
  comparison: null,
  budget: null,
  settings: {},
  editingId: null,
};

const $ = (id) => document.getElementById(id);

function debounce(fn, delay) {
  let timer = null;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

function localDateISO() {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}

function currentMonth() {
  return localDateISO().slice(0, 7);
}

function formatMoney(value) {
  return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 }).format(Number(value || 0)) + ' ₽';
}

function formatAmount(value, currency) {
  return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 }).format(Number(value || 0)) + ` ${currency}`;
}

function formatDate(value) {
  const [year, month, day] = String(value).split('-');
  return `${day}.${month}.${year}`;
}

function plural(n, one, few, many) {
  const value = Math.abs(n) % 100;
  const last = value % 10;
  if (value >= 11 && value <= 19) return many;
  if (last === 1) return one;
  if (last >= 2 && last <= 4) return few;
  return many;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
  }[char]));
}

function showToast(message) {
  const toast = $('toast');
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove('show'), 2400);
}

function openModal(id) {
  $('modalBackdrop').hidden = false;
  for (const name of ['expenseModal', 'settingsModal', 'currencyModal']) {
    $(name).hidden = name !== id;
  }
}

function closeModal() {
  $('modalBackdrop').hidden = true;
}

function queryParams() {
  const value = $('period').value || currentMonth();
  const [year, month] = value.split('-');
  const params = new URLSearchParams({ year, month: Number(month) });
  if ($('categoryFilter').value !== 'all') params.set('category', $('categoryFilter').value);
  if ($('searchText').value.trim()) params.set('q', $('searchText').value.trim());
  if ($('amountMin').value) params.set('amount_min', $('amountMin').value);
  if ($('amountMax').value) params.set('amount_max', $('amountMax').value);
  return params;
}

async function loadData() {
  document.body.classList.add('is-loading');
  try {
    const response = await fetch(`/api/data?${queryParams().toString()}`, { cache: 'no-store' });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Не удалось загрузить данные.');
    Object.assign(state, data);
    render();
  } catch (error) {
    showToast(error.message || 'Ошибка загрузки.');
  } finally {
    document.body.classList.remove('is-loading');
  }
}

function render() {
  const analysis = state.analysis || {};
  const budget = state.budget || {};

  $('totalValue').textContent = formatMoney(analysis.total);
  $('countValue').textContent = `${analysis.count || 0} ${plural(analysis.count || 0, 'операция', 'операции', 'операций')}`;
  $('budgetValue').textContent = budget.has_budget ? formatMoney(budget.budget) : 'Не задан';
  $('remainingValue').textContent = budget.has_budget ? formatMoney(budget.remaining) : '—';
  $('averageValue').textContent = formatMoney(analysis.average);

  renderComparison(state.comparison);
  renderBudget(budget);
  renderCategories(analysis.categories || []);
  renderDays(analysis.days || []);
  renderTable(state.expenses || []);
}

function renderComparison(comparison) {
  const value = $('comparisonValue');
  const note = $('comparisonNote');
  value.className = 'comparison-value';
  if (!comparison || comparison.previous_total === 0) {
    value.textContent = 'Нет базы';
    note.textContent = 'предыдущий месяц без расходов';
    return;
  }
  const percent = Number(comparison.percent || 0);
  value.textContent = `${percent > 0 ? '+' : ''}${percent.toFixed(1)}%`;
  note.textContent = 'к предыдущему месяцу';
  if (percent > 0) value.classList.add('trend-up');
  if (percent < 0) value.classList.add('trend-down');
  value.title = `Изменение: ${formatMoney(comparison.difference)}`;
}

function renderBudget(budget) {
  if (!budget.has_budget) {
    $('progressLabel').textContent = '—';
    $('progressAmount').textContent = 'Бюджет не задан';
  } else {
    $('progressLabel').textContent = `${Number(budget.percent_used || 0).toFixed(1)}%`;
    $('progressAmount').textContent = `${formatMoney(budget.spent)} из ${formatMoney(budget.budget)}`;
  }
  $('progressFill').style.width = budget.has_budget ? `${Math.min(100, Math.max(0, Number(budget.percent_used || 0)))}%` : '0%';
  $('avgDayValue').textContent = formatMoney(budget.avg_per_day);
  $('forecastValue').textContent = formatMoney(budget.forecast);

  const daysLeft = Math.max(0, Number(budget.month_days || 0) - Number(budget.elapsed_days || 0));
  $('daysLeftValue').textContent = `${daysLeft} ${plural(daysLeft, 'день', 'дня', 'дней')}`;

  const alert = $('forecastAlert');
  if (budget.status === 'exceeded') {
    alert.className = 'alert warn';
    alert.textContent = `Бюджет уже превышен на ${formatMoney(Math.abs(budget.remaining))}.`;
    $('budgetStatus').textContent = 'бюджет превышен';
  } else if (budget.status === 'risk') {
    alert.className = 'alert warn';
    alert.textContent = `Прогноз превышает бюджет на ${formatMoney(budget.forecast_over_budget)}.`;
    $('budgetStatus').textContent = 'есть риск превышения';
  } else if (budget.status === 'ok') {
    alert.className = 'alert good';
    alert.textContent = 'По текущему темпу расходов прогноз укладывается в установленный бюджет.';
    $('budgetStatus').textContent = 'в пределах бюджета';
  } else if (budget.is_future) {
    alert.className = 'alert';
    alert.textContent = 'Это будущий месяц: прогноз будет доступен после появления расходов.';
    $('budgetStatus').textContent = 'будущий период';
  } else if (budget.status === 'empty' && budget.has_budget) {
    alert.className = 'alert good';
    alert.textContent = 'Расходов за выбранный месяц пока нет. Бюджет свободен полностью.';
    $('budgetStatus').textContent = 'расходов пока нет';
  } else {
    alert.className = 'alert';
    alert.textContent = 'Установите месячный бюджет, чтобы включить контроль и прогноз.';
    $('budgetStatus').textContent = 'бюджет не задан';
  }
}

function renderCategories(categories) {
  const root = $('categoriesChart');
  root.innerHTML = '';
  if (!categories.length) {
    root.innerHTML = '<div class="empty-state compact-empty">Недостаточно данных для анализа.</div>';
    return;
  }
  const max = Math.max(...categories.map(item => Number(item.amount || 0)), 1);
  for (const item of categories) {
    const row = document.createElement('div');
    row.className = 'bar-row';
    row.innerHTML = `
      <div class="bar-label" title="${escapeHtml(item.category)}">${escapeHtml(item.category)}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${Math.max(4, Number(item.amount) / max * 100)}%"></div></div>
      <div class="bar-value">${formatMoney(item.amount)} <span class="bar-share">${Number(item.share || 0).toFixed(1)}%</span></div>`;
    root.appendChild(row);
  }
}

function renderDays(days) {
  const root = $('daysChart');
  root.innerHTML = '';
  if (!days.length) {
    root.innerHTML = '<div class="empty-state">Добавьте расходы для отображения динамики.</div>';
    return;
  }
  const max = Math.max(...days.map(item => Number(item.amount || 0)), 1);
  for (const item of days) {
    const amount = Number(item.amount || 0);
    const wrap = document.createElement('div');
    wrap.className = 'day-bar';
    const height = amount > 0 ? Math.max(4, amount / max * 180) : 2;
    wrap.innerHTML = `
      <div class="day-fill" style="height:${height}px" title="${formatDate(item.date)} — ${formatMoney(amount)}"></div>
      <div class="day-label">${item.date.slice(8)}</div>`;
    root.appendChild(wrap);
  }
}

function renderTable(expenses) {
  const body = $('expensesTable');
  body.innerHTML = '';
  $('tableMeta').textContent = `${expenses.length} ${plural(expenses.length, 'запись', 'записи', 'записей')}`;
  $('emptyState').hidden = expenses.length !== 0;

  for (const expense of expenses) {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${formatDate(expense.date)}</td>
      <td><span class="category-pill">${escapeHtml(expense.category)}</span></td>
      <td>${escapeHtml(expense.description || '—')}</td>
      <td class="amount">${formatAmount(expense.amount, expense.currency)}</td>
      <td>${formatMoney(expense.base_amount)}</td>
      <td>
        <div class="row-actions">
          <button class="small-btn" title="Изменить" data-action="edit" data-id="${expense.id}">✎</button>
          <button class="small-btn danger-btn" title="Удалить" data-action="delete" data-id="${expense.id}">×</button>
        </div>
      </td>`;
    body.appendChild(row);
  }
}

function resetExpenseForm() {
  state.editingId = null;
  $('expenseModalTitle').textContent = 'Добавить расход';
  $('expenseForm').reset();
  const today = localDateISO();
  $('expenseDate').value = today;
  $('expenseDate').max = today;
  $('expenseCurrency').value = 'RUB';
  $('expenseCategory').value = 'Еда';
  $('formError').textContent = '';
}

function editExpense(id) {
  const expense = state.expenses.find(item => Number(item.id) === Number(id));
  if (!expense) return;
  state.editingId = Number(id);
  $('expenseModalTitle').textContent = 'Изменить расход';
  $('expenseId').value = expense.id;
  $('expenseDate').value = expense.date;
  $('expenseDate').max = localDateISO();
  $('expenseAmount').value = expense.amount;
  $('expenseCurrency').value = expense.currency;
  $('expenseCategory').value = expense.category;
  $('expenseDescription').value = expense.description || '';
  $('formError').textContent = '';
  openModal('expenseModal');
}

async function deleteExpense(id) {
  if (!confirm('Удалить этот расход?')) return;
  try {
    const response = await fetch(`/api/expenses/${id}`, { method: 'DELETE' });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Не удалось удалить расход.');
    showToast('Расход удалён.');
    await loadData();
  } catch (error) {
    showToast(error.message || 'Ошибка удаления.');
  }
}

async function loadRates() {
  for (const code of ['USD', 'EUR', 'CNY']) {
    const key = code.toLowerCase();
    $(`${key}Rate`).textContent = '…';
    $(`${key}Date`).textContent = 'загрузка';
  }
  await Promise.all(['USD', 'EUR', 'CNY'].map(async (code) => {
    const key = code.toLowerCase();
    try {
      const response = await fetch(`/api/rate?from=${code}&to=RUB`, { cache: 'no-store' });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Ошибка');
      $(`${key}Rate`).textContent = Number(data.rate).toFixed(4);
      const source = data.source === 'api' ? 'API' : data.source === 'api-latest' ? 'API · последний доступный' : data.source === 'cache' ? 'кэш' : 'резерв';
      $(`${key}Date`).textContent = `на ${formatDate(data.date)} · ${source}`;
    } catch {
      $(`${key}Rate`).textContent = 'нет данных';
      $(`${key}Date`).textContent = 'сервис недоступен';
    }
  }));
}

$('addExpenseBtn').addEventListener('click', () => { resetExpenseForm(); openModal('expenseModal'); });
$('todayBtn').addEventListener('click', () => { $('period').value = currentMonth(); loadData(); });
$('settingsBtn').addEventListener('click', () => {
  $('monthlyBudget').value = state.budget?.has_budget ? state.budget.budget : '';
  $('settingsError').textContent = '';
  openModal('settingsModal');
});
$('currencyBtn').addEventListener('click', async () => { openModal('currencyModal'); await loadRates(); });
$('resetFilters').addEventListener('click', () => {
  $('categoryFilter').value = 'all';
  $('searchText').value = '';
  $('amountMin').value = '';
  $('amountMax').value = '';
  loadData();
});
$('period').addEventListener('change', loadData);
$('categoryFilter').addEventListener('change', loadData);
$('searchText').addEventListener('input', debounce(loadData, 250));
$('amountMin').addEventListener('change', loadData);
$('amountMax').addEventListener('change', loadData);

$('exportBtn').addEventListener('click', () => {
  const params = queryParams();
  window.location.href = `/api/export?${params.toString()}`;
});

$('modalBackdrop').addEventListener('click', (event) => {
  if (event.target.id === 'modalBackdrop' || event.target.closest('.close-modal')) closeModal();
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && !$('modalBackdrop').hidden) closeModal();
});

$('expenseForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  $('formError').textContent = '';
  const payload = {
    date: $('expenseDate').value,
    amount: $('expenseAmount').value,
    currency: $('expenseCurrency').value,
    category: $('expenseCategory').value,
    description: $('expenseDescription').value,
  };
  const amount = Number(payload.amount);
  if (!payload.date || !Number.isFinite(amount) || amount <= 0) {
    $('formError').textContent = 'Укажите корректную дату и сумму больше нуля.';
    return;
  }
  if (payload.date > localDateISO()) {
    $('formError').textContent = 'Дата расхода не может быть в будущем.';
    return;
  }
  const button = $('expenseSubmitBtn');
  button.disabled = true;
  button.textContent = 'Сохранение…';
  try {
    const id = state.editingId;
    const response = await fetch(id ? `/api/expenses/${id}` : '/api/expenses', {
      method: id ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Ошибка сохранения.');
    closeModal();
    showToast(id ? 'Расход обновлён.' : 'Расход добавлен.');
    await loadData();
  } catch (error) {
    $('formError').textContent = error.message || 'Не удалось связаться с сервером.';
  } finally {
    button.disabled = false;
    button.textContent = 'Сохранить';
  }
});

$('clearBudgetBtn').addEventListener('click', async () => {
  const [year, month] = ($('period').value || currentMonth()).split('-');
  try {
    const response = await fetch(`/api/settings/budget?year=${year}&month=${Number(month)}`, { method: 'DELETE' });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Не удалось сбросить бюджет.');
    closeModal();
    showToast(`Бюджет на ${month}.${year} сброшен.`);
    await loadData();
  } catch (error) {
    $('settingsError').textContent = error.message || 'Ошибка сброса бюджета.';
  }
});

$('settingsForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  $('settingsError').textContent = '';
  const [year, month] = ($('period').value || currentMonth()).split('-');
  try {
    const response = await fetch('/api/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ monthly_budget: $('monthlyBudget').value, year: Number(year), month: Number(month) }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Ошибка сохранения бюджета.');
    closeModal();
    showToast(`Бюджет на ${month}.${year} сохранён.`);
    await loadData();
  } catch (error) {
    $('settingsError').textContent = error.message || 'Ошибка сохранения.';
  }
});

$('expensesTable').addEventListener('click', (event) => {
  const button = event.target.closest('button[data-action]');
  if (!button) return;
  const id = button.dataset.id;
  if (button.dataset.action === 'edit') editExpense(id);
  if (button.dataset.action === 'delete') deleteExpense(id);
});

$('period').value = currentMonth();
resetExpenseForm();
loadData();
