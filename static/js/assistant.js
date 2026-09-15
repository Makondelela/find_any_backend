/* ═══════════════════════════════════════════════════════════════════════════
   FindFast - Application Assistant integration
   Talks to the local autofill server (Apply/app.py) which drives a single,
   real, visible Chrome window. "View Job" opens the link there instead of a
   plain new browser tab, so the user can sign in / click through normally,
   then use "Fill In" to auto-populate whatever application form they land on.
   ═══════════════════════════════════════════════════════════════════════════ */

const ASSISTANT_BASE = '/assistant';
let assistantOpenSequence = 0;
let assistantLastUrl = '';
let assistantStatusPoller = null;

function assistantEls() {
    return {
        panel: document.getElementById('assistantPanel'),
        header: document.getElementById('assistantHeader'),
        urlInput: document.getElementById('assistantUrl'),
        copyBtn: document.getElementById('assistantCopyBtn'),
        refreshBtn: document.getElementById('assistantRefreshBtn'),
        fillBtn: document.getElementById('assistantFillBtn'),
        webview: document.getElementById('assistantWebview'),
        screenButton: document.getElementById('assistantScreenButton'),
        screen: document.getElementById('assistantScreen'),
        typeInput: document.getElementById('assistantTypeInput'),
        typeBtn: document.getElementById('assistantTypeBtn'),
        backBtn: document.getElementById('assistantBackBtn'),
        forwardBtn: document.getElementById('assistantForwardBtn'),
        reloadBtn: document.getElementById('assistantReloadBtn'),
        log: document.getElementById('assistantLog'),
    };
}

function assistantShowScreen(data) {
    const { screen, webview } = assistantEls();
    if (!screen || !webview || !data.image) return;
    screen.src = `data:image/jpeg;base64,${data.image}`;
    webview.hidden = false;
    if (data.url) {
        assistantLastUrl = data.url;
        assistantEls().urlInput.value = data.url;
    }
}

async function assistantScreenshot() {
    const data = await assistantCall('/api/screenshot', { method: 'GET' });
    assistantShowScreen(data);
}

async function assistantBrowserAction(endpoint, body = {}) {
    try {
        const data = await assistantCall(`/api/${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        assistantShowScreen(data);
    } catch (err) {
        assistantLog(`${endpoint} failed: ${err.message}`, true);
    }
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
    const { urlInput, log, screen, webview } = assistantEls();
    assistantLastUrl = '';
    if (urlInput) urlInput.value = '';
    if (log) log.replaceChildren();
    if (screen) screen.removeAttribute('src');
    if (webview) webview.hidden = true;
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
        await assistantScreenshot();
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
        if (data.running && changed) {
            await assistantScreenshot();
        }
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

async function assistantFillIn() {
    assistantLog('Filling in the current page...');
    try {
        const data = await assistantCall('/api/fill', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}),
        });
        assistantEls().urlInput.value = data.url || '';
        await assistantScreenshot();
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
    const { header, copyBtn, refreshBtn, fillBtn, panel, screenButton, typeInput, typeBtn, backBtn, forwardBtn, reloadBtn } = assistantEls();
    if (!panel) return;

    header.addEventListener('click', () => panel.classList.toggle('assistant-collapsed'));
    copyBtn.addEventListener('click', assistantCopyLink);
    refreshBtn.addEventListener('click', assistantRefreshStatus);
    fillBtn.addEventListener('click', assistantFillIn);
    screenButton.addEventListener('click', (event) => {
        const rect = event.currentTarget.getBoundingClientRect();
        const image = assistantEls().screen;
        const scaleX = image.naturalWidth / image.clientWidth;
        const scaleY = image.naturalHeight / image.clientHeight;
        assistantBrowserAction('tap', {
            x: (event.clientX - rect.left) * scaleX,
            y: (event.clientY - rect.top) * scaleY,
        });
    });
    typeBtn.addEventListener('click', () => {
        if (!typeInput.value) return;
        assistantBrowserAction('type', { text: typeInput.value });
        typeInput.value = '';
    });
    backBtn.addEventListener('click', () => assistantBrowserAction('back'));
    forwardBtn.addEventListener('click', () => assistantBrowserAction('forward'));
    reloadBtn.addEventListener('click', () => assistantBrowserAction('reload'));

    assistantRefreshStatus();
    startAssistantStatusPolling();
});
