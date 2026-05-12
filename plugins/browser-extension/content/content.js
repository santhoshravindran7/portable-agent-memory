/**
 * PAM Content Script
 * Runs on supported AI chat pages. Provides floating button,
 * text selection tooltip, and chat injection capabilities.
 */

(function() {
  'use strict';

  // Avoid double-injection
  if (window.__pamContentLoaded) return;
  window.__pamContentLoaded = true;

  const SUPPORTED_SITES = {
    'chat.openai.com': {
      name: 'ChatGPT',
      inputSelector: '#prompt-textarea, textarea[data-id], div[id="prompt-textarea"]',
      isContentEditable: true
    },
    'chatgpt.com': {
      name: 'ChatGPT',
      inputSelector: '#prompt-textarea, textarea[data-id], div[id="prompt-textarea"]',
      isContentEditable: true
    },
    'claude.ai': {
      name: 'Claude',
      inputSelector: 'div[contenteditable="true"].ProseMirror, div[contenteditable="true"]',
      isContentEditable: true
    },
    'gemini.google.com': {
      name: 'Gemini',
      inputSelector: 'div.ql-editor, rich-textarea .ql-editor, div[contenteditable="true"]',
      isContentEditable: true
    },
    'copilot.microsoft.com': {
      name: 'Copilot',
      inputSelector: '#searchbox textarea, textarea[id*="cib"], #userInput',
      isContentEditable: false
    }
  };

  const currentHost = window.location.hostname;
  const siteConfig = SUPPORTED_SITES[currentHost];
  if (!siteConfig) return;

  // Inject styles
  const style = document.createElement('style');
  style.textContent = `
    .pam-floating-btn {
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: 48px;
      height: 48px;
      border-radius: 50%;
      background: linear-gradient(135deg, #4ea8de, #7c3aed);
      border: none;
      cursor: pointer;
      box-shadow: 0 4px 16px rgba(78, 168, 222, 0.4);
      z-index: 999999;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 0.2s, box-shadow 0.2s;
      font-size: 20px;
    }
    .pam-floating-btn:hover {
      transform: scale(1.1);
      box-shadow: 0 6px 24px rgba(78, 168, 222, 0.6);
    }
    .pam-floating-btn svg {
      width: 24px;
      height: 24px;
      fill: white;
    }
    .pam-tooltip {
      position: absolute;
      background: #1a1a2e;
      color: #e0e0e0;
      border: 1px solid #4ea8de;
      border-radius: 8px;
      padding: 8px 12px;
      font-size: 13px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      cursor: pointer;
      z-index: 9999999;
      box-shadow: 0 4px 12px rgba(0,0,0,0.4);
      transition: opacity 0.2s;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .pam-tooltip:hover {
      background: #2a2a4e;
    }
    .pam-tooltip svg {
      width: 14px;
      height: 14px;
      fill: #4ea8de;
    }
    .pam-notification {
      position: fixed;
      top: 20px;
      right: 20px;
      background: #1a1a2e;
      color: #4ea8de;
      border: 1px solid #4ea8de;
      border-radius: 8px;
      padding: 12px 20px;
      font-size: 14px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      z-index: 9999999;
      box-shadow: 0 4px 16px rgba(0,0,0,0.4);
      animation: pamSlideIn 0.3s ease, pamFadeOut 0.3s ease 1.7s forwards;
    }
    @keyframes pamSlideIn {
      from { transform: translateX(100px); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
    }
    @keyframes pamFadeOut {
      from { opacity: 1; }
      to { opacity: 0; }
    }
    .pam-quick-menu {
      position: fixed;
      bottom: 80px;
      right: 24px;
      background: #1a1a2e;
      border: 1px solid #333;
      border-radius: 12px;
      padding: 12px;
      z-index: 999998;
      box-shadow: 0 8px 32px rgba(0,0,0,0.5);
      min-width: 200px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    .pam-quick-menu button {
      display: block;
      width: 100%;
      padding: 10px 14px;
      margin: 4px 0;
      background: #2a2a4e;
      color: #e0e0e0;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      font-size: 13px;
      text-align: left;
      transition: background 0.2s;
    }
    .pam-quick-menu button:hover {
      background: #3a3a6e;
    }
    .pam-quick-menu .pam-menu-title {
      color: #4ea8de;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 1px;
      padding: 4px 14px;
      margin-bottom: 4px;
    }
  `;
  document.head.appendChild(style);

  // Brain SVG icon
  const brainSvg = `<svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>`;
  const memorySvg = `<svg viewBox="0 0 24 24"><path d="M12 2a9 9 0 0 0-9 9c0 3.07 1.53 5.78 3.87 7.41C8.24 19.41 10.03 20 12 20s3.76-.59 5.13-1.59C19.47 16.78 21 14.07 21 11a9 9 0 0 0-9-9zm0 16c-3.87 0-7-3.13-7-7s3.13-7 7-7 7 3.13 7 7-3.13 7-7 7zm1-11h-2v3H8v2h3v3h2v-3h3v-2h-3V7z"/></svg>`;

  // Create floating PAM button
  const floatingBtn = document.createElement('button');
  floatingBtn.className = 'pam-floating-btn';
  floatingBtn.innerHTML = memorySvg;
  floatingBtn.title = 'Portable Agent Memory';
  document.body.appendChild(floatingBtn);

  let quickMenuVisible = false;
  let quickMenu = null;

  floatingBtn.addEventListener('click', () => {
    if (quickMenuVisible) {
      hideQuickMenu();
    } else {
      showQuickMenu();
    }
  });

  function showQuickMenu() {
    quickMenu = document.createElement('div');
    quickMenu.className = 'pam-quick-menu';
    quickMenu.innerHTML = `
      <div class="pam-menu-title">PAM · ${siteConfig.name}</div>
      <button id="pam-inject-context">💉 Inject Memory Context</button>
      <button id="pam-inject-clipboard">📋 Copy Context to Clipboard</button>
      <button id="pam-remember-page">🧠 Remember Current Page</button>
      <button id="pam-open-sidebar">📂 Open Side Panel</button>
    `;
    document.body.appendChild(quickMenu);
    quickMenuVisible = true;

    quickMenu.querySelector('#pam-inject-context').addEventListener('click', injectContext);
    quickMenu.querySelector('#pam-inject-clipboard').addEventListener('click', copyContextToClipboard);
    quickMenu.querySelector('#pam-remember-page').addEventListener('click', rememberPage);
    quickMenu.querySelector('#pam-open-sidebar').addEventListener('click', () => {
      chrome.runtime.sendMessage({ action: 'openSidePanel' });
      hideQuickMenu();
    });

    // Close on outside click
    setTimeout(() => {
      document.addEventListener('click', outsideClickHandler);
    }, 0);
  }

  function hideQuickMenu() {
    if (quickMenu) {
      quickMenu.remove();
      quickMenu = null;
    }
    quickMenuVisible = false;
    document.removeEventListener('click', outsideClickHandler);
  }

  function outsideClickHandler(e) {
    if (quickMenu && !quickMenu.contains(e.target) && e.target !== floatingBtn) {
      hideQuickMenu();
    }
  }

  // Inject memory context into the chat input
  async function injectContext() {
    hideQuickMenu();
    try {
      const response = await chrome.runtime.sendMessage({ action: 'getPromptContext' });
      if (response.context) {
        const input = document.querySelector(siteConfig.inputSelector);
        if (input) {
          if (siteConfig.isContentEditable) {
            // For contenteditable divs
            input.focus();
            const p = document.createElement('p');
            p.textContent = response.context;
            input.appendChild(p);
            // Trigger input event for frameworks
            input.dispatchEvent(new Event('input', { bubbles: true }));
          } else {
            // For textarea elements
            input.focus();
            input.value = response.context;
            input.dispatchEvent(new Event('input', { bubbles: true }));
          }
          showNotification('Memory context injected!');
        } else {
          // Fallback to clipboard
          await navigator.clipboard.writeText(response.context);
          showNotification('Copied to clipboard (input not found)');
        }
      }
    } catch (err) {
      showNotification('Error: ' + err.message);
    }
  }

  async function copyContextToClipboard() {
    hideQuickMenu();
    try {
      const response = await chrome.runtime.sendMessage({ action: 'getPromptContext' });
      if (response.context) {
        await navigator.clipboard.writeText(response.context);
        showNotification('Memory context copied to clipboard!');
      }
    } catch (err) {
      showNotification('Error: ' + err.message);
    }
  }

  async function rememberPage() {
    hideQuickMenu();
    const pageTitle = document.title;
    const url = window.location.href;
    await chrome.runtime.sendMessage({
      action: 'addEpisodic',
      data: {
        content: `Visited ${siteConfig.name}: "${pageTitle}" at ${url}`,
        event_type: 'page_visit'
      }
    });
    showNotification('Page remembered!');
  }

  // Text selection tooltip
  let selectionTooltip = null;

  document.addEventListener('mouseup', (e) => {
    setTimeout(() => {
      const selection = window.getSelection();
      const text = selection.toString().trim();

      if (selectionTooltip) {
        selectionTooltip.remove();
        selectionTooltip = null;
      }

      if (text.length > 5 && text.length < 2000) {
        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();

        selectionTooltip = document.createElement('div');
        selectionTooltip.className = 'pam-tooltip';
        selectionTooltip.innerHTML = `${memorySvg} Remember this`;
        selectionTooltip.style.top = (rect.top + window.scrollY - 40) + 'px';
        selectionTooltip.style.left = (rect.left + window.scrollX) + 'px';
        document.body.appendChild(selectionTooltip);

        selectionTooltip.addEventListener('click', async () => {
          await chrome.runtime.sendMessage({
            action: 'addEpisodic',
            data: { content: text, event_type: 'user_highlighted' }
          });
          showNotification('Remembered!');
          selectionTooltip.remove();
          selectionTooltip = null;
        });
      }
    }, 10);
  });

  // Hide tooltip on click elsewhere
  document.addEventListener('mousedown', (e) => {
    if (selectionTooltip && !selectionTooltip.contains(e.target)) {
      selectionTooltip.remove();
      selectionTooltip = null;
    }
  });

  // Notification helper
  function showNotification(message) {
    const notif = document.createElement('div');
    notif.className = 'pam-notification';
    notif.textContent = message;
    document.body.appendChild(notif);
    setTimeout(() => notif.remove(), 2000);
  }

  // Listen for messages from background/popup
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === 'showNotification') {
      showNotification(message.message);
    } else if (message.action === 'injectText') {
      const input = document.querySelector(siteConfig.inputSelector);
      if (input) {
        if (siteConfig.isContentEditable) {
          input.focus();
          const p = document.createElement('p');
          p.textContent = message.text;
          input.appendChild(p);
          input.dispatchEvent(new Event('input', { bubbles: true }));
        } else {
          input.focus();
          input.value = message.text;
          input.dispatchEvent(new Event('input', { bubbles: true }));
        }
        sendResponse({ success: true });
      } else {
        sendResponse({ success: false, error: 'Input not found' });
      }
    }
    return true;
  });
})();
