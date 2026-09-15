/* ═══════════════════════════════════════════════════════════════════════════
   FindFast - Application Assistant integration
   Talks to the local autofill server (Apply/app.py) which drives a single,
   real, visible Chrome window. "View Job" opens the link there instead of a
   plain new browser tab, so the user can sign in / click through normally,
   then use "Fill In" to auto-populate whatever application form they land on.
   ═══════════════════════════════════════════════════════════════════════════ */

const ASSISTANT_BASE = 'http://127.0.0.1:5050';

function assistantEls() {
    return {
        panel: document.getElementById('assistantPanel'),
        header: document.getElementById('assistantHeader'),
        urlInput: document.getElementById('assistantUrl'),
        copyBtn: document.getElementById('assistantCopyBtn'),
        refreshBtn: document.getElementById('assistantRefreshBtn'),
        fillBtn: document.getElementById('assistantFillBtn'),
        log: document.getElementById('assistantLog'),
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
    assistantExpand();
    assistantLog(`Opening in assistant browser: ${url}`);
    try {
        const data = await assistantCall('/api/open', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url }),
        });
        assistantEls().urlInput.value = data.url || url;
        assistantLog('Opened. Sign in / navigate to the application form, then click Fill In.');
    } catch (err) {
        assistantLog(
            `Could not reach the assistant browser (is it running? "python3 app.py" in the Apply folder). Opening in a normal tab instead. ${err.message}`,
            true
        );
        window.open(url, '_blank', 'noopener,noreferrer');
    }
}

async function assistantRefreshStatus() {
    try {
        const data = await assistantCall('/api/status', { method: 'GET' });
        assistantEls().urlInput.value = data.running ? (data.url || '') : '';
        if (!data.running) {
            assistantLog('Assistant browser is not open yet - click a job\'s "View Job" button to start.');
        }
    } catch (err) {
        assistantLog(`Assistant server unreachable: ${err.message}`, true);
    }
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
    const { header, copyBtn, refreshBtn, fillBtn, panel } = assistantEls();
    if (!panel) return;

    header.addEventListener('click', () => panel.classList.toggle('assistant-collapsed'));
    copyBtn.addEventListener('click', assistantCopyLink);
    refreshBtn.addEventListener('click', assistantRefreshStatus);
    fillBtn.addEventListener('click', assistantFillIn);

    assistantRefreshStatus();
});
