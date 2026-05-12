/**
 * PAM Background Service Worker
 * Handles storage, messaging between popup/sidebar/content scripts, and side panel.
 */

importScripts('../lib/pam-core.js');

// Initialize storage on install
chrome.runtime.onInstalled.addListener(async () => {
  const existing = await chrome.storage.local.get('pam_artifact');
  if (!existing.pam_artifact) {
    const pam = new PamArtifact();
    await chrome.storage.local.set({ pam_artifact: pam.toPlainObject() });
  }
});

// Enable side panel on supported sites
chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: false }).catch(() => {});

// Message handler for communication between extension components
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handleMessage(message, sender).then(sendResponse).catch(err => {
    sendResponse({ error: err.message });
  });
  return true; // Keep channel open for async response
});

async function handleMessage(message, sender) {
  switch (message.action) {
    case 'getArtifact':
      return getArtifact();

    case 'getStats':
      return getStats();

    case 'addEpisodic':
      return addEntry('episodic', message.data);

    case 'addSemantic':
      return addEntry('semantic', message.data);

    case 'addProcedural':
      return addEntry('procedural', message.data);

    case 'addWorking':
      return addEntry('working', message.data);

    case 'addIdentity':
      return addEntry('identity', message.data);

    case 'removeEntry':
      return removeEntry(message.id);

    case 'getPromptContext':
      return getPromptContext(message.task);

    case 'importArtifact':
      return importArtifact(message.data);

    case 'exportArtifact':
      return exportArtifact();

    case 'search':
      return searchMemories(message.query);

    case 'clearAll':
      return clearAll();

    default:
      return { error: 'Unknown action: ' + message.action };
  }
}

async function getArtifact() {
  const result = await chrome.storage.local.get('pam_artifact');
  return result.pam_artifact || new PamArtifact().toPlainObject();
}

async function getStats() {
  const artifact = await getArtifact();
  const pam = PamArtifact.fromObject(artifact);
  return pam.getStats();
}

async function addEntry(category, data) {
  const artifact = await getArtifact();
  const pam = PamArtifact.fromObject(artifact);

  switch (category) {
    case 'episodic':
      await pam.addEpisodic(data.content, data.event_type || 'observation');
      break;
    case 'semantic':
      await pam.addSemantic(data.subject, data.predicate, data.object, data.confidence || 1.0);
      break;
    case 'procedural':
      await pam.addProcedural(data.name, data.description, data.steps || [], data.language || 'natural');
      break;
    case 'working':
      await pam.addWorking(data.content, data.goals || [], data.context || {});
      break;
    case 'identity':
      await pam.addIdentity(data.key, data.value);
      break;
  }

  await chrome.storage.local.set({ pam_artifact: pam.toPlainObject() });
  return { success: true, stats: pam.getStats() };
}

async function removeEntry(id) {
  const artifact = await getArtifact();
  const pam = PamArtifact.fromObject(artifact);
  const removed = pam.removeEntry(id);
  if (removed) {
    await chrome.storage.local.set({ pam_artifact: pam.toPlainObject() });
  }
  return { success: removed, stats: pam.getStats() };
}

async function getPromptContext(task = "") {
  const artifact = await getArtifact();
  const pam = PamArtifact.fromObject(artifact);
  return { context: pam.toPromptContext(task) };
}

async function importArtifact(data) {
  try {
    const imported = typeof data === 'string' ? JSON.parse(data) : data;
    const pam = PamArtifact.fromObject(imported);
    await chrome.storage.local.set({ pam_artifact: pam.toPlainObject() });
    return { success: true, stats: pam.getStats() };
  } catch (err) {
    return { error: 'Invalid PAM file: ' + err.message };
  }
}

async function exportArtifact() {
  const artifact = await getArtifact();
  const pam = PamArtifact.fromObject(artifact);
  const json = await pam.toJSON();
  return { data: json };
}

async function searchMemories(query) {
  const artifact = await getArtifact();
  const pam = PamArtifact.fromObject(artifact);
  return { results: pam.search(query) };
}

async function clearAll() {
  const pam = new PamArtifact();
  await chrome.storage.local.set({ pam_artifact: pam.toPlainObject() });
  return { success: true, stats: pam.getStats() };
}

// Context menu for "Remember selected text"
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'pam-remember',
    title: 'Remember with PAM',
    contexts: ['selection']
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === 'pam-remember' && info.selectionText) {
    await addEntry('episodic', {
      content: info.selectionText,
      event_type: 'user_highlighted'
    });
    // Notify content script to show confirmation
    chrome.tabs.sendMessage(tab.id, {
      action: 'showNotification',
      message: 'Remembered!'
    }).catch(() => {});
  }
});
