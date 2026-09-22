const button = document.getElementById('fill');
const refreshProfileButton = document.getElementById('refreshProfile');
const status = document.getElementById('status');

refreshProfileButton.addEventListener('click', async () => {
  refreshProfileButton.disabled = true;
  status.className = '';
  status.textContent = 'Refreshing profile...';
  try {
    const response = await chrome.runtime.sendMessage({ type: 'REFRESH_PROFILE' });
    if (!response?.ok) throw new Error(response?.error || 'Unable to refresh profile');
    status.className = 'success';
    status.textContent = 'Profile refreshed.';
  } catch (error) {
    status.className = 'error';
    status.textContent = error.message;
  } finally {
    refreshProfileButton.disabled = false;
  }
});

button.addEventListener('click', async () => {
  button.disabled = true;
  status.className = '';
  status.textContent = 'Inspecting form and loading profile...';
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const response = await chrome.runtime.sendMessage({ type: 'FILL_ACTIVE_TAB', tabId: tab.id });
    if (!response?.ok) throw new Error(response?.error || 'Unable to fill this page');
    const result = response.result?.result || {};
    status.className = 'success';
    status.textContent = `Filled ${result.filled?.length || 0} fields; ${result.skipped?.length || 0} need review.`;
  } catch (error) {
    status.className = 'error';
    status.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});
