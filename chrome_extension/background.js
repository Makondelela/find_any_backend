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

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type !== 'FILL_ACTIVE_TAB') return undefined;

  requestProfile()
    .then(profile =>
      chrome.tabs.sendMessage(message.tabId || sender.tab?.id, { type: 'FILL_PROFILE', profile })
    )
    .then(result => sendResponse({ ok: true, result }))
    .catch(error => sendResponse({ ok: false, error: error.message }));

  return true;
});
