/**
 * PAM Popup Script
 * Handles UI interactions for the extension popup.
 */

document.addEventListener('DOMContentLoaded', init);

async function init() {
  await refreshStats();
  await refreshMemoryList();
  setupEventListeners();
}

function setupEventListeners() {
  // Remember button
  document.getElementById('remember-btn').addEventListener('click', handleRemember);
  document.getElementById('remember-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleRemember();
  });

  // Memory type selector — show/hide extra fields
  document.getElementById('memory-type').addEventListener('change', (e) => {
    document.getElementById('semantic-form').style.display = e.target.value === 'semantic' ? 'block' : 'none';
    document.getElementById('procedural-form').style.display = e.target.value === 'procedural' ? 'block' : 'none';
  });

  // Action buttons
  document.getElementById('inject-btn').addEventListener('click', handleInject);
  document.getElementById('export-btn').addEventListener('click', handleExport);
  document.getElementById('import-btn').addEventListener('click', () => document.getElementById('import-file').click());
  document.getElementById('import-file').addEventListener('change', handleImport);

  // Open sidebar
  document.getElementById('open-sidebar').addEventListener('click', (e) => {
    e.preventDefault();
    chrome.sidePanel.open({ windowId: chrome.windows.WINDOW_ID_CURRENT }).catch(() => {
      // Fallback: open sidebar.html in new tab
      chrome.tabs.create({ url: chrome.runtime.getURL('sidebar/sidebar.html') });
    });
  });

  // Settings
  document.getElementById('settings-btn').addEventListener('click', () => {
    chrome.tabs.create({ url: chrome.runtime.getURL('sidebar/sidebar.html#settings') });
  });
}

async function handleRemember() {
  const input = document.getElementById('remember-input');
  const type = document.getElementById('memory-type').value;
  const content = input.value.trim();

  if (!content && type !== 'semantic' && type !== 'procedural') return;

  let data;
  switch (type) {
    case 'episodic':
      data = { content, event_type: 'user_note' };
      await chrome.runtime.sendMessage({ action: 'addEpisodic', data });
      break;
    case 'semantic': {
      const subject = document.getElementById('sem-subject').value.trim() || content;
      const predicate = document.getElementById('sem-predicate').value.trim() || 'is';
      const object = document.getElementById('sem-object').value.trim() || content;
      data = { subject, predicate, object };
      await chrome.runtime.sendMessage({ action: 'addSemantic', data });
      document.getElementById('sem-subject').value = '';
      document.getElementById('sem-predicate').value = '';
      document.getElementById('sem-object').value = '';
      break;
    }
    case 'procedural': {
      const name = document.getElementById('proc-name').value.trim() || content;
      const desc = document.getElementById('proc-desc').value.trim() || content;
      data = { name, description: desc };
      await chrome.runtime.sendMessage({ action: 'addProcedural', data });
      document.getElementById('proc-name').value = '';
      document.getElementById('proc-desc').value = '';
      break;
    }
    case 'working':
      data = { content, goals: [] };
      await chrome.runtime.sendMessage({ action: 'addWorking', data });
      break;
  }

  input.value = '';
  await refreshStats();
  await refreshMemoryList();
}

async function handleInject() {
  try {
    const response = await chrome.runtime.sendMessage({ action: 'getPromptContext' });
    if (response.context) {
      // Try to inject into active tab
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab) {
        try {
          await chrome.tabs.sendMessage(tab.id, { action: 'injectText', text: response.context });
        } catch {
          // Fallback: copy to clipboard
          await navigator.clipboard.writeText(response.context);
          showToast('Copied to clipboard!');
          return;
        }
      }
      showToast('Injected!');
    } else {
      showToast('No memories to inject');
    }
  } catch (err) {
    showToast('Error: ' + err.message);
  }
}

async function handleExport() {
  try {
    const response = await chrome.runtime.sendMessage({ action: 'exportArtifact' });
    if (response.data) {
      const blob = new Blob([response.data], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `memory_${new Date().toISOString().slice(0,10)}.pam`;
      a.click();
      URL.revokeObjectURL(url);
      showToast('Exported!');
    }
  } catch (err) {
    showToast('Export failed');
  }
}

async function handleImport(e) {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = async (event) => {
    try {
      const response = await chrome.runtime.sendMessage({
        action: 'importArtifact',
        data: event.target.result
      });
      if (response.success) {
        await refreshStats();
        await refreshMemoryList();
        showToast('Imported successfully!');
      } else {
        showToast(response.error || 'Import failed');
      }
    } catch (err) {
      showToast('Import error');
    }
  };
  reader.readAsText(file);
  e.target.value = '';
}

async function refreshStats() {
  const stats = await chrome.runtime.sendMessage({ action: 'getStats' });
  document.getElementById('stat-episodic').textContent = stats.episodic || 0;
  document.getElementById('stat-semantic').textContent = stats.semantic || 0;
  document.getElementById('stat-procedural').textContent = stats.procedural || 0;
}

async function refreshMemoryList() {
  const artifact = await chrome.runtime.sendMessage({ action: 'getArtifact' });
  const list = document.getElementById('memory-list');

  const allEntries = [
    ...artifact.episodic.map(e => ({ ...e, category: 'episodic' })),
    ...artifact.semantic.map(e => ({ ...e, category: 'semantic' })),
    ...artifact.procedural.map(e => ({ ...e, category: 'procedural' })),
    ...artifact.working.map(e => ({ ...e, category: 'working' }))
  ].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)).slice(0, 10);

  if (allEntries.length === 0) {
    list.innerHTML = '<div class="empty-state">No memories yet. Start remembering!</div>';
    return;
  }

  list.innerHTML = allEntries.map(entry => {
    let content;
    if (entry.category === 'semantic') {
      content = `${entry.subject} ${entry.predicate} ${entry.object}`;
    } else if (entry.category === 'procedural') {
      content = `${entry.name}: ${entry.description}`;
    } else {
      content = entry.content;
    }
    return `
      <div class="memory-item" data-id="${entry.id}">
        <span class="memory-badge badge-${entry.category}">${entry.category.slice(0, 4)}</span>
        <span class="memory-content" title="${escapeHtml(content)}">${escapeHtml(content)}</span>
        <button class="memory-delete" data-id="${entry.id}" title="Delete">×</button>
      </div>
    `;
  }).join('');

  // Attach delete handlers
  list.querySelectorAll('.memory-delete').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const id = btn.dataset.id;
      await chrome.runtime.sendMessage({ action: 'removeEntry', id });
      await refreshStats();
      await refreshMemoryList();
    });
  });
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function showToast(message) {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  toast.style.cssText = `
    position: fixed;
    bottom: 12px;
    left: 50%;
    transform: translateX(-50%);
    background: var(--bg-tertiary);
    color: var(--accent-blue);
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 12px;
    border: 1px solid var(--accent-blue);
    z-index: 1000;
    animation: fadeIn 0.2s ease;
  `;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 2000);
}
