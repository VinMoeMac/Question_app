const state = {
  page: 1,
  pageSize: 100,
  sortBy: null,
  sortDir: 'asc',
  search: '',
};

let columns = [];

const elements = {
  totalRows: document.getElementById('total-rows'),
  columnCount: document.getElementById('column-count'),
  defaultSort: document.getElementById('default-sort'),
  pagination: document.getElementById('pagination'),
  filteredCount: document.getElementById('filtered-count'),
  tableHead: document.querySelector('#data-table thead'),
  tableBody: document.querySelector('#data-table tbody'),
  prevButton: document.getElementById('prev-page'),
  nextButton: document.getElementById('next-page'),
  csvPath: document.getElementById('csv-path'),
  pageSize: document.getElementById('page-size'),
  sortBy: document.getElementById('sort-by'),
  sortDir: document.getElementById('sort-dir'),
  search: document.getElementById('search'),
  refresh: document.getElementById('refresh'),
  toolbar: document.getElementById('toolbar'),
};

function formatNumber(value) {
  return new Intl.NumberFormat().format(value);
}

function renderColumns(colDefs) {
  columns = colDefs;
  elements.sortBy.innerHTML = '';
  columns.forEach((column) => {
    const option = document.createElement('option');
    option.value = column.name;
    option.textContent = `${column.name} (${column.type})`;
    elements.sortBy.appendChild(option);
  });
}

function renderTable(rows) {
  if (!columns.length) {
    elements.tableHead.innerHTML = '';
    elements.tableBody.innerHTML = '<tr><td class="placeholder">No metadata available.</td></tr>';
    return;
  }

  const headRow = document.createElement('tr');
  columns.forEach((column) => {
    const th = document.createElement('th');
    th.textContent = column.name;
    headRow.appendChild(th);
  });
  elements.tableHead.innerHTML = '';
  elements.tableHead.appendChild(headRow);

  if (!rows.length) {
    elements.tableBody.innerHTML = '<tr><td class="placeholder" colspan="' + columns.length + '">No rows match the current filters.</td></tr>';
    return;
  }

  const fragment = document.createDocumentFragment();
  rows.forEach((row) => {
    const tr = document.createElement('tr');
    columns.forEach((column) => {
      const td = document.createElement('td');
      const value = row[column.name];
      td.textContent = value === null || value === undefined ? '' : value;
      tr.appendChild(td);
    });
    fragment.appendChild(tr);
  });
  elements.tableBody.innerHTML = '';
  elements.tableBody.appendChild(fragment);
}

function updateStats(metadata) {
  elements.totalRows.textContent = metadata.row_count ? formatNumber(metadata.row_count) : '0';
  elements.columnCount.textContent = metadata.columns ? metadata.columns.length : 0;
  elements.defaultSort.textContent = metadata.default_sort || '—';
}

function updatePagination(payload) {
  const { page, page_size: pageSize, total_rows: totalRows, total_filtered: totalFiltered } = payload;
  const firstRow = totalFiltered === 0 ? 0 : (page - 1) * pageSize + 1;
  const lastRow = Math.min(page * pageSize, totalFiltered);

  elements.pagination.textContent = totalFiltered
    ? `Showing ${formatNumber(firstRow)}–${formatNumber(lastRow)} of ${formatNumber(totalFiltered)}`
    : 'No results';

  if (totalFiltered !== totalRows) {
    elements.filteredCount.textContent = `Filtered from ${formatNumber(totalRows)} total rows`;
  } else {
    elements.filteredCount.textContent = '';
  }

  elements.prevButton.disabled = page <= 1;
  elements.nextButton.disabled = lastRow >= totalFiltered;
}

async function fetchJSON(url) {
  const response = await fetch(url);
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(detail.detail || response.statusText || 'Request failed');
  }
  return response.json();
}

async function loadMetadata() {
  try {
    const metadata = await fetchJSON('/api/metadata');
    updateStats(metadata);
    if (metadata.csv_display_name) {
      elements.csvPath.textContent = metadata.csv_display_name;
    }
    renderColumns(metadata.columns || []);
    if (metadata.default_sort) {
      elements.sortBy.value = metadata.default_sort;
      state.sortBy = metadata.default_sort;
    }
    return metadata;
  } catch (error) {
    console.error(error);
    elements.tableBody.innerHTML = `<tr><td class="placeholder">Failed to load metadata: ${error.message}</td></tr>`;
    throw error;
  }
}

async function loadRows() {
  const params = new URLSearchParams();
  params.set('page', String(state.page));
  params.set('page_size', String(state.pageSize));
  params.set('sort_dir', state.sortDir);
  if (state.sortBy) {
    params.set('sort_by', state.sortBy);
  }
  if (state.search) {
    params.set('search', state.search);
  }

  try {
    const payload = await fetchJSON(`/api/rows?${params.toString()}`);
    renderTable(payload.rows || []);
    updatePagination(payload);
  } catch (error) {
    console.error(error);
    elements.tableBody.innerHTML = `<tr><td class="placeholder">${error.message}</td></tr>`;
    elements.pagination.textContent = '';
    elements.filteredCount.textContent = '';
  }
}

function handleToolbarSubmit(event) {
  event.preventDefault();
  state.search = elements.search.value.trim();
  state.pageSize = Number(elements.pageSize.value);
  state.sortBy = elements.sortBy.value || null;
  state.sortDir = elements.sortDir.value;
  state.page = 1;
  loadRows();
}

function goToPreviousPage() {
  if (state.page <= 1) return;
  state.page -= 1;
  loadRows();
}

function goToNextPage() {
  state.page += 1;
  loadRows();
}

async function handleRefresh() {
  elements.refresh.disabled = true;
  elements.refresh.textContent = 'Refreshing…';
  try {
    await fetchJSON('/api/refresh');
    const metadata = await loadMetadata();
    if (metadata.default_sort) {
      elements.sortBy.value = metadata.default_sort;
      state.sortBy = metadata.default_sort;
    }
    state.page = 1;
    await loadRows();
  } catch (error) {
    console.error(error);
  } finally {
    elements.refresh.disabled = false;
    elements.refresh.textContent = 'Refresh CSV';
  }
}

function initPageSize(metadata) {
  const options = Array.from(elements.pageSize.options);
  const maxPageSize = metadata.max_page_size || 500;

  options.forEach((option) => {
    const value = Number(option.value);
    if (value > maxPageSize) {
      option.disabled = true;
    }
  });

  const defaultSize = metadata.default_page_size || state.pageSize;
  const currentValues = options.map((option) => Number(option.value));
  if (!currentValues.includes(defaultSize)) {
    const option = document.createElement('option');
    option.value = defaultSize;
    option.textContent = `${defaultSize}`;
    option.selected = true;
    elements.pageSize.appendChild(option);
  }

  elements.pageSize.value = String(defaultSize);
  state.pageSize = defaultSize;
}

async function bootstrap() {
  elements.toolbar.addEventListener('submit', handleToolbarSubmit);
  elements.prevButton.addEventListener('click', goToPreviousPage);
  elements.nextButton.addEventListener('click', goToNextPage);
  elements.refresh.addEventListener('click', handleRefresh);

  try {
    const metadata = await loadMetadata();
    initPageSize(metadata);
    await loadRows();
  } catch (error) {
    console.error('Bootstrap failed', error);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', bootstrap);
} else {
  bootstrap();
}
