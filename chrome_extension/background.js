const DEFAULT_APP_URL = 'https://find-any-backend-1.onrender.com';

async function getAppUrl() {
  const stored = await chrome.storage.sync.get({ appUrl: DEFAULT_APP_URL });
  return stored.appUrl.replace(/\/$/, '');
}

async function requestProfile() {
  const appUrl = await getAppUrl();
  const response = await fetch(`${appUrl}/api/profile`, {
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });
  const data = await response.json().catch(() => ({}));
  if (response.status === 401) {
    throw new Error(`Sign in to FindFast first: ${appUrl}/login`);
  }
  if (!response.ok || !data.success) {
    throw new Error(data.error || `FindFast returned HTTP ${response.status}`);
  }
  return data.profile;
}

async function fillTab(tabId, profile) {
  if (!tabId) throw new Error('No active tab was found.');

  try {
    await chrome.scripting.executeScript({
      target: { tabId },
      files: ['content.js'],
    });
  } catch (error) {
    throw new Error(
      'This page does not allow extensions. Open the application in a normal web tab, then try again.'
    );
  }

  return chrome.tabs.sendMessage(tabId, { type: 'FILL_PROFILE', profile });
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type !== 'FILL_ACTIVE_TAB') return undefined;

  requestProfile()
    .then(profile => fillTab(message.tabId || sender.tab?.id, profile))
    .then(result => sendResponse({ ok: true, result }))
    .catch(error => {
      const messageText = error.message.includes('Receiving end does not exist')
        ? 'The form helper could not start on this tab. Refresh the application page and try again.'
        : error.message;
      sendResponse({ ok: false, error: messageText });
    });

  return true;
});
