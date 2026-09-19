const DEFAULT_APP_URL = 'https://find-any-backend-1.onrender.com';
const appUrl = document.getElementById('appUrl');
const status = document.getElementById('status');

chrome.storage.sync.get({ appUrl: DEFAULT_APP_URL }).then(values => {
  appUrl.value = values.appUrl;
});

document.getElementById('save').addEventListener('click', async () => {
  const value = appUrl.value.trim().replace(/\/$/, '');
  if (!/^https?:\/\//i.test(value)) {
    status.textContent = 'Enter a valid http(s) URL.';
    return;
  }
  await chrome.storage.sync.set({ appUrl: value });
  status.textContent = 'Saved.';
});
