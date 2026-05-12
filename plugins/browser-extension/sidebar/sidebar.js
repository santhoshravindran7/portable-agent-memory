/**
 * PAM Sidebar Script
 * Full memory view with tabs, search, selection, and bulk operations.
 */

document.addEventListener('DOMContentLoaded', init);

let currentTab = 'all';
let selectedIds = new Set();
let allEntries = [];

async function init() {
  await refreshEntries();
  setupEventListeners();
}

function setupEventListeners() {
  // Tabs
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      currentTab = tab.dataset.tab;
      renderEntries();
    });
  });

  // Search
  document.getElementById('search-input').addEventListener('input', debounce(renderEntries, 200));

  // Inject all
  document.getElementById('inject-all-btn').addEventListener('click', handleInjectAll);

  // Inject selected
  document.getElementById('inject-selected-btn').addEventListener('click', handleInjectSelected);

  // Clear all
  document.getElementById('clear-all-btn').addEventListener('click', async () => {
    if (confirm('Delete all memories? This cannot be undone.')) {
      await chrome.runtime.sendMessage({ action: 'clearAll' });
      await refreshEntries();
    }
  });

  // Export / Import
  document.getElementById('export-btn').addEventListener('click', handleExport);
  document.getElementById('import-btn').addEventListener('click', () => document.getElementById('import-file').click());
  document.getElementById('import-file').addEventListener('change', handleImport);
}

async function refreshEntries() {
  const artifact = await chrome.runtime.sendMessage({ action: 'getArtifact' });
  allEntries = [
    ...artifact.episodic.map(e => ({ ...e, category: 'episodic' })),
    ...artifact.semantic.map(e => ({ ...e, category: 'semantic' })),
    ...artifact.procedural.map(e => ({ ...e, category: 'procedural' })),
    ...artifact.working.map(e => ({ ...e, category: 'working' })),
    ...(artifact.identity || []).map(e => ({ ...e, category: 'identity' }))
  ].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

  document.getElementById('stat-total').textContent = allEntries.length;
  renderEntries();
}

function renderEntries() {
  const container = document.getElementById('entries-container');
  const query = document.getElementById('search-input').value.toLowerCase().trim();

  let filtered = allEntries;

  // Filter by tab
  if (currentTab !== 'all') {
    filtered = filtered.filter(e => e.category === currentTab);
  }

  // Filter by search
  if (query) {
    filtered = filtered.filter(e => {
      const text = getEntryText(e).toLowerCase();
      return text.includes(query);
    });
  }

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🔍</div>
        <p>${query ? 'No matching memories' : 'No memories in this category'}</p>
      </div>
    `;
    return;
  }

  container.innerHTML = filtered.map(entry => {
    const content = escapeHtml(getEntryText(entry));
    const time = formatTime(entry.timestamp);
    const isSelected = selectedIds.has(entry.id);

    return `
      <div class="entry-card ${isSelected ? 'selected' : ''}" data-id="${entry.id}">
        <div class="entry-header">
          <span class="entry-badge badge-${entry.category}">${entry.category}</span>
          <span class="entry-time">${time}</span>
        </div>
        <div class="entry-content">${content}</div>
        <div class="entry-actions">
          <button class="select-btn" data-id="${entry.id}">${isSelected ? '✓ Selected' : 'Select'}</button>
          <button class="copy-btn" data-id="${entry.id}">Copy</button>
          <button class="delete-btn" data-id="${entry.id}">Delete</button>
        </div>
      </div>
    `;
  }).join('');

  // Attach event handlers
  container.querySelectorAll('.select-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleSelect(btn.dataset.id);
    });
  });

  container.querySelectorAll('.copy-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const entry = allEntries.find(en => en.id === btn.dataset.id);
      if (entry) {
        navigator.clipboard.writeText(getEntryText(entry));
        btn.textContent = 'Copied!';
        setTimeout(() => btn.textContent = 'Copy', 1000);
      }
    });
  });

  container.querySelectorAll('.delete-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      await chrome.runtime.sendMessage({ action: 'removeEntry', id: btn.dataset.id });
      selectedIds.delete(btn.dataset.id);
      await refreshEntries();
    });
  });

  // Click card to select
  container.querySelectorAll('.entry-card').forEach(card => {
    card.addEventListener('click', () => toggleSelect(card.dataset.id));
  });
}

function toggleSelect(id) {
  if (selectedIds.has(id)) {
    selectedIds.delete(id);
  } else {
    selectedIds.add(id);
  }
  updateInjectButton();
  renderEntries();
}

function updateInjectButton() {
  const btn = document.getElementById('inject-selected-btn');
  btn.disabled = selectedIds.size === 0;
  btn.textContent = selectedIds.size > 0 ? `Inject ${selectedIds.size} Selected` : 'Inject Selected';
}

async function handleInjectAll() {
  const response = await chrome.runtime.sendMessage({ action: 'getPromptContext' });
  if (response.context) {
    await navigator.clipboard.writeText(response.context);
    showToast('All memory context copied to clipboard!');
  }
}

async function handleInjectSelected() {
  if (selectedIds.size === 0) return;

  const selected = allEntries.filter(e => selectedIds.has(e.id));
  const parts = ['[Selected Memory Context from PAM]'];

  selected.forEach(entry => {
    parts.push(`- [${entry.category}] ${getEntryText(entry)}`);
  });

  const text = parts.join('\n');
  await navigator.clipboard.writeText(text);
  showToast(`${selectedIds.size} memories copied to clipboard!`);
}

async function handleExport() {
  const response = await chrome.runtime.sendMessage({ action: 'exportArtifact' });
  if (response.data) {
    const blob = new Blob([response.data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `memory_${new Date().toISOString().slice(0, 10)}.pam`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('Exported!');
  }
}

async function handleImport(e) {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = async (event) => {
    const response = await chrome.runtime.sendMessage({
      action: 'importArtifact',
      data: event.target.result
    });
    if (response.success) {
      await refreshEntries();
      showToast('Imported successfully!');
    } else {
      showToast(response.error || 'Import failed');
    }
  };
  reader.readAsText(file);
  e.target.value = '';
}

function getEntryText(entry) {
  switch (entry.category) {
    case 'semantic':
      return `${entry.subject} ${entry.predicate} ${entry.object}`;
    case 'procedural':
      return `${entry.name}: ${entry.description}`;
    case 'identity':
      return `${entry.key}: ${entry.value}`;
    default:
      return entry.content || '';
  }
}

function formatTime(timestamp) {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now - date;

  if (diff < 60000) return 'just now';
  if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago';
  if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago';
  return date.toLocaleDateString();
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function debounce(fn, ms) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

function showToast(message) {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  toast.style.cssText = `
    position: fixed;
    bottom: 60px;
    left: 50%;
    transform: translateX(-50%);
    background: var(--bg-tertiary);
    color: var(--accent-blue);
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 12px;
    border: 1px solid var(--accent-blue);
    z-index: 1000;
  `;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 2000);
}
