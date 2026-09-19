/* ═══════════════════════════════════════════════════════════════════════════
   FindFast - Application Assistant integration
   Talks to the hosted assistant server (app.py) which drives a headless
   Chrome instance server-side. "View Job" opens the link there instead of a
   plain new browser tab, and a polled screenshot is rendered into an <img>
   so the page is actually visible, since a headless server-side browser has
   no window to show directly. Click/type/scroll on the screenshot are
   forwarded to the remote page. "Fill In" auto-populates whatever
   application form is currently loaded.
   ═══════════════════════════════════════════════════════════════════════════ */

const ASSISTANT_BASE = '/assistant';
let assistantOpenSequence = 0;
let assistantLastUrl = '';
let assistantStatusPoller = null;
let assistantScreenshotPoller = null;
let assistantWebviewHidden = false;

function assistantEls() {
    return {
        panel: document.getElementById('assistantPanel'),
        header: document.getElementById('assistantHeader'),
        urlInput: document.getElementById('assistantUrl'),
        copyBtn: document.getElementById('assistantCopyBtn'),
        refreshBtn: document.getElementById('assistantRefreshBtn'),
        fillBtn: document.getElementById('assistantFillBtn'),
        log: document.getElementById('assistantLog'),
        screenshot: document.getElementById('assistantScreenshot'),
        webview: document.getElementById('assistantWebview'),
        webviewStage: document.querySelector('.assistant-webview-stage'),
        dropdown: document.getElementById('assistantDropdown'),
        webviewCloseBtn: document.getElementById('assistantWebviewCloseBtn'),
    };
}

function assistantLog(message, isError) {
    const { log } = assistantEls();
    if (!log) return;
    const line = document.createElement('div');
    line.className = isError ? 'assistant-log-line assistant-log-error' : 'assistant-log-line';
    line.textContent = message;
    log.prepend(line);
}

function clearAssistantState() {
    const { urlInput, log, screenshot, webview, dropdown } = assistantEls();
    assistantLastUrl = '';
    assistantWebviewHidden = false;
    if (urlInput) urlInput.value = '';
    if (log) log.replaceChildren();
    if (screenshot) screenshot.removeAttribute('src');
    if (dropdown) {
        dropdown.replaceChildren();
        dropdown.hidden = true;
    }
    if (webview) webview.style.display = 'none';
}

function assistantExpand() {
    const { panel } = assistantEls();
    panel.classList.remove('assistant-collapsed');
}

async function assistantCall(path, options) {
    const response = await fetch(`${ASSISTANT_BASE}${path}`, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.ok === false) {
        throw new Error(data.error || `Request to ${path} failed`);
    }
    return data;
}

/**
 * Open a job/application URL in the shared assistant browser window
 * instead of a plain new tab.
 */
async function openInAssistant(url) {
    const openSequence = ++assistantOpenSequence;
    assistantExpand();
    clearAssistantState();
    assistantLog(`Starting a fresh application context for: ${url}`);
    try {
        await assistantCall('/api/reset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
        });
    } catch (err) {
        assistantLog(`Could not reset the previous application: ${err.message}`, true);
    }

    // A newer View Job click owns the browser now.
    if (openSequence !== assistantOpenSequence) return;

    assistantLog(`Opening in assistant browser: ${url}`);
    try {
        const data = await assistantCall('/api/open', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url }),
        });
        assistantLastUrl = data.url || url;
        assistantEls().urlInput.value = assistantLastUrl;
        assistantLog('Opened. Sign in / navigate to the application form, then click Fill In.');
    } catch (err) {
        assistantLog(
            `The hosted assistant browser could not open this job. Opening it in a normal tab instead. ${err.message}`,
            true
        );
        window.open(url, '_blank', 'noopener,noreferrer');
    }
}

async function assistantRefreshStatus(isPolling = false) {
    try {
        const data = await assistantCall('/api/status', { method: 'GET' });
        const currentUrl = data.running ? (data.url || '') : '';
        const changed = currentUrl !== assistantLastUrl;
        assistantLastUrl = currentUrl;
        assistantEls().urlInput.value = currentUrl;
        if (!data.running && changed) {
            assistantLog('Assistant browser is not open yet - click a job\'s "View Job" button to start.');
        }
    } catch (err) {
        // Avoid filling the assistant log with the same polling error every
        // two seconds; the manual refresh button still reports it immediately.
        if (!isPolling) {
            assistantLog(`Assistant server unreachable: ${err.message}`, true);
        }
    }
}

function startAssistantStatusPolling() {
    if (assistantStatusPoller) clearInterval(assistantStatusPoller);
    assistantStatusPoller = setInterval(() => assistantRefreshStatus(true), 2000);
}

async function assistantRefreshScreenshot() {
    const { screenshot, webview } = assistantEls();
    if (!screenshot) return;
    try {
        const data = await assistantCall('/api/screenshot', { method: 'GET' });
        if (data.running && data.image) {
            screenshot.src = data.image;
            if (webview && !assistantWebviewHidden) webview.style.display = 'flex';
        } else {
            screenshot.removeAttribute('src');
            if (webview) webview.style.display = 'none';
        }
    } catch (err) {
        // Silent: the status poller already reports connectivity errors,
        // no need to duplicate them every second.
    }
}

function startAssistantScreenshotPolling() {
    if (assistantScreenshotPoller) clearInterval(assistantScreenshotPoller);
    assistantScreenshotPoller = setInterval(assistantRefreshScreenshot, 1000);
}

// Map a click/coords on the displayed (possibly scaled) <img> back to real
// pixel coordinates in the remote page's viewport.
function assistantImageToPageCoords(img, clientX, clientY) {
    const rect = img.getBoundingClientRect();
    const scaleX = img.naturalWidth / rect.width;
    const scaleY = img.naturalHeight / rect.height;
    return {
        x: (clientX - rect.left) * scaleX,
        y: (clientY - rect.top) * scaleY,
    };
}

async function assistantHandleClick(event) {
    const { screenshot, dropdown } = assistantEls();
    if (!screenshot || !screenshot.naturalWidth) return;
    screenshot.focus();
    const { x, y } = assistantImageToPageCoords(screenshot, event.clientX, event.clientY);
    try {
        const data = await assistantCall('/api/click', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ x, y }),
        });
        if (data.dropdown) assistantShowDropdown(data.dropdown, event.clientX, event.clientY);
        else if (dropdown) dropdown.hidden = true;
    } catch (err) {
        assistantLog(`Click failed: ${err.message}`, true);
    }
    assistantRefreshScreenshot();
}

function assistantShowDropdown(dropdownData, clientX, clientY) {
    const { dropdown, webviewStage } = assistantEls();
    if (!dropdown || !webviewStage) return;
    dropdown.replaceChildren();
    const stageRect = webviewStage.getBoundingClientRect();
    dropdown.style.left = `${Math.max(4, clientX - stageRect.left)}px`;
    dropdown.style.top = `${Math.max(4, clientY - stageRect.top)}px`;

    dropdownData.options.forEach(option => {
        const optionButton = document.createElement('button');
        optionButton.type = 'button';
        optionButton.className = 'assistant-dropdown-option';
        optionButton.textContent = option.label || '(blank)';
        optionButton.disabled = option.disabled;
        if (option.selected) optionButton.classList.add('selected');
        optionButton.addEventListener('click', async event => {
            event.stopPropagation();
            try {
                await assistantCall('/api/select', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        fieldId: dropdownData.id,
                        fieldName: dropdownData.name,
                        index: option.index,
                    }),
                });
                dropdown.hidden = true;
                assistantLog(`Selected: ${option.label || '(blank)'}`);
                assistantRefreshScreenshot();
            } catch (err) {
                assistantLog(`Dropdown selection failed: ${err.message}`, true);
            }
        });
        dropdown.appendChild(optionButton);
    });
    dropdown.hidden = false;
}

const ASSISTANT_MODIFIER_KEYS = new Set(['Shift', 'Control', 'Alt', 'Meta', 'CapsLock']);

async function assistantHandleKeydown(event) {
    if (ASSISTANT_MODIFIER_KEYS.has(event.key)) return;
    event.preventDefault();
    try {
        await assistantCall('/api/key', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key: event.key }),
        });
    } catch (err) {
        assistantLog(`Key press failed: ${err.message}`, true);
    }
    assistantRefreshScreenshot();
}

let assistantScrollBusy = false;

async function assistantHandleWheel(event) {
    event.preventDefault();
    if (assistantScrollBusy) return;
    assistantScrollBusy = true;
    try {
        await assistantCall('/api/scroll', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ deltaX: event.deltaX, deltaY: event.deltaY }),
        });
    } catch (err) {
        // Silent: wheel events fire rapidly, avoid spamming the log.
    } finally {
        assistantScrollBusy = false;
    }
    assistantRefreshScreenshot();
}

async function assistantFillIn() {
    assistantLog('Filling in the current page...');
    try {
        const data = await assistantCall('/api/fill', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}),
        });
        assistantEls().urlInput.value = data.url || '';
        const filled = data.filled || [];
        const skipped = data.skipped || [];
        assistantLog(
            filled.length ? `Filled: ${filled.join(', ')}` : 'No matching fields were found to fill.'
        );
        if (skipped.length) {
            assistantLog(`Skipped (no match for CV data): ${skipped.join(', ')}`);
        }
    } catch (err) {
        assistantLog(`Fill in failed: ${err.message}`, true);
    }
    assistantRefreshScreenshot();
}

function assistantCopyLink() {
    const { urlInput } = assistantEls();
    if (!urlInput.value) return;
    navigator.clipboard
        .writeText(urlInput.value)
        .then(() => assistantLog('Link copied to clipboard.'))
        .catch(() => assistantLog('Could not copy link.', true));
}

document.addEventListener('DOMContentLoaded', () => {
    const { header, copyBtn, refreshBtn, fillBtn, panel, screenshot, webview, webviewCloseBtn, dropdown } = assistantEls();
    if (!panel) return;

    header.addEventListener('click', () => {
        const collapsed = panel.classList.toggle('assistant-collapsed');
        // Re-expanding the small tab also brings back a preview you'd closed.
        if (!collapsed) assistantWebviewHidden = false;
    });
    copyBtn.addEventListener('click', assistantCopyLink);
    refreshBtn.addEventListener('click', assistantRefreshStatus);
    fillBtn.addEventListener('click', assistantFillIn);

    if (webviewCloseBtn) {
        webviewCloseBtn.addEventListener('click', () => {
            assistantWebviewHidden = true;
            if (webview) webview.style.display = 'none';
            if (dropdown) dropdown.hidden = true;
        });
    }

    if (screenshot) {
        screenshot.addEventListener('click', assistantHandleClick);
        screenshot.addEventListener('keydown', assistantHandleKeydown);
        screenshot.addEventListener('wheel', assistantHandleWheel, { passive: false });
    }

    assistantRefreshStatus();
    startAssistantStatusPolling();
    startAssistantScreenshotPolling();
});
