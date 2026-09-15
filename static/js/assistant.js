/* ═══════════════════════════════════════════════════════════════════════════
   FindFast - Application Assistant integration
   Talks to the hosted assistant server (app.py) which drives a headless
   Chrome instance server-side. "View Job" opens the link there instead of a
   plain new browser tab, and a polled screenshot is rendered into an <img>
   so the page is actually visible, since a headless server-side browser has
   no window to show directly. "Fill In" auto-populates whatever application
   form is currently loaded.
   ═══════════════════════════════════════════════════════════════════════════ */

const ASSISTANT_BASE = '/assistant';
let assistantOpenSequence = 0;
let assistantLastUrl = '';
let assistantStatusPoller = null;
let assistantScreenshotPoller = null;

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
    const { urlInput, log, screenshot } = assistantEls();
    assistantLastUrl = '';
    if (urlInput) urlInput.value = '';
    if (log) log.replaceChildren();
    if (screenshot) {
        screenshot.removeAttribute('src');
        screenshot.style.display = 'none';
    }
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
    const { screenshot } = assistantEls();
    if (!screenshot) return;
    try {
        const data = await assistantCall('/api/screenshot', { method: 'GET' });
        if (data.running && data.image) {
            screenshot.src = data.image;
            screenshot.style.display = 'block';
        } else {
            screenshot.removeAttribute('src');
            screenshot.style.display = 'none';
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
    const { screenshot } = assistantEls();
    if (!screenshot || !screenshot.naturalWidth) return;
    screenshot.focus();
    const { x, y } = assistantImageToPageCoords(screenshot, event.clientX, event.clientY);
    try {
        await assistantCall('/api/click', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ x, y }),
        });
    } catch (err) {
        assistantLog(`Click failed: ${err.message}`, true);
    }
    assistantRefreshScreenshot();
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
        (data.log || '')
            .split('\n')
            .filter(Boolean)
            .forEach((line) => assistantLog(line));
    } catch (err) {
        assistantLog(`Fill in failed: ${err.message}`, true);
    }
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
    const { header, copyBtn, refreshBtn, fillBtn, panel, screenshot } = assistantEls();
    if (!panel) return;

    header.addEventListener('click', () => panel.classList.toggle('assistant-collapsed'));
    copyBtn.addEventListener('click', assistantCopyLink);
    refreshBtn.addEventListener('click', assistantRefreshStatus);
    fillBtn.addEventListener('click', assistantFillIn);

    if (screenshot) {
        screenshot.addEventListener('click', assistantHandleClick);
        screenshot.addEventListener('keydown', assistantHandleKeydown);
        screenshot.addEventListener('wheel', assistantHandleWheel, { passive: false });
    }

    assistantRefreshStatus();
    startAssistantStatusPolling();
    startAssistantScreenshotPolling();
});
