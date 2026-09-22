const DEFAULT_APP_URL = 'https://find-any-backend-1.onrender.com';
const PROFILE_CACHE_KEY = 'profileCache';
const PROFILE_CACHE_TTL_MS = 2 * 60 * 60 * 1000;

async function getAppUrl() {
  const stored = await chrome.storage.sync.get({ appUrl: DEFAULT_APP_URL });
  return stored.appUrl.replace(/\/$/, '');
}

async function requestProfile(forceRefresh = false) {
  const appUrl = await getAppUrl();
  if (!forceRefresh) {
    const stored = await chrome.storage.local.get(PROFILE_CACHE_KEY);
    const cached = stored[PROFILE_CACHE_KEY];
    if (cached && cached.appUrl === appUrl && Date.now() - cached.fetchedAt < PROFILE_CACHE_TTL_MS) {
      return { profile: cached.profile, fieldMappings: cached.fieldMappings, cached: true };
    }
  }
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
  const result = { profile: data.profile, fieldMappings: data.field_mappings || {} };
  await chrome.storage.local.set({
    [PROFILE_CACHE_KEY]: { ...result, appUrl, fetchedAt: Date.now() },
  });
  return { ...result, cached: false };
}

async function fillTab(tabId, profile, fieldMappings) {
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

  return chrome.tabs.sendMessage(tabId, { type: 'FILL_PROFILE', profile, fieldMappings });
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'REFRESH_PROFILE') {
    requestProfile(true)
      .then(() => sendResponse({ ok: true }))
      .catch(error => sendResponse({ ok: false, error: error.message }));
    return true;
  }
  if (message.type !== 'FILL_ACTIVE_TAB') return undefined;

  requestProfile()
    .then(({ profile, fieldMappings }) => fillTab(
      message.tabId || sender.tab?.id,
      profile,
      fieldMappings,
    ))
    .then(result => sendResponse({ ok: true, result }))
    .catch(error => {
      const messageText = error.message.includes('Receiving end does not exist')
        ? 'The form helper could not start on this tab. Refresh the application page and try again.'
        : error.message;
      sendResponse({ ok: false, error: messageText });
    });

  return true;
});
