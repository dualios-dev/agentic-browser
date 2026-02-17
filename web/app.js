/**
 * Agentic Browser Dashboard — Client
 * 
 * Connects via WebSocket for live updates:
 * - Screenshot stream (live browser view)
 * - Agent step progress
 * - Chat messages
 */

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// State
let ws = null;
let isConnected = false;

// Elements
const statusDot = $('#status-dot');
const statusText = $('#status-text');
const screenshot = $('#screenshot');
const screenshotPlaceholder = $('#screenshot-placeholder');
const chatMessages = $('#chat-messages');
const chatInput = $('#chat-input');
const sendBtn = $('#send-btn');
const stopBtn = $('#stop-btn');
const taskSteps = $('#task-steps');
const urlInput = $('#url-input');
const goBtn = $('#go-btn');

// --- WebSocket Connection ---

function connect() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${location.host}/ws`);

    ws.onopen = () => {
        isConnected = true;
        statusDot.className = 'status-dot online';
        statusText.textContent = 'Connected';
        addMessage('system', 'Connected to Agentic Browser');
    };

    ws.onclose = () => {
        isConnected = false;
        statusDot.className = 'status-dot offline';
        statusText.textContent = 'Disconnected';
        // Reconnect after 3s
        setTimeout(connect, 3000);
    };

    ws.onerror = () => {
        statusDot.className = 'status-dot offline';
        statusText.textContent = 'Connection error';
    };

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        handleMessage(msg);
    };
}

// --- Message Handlers ---

function handleMessage(msg) {
    switch (msg.type) {
        case 'connected':
            // Load existing tasks
            if (msg.tasks && msg.tasks.length > 0) {
                msg.tasks.reverse().forEach(renderTaskSummary);
            }
            break;

        case 'screenshot':
            screenshot.src = `data:image/png;base64,${msg.data}`;
            screenshot.classList.add('loaded');
            screenshotPlaceholder.style.display = 'none';
            break;

        case 'step':
            renderStep(msg.data);
            // Update screenshot if step has one
            if (msg.data.screenshot) {
                screenshot.src = `data:image/png;base64,${msg.data.screenshot}`;
                screenshot.classList.add('loaded');
                screenshotPlaceholder.style.display = 'none';
            }
            break;

        case 'task_created':
            addMessage('system', `Task started: ${msg.task.goal}`);
            statusDot.className = 'status-dot working';
            statusText.textContent = 'Working...';
            stopBtn.style.display = 'block';
            taskSteps.innerHTML = '';
            break;

        case 'task_started':
            statusDot.className = 'status-dot working';
            statusText.textContent = 'Agent working...';
            break;

        case 'task_completed':
            const t = msg.task;
            const success = t.status === 'completed';
            statusDot.className = `status-dot ${success ? 'online' : 'offline'}`;
            statusText.textContent = success ? 'Done' : 'Failed';
            stopBtn.style.display = 'none';
            if (t.result) {
                addMessage(
                    success ? 'agent' : 'error',
                    t.result.summary
                );
            }
            break;

        case 'task_failed':
            statusDot.className = 'status-dot offline';
            statusText.textContent = 'Failed';
            stopBtn.style.display = 'none';
            addMessage('error', `Task failed: ${msg.error || 'Unknown error'}`);
            break;

        case 'task_cancelled':
            statusDot.className = 'status-dot online';
            statusText.textContent = 'Cancelled';
            stopBtn.style.display = 'none';
            addMessage('system', 'Task cancelled');
            break;
    }
}

// --- UI Rendering ---

function addMessage(type, text) {
    const div = document.createElement('div');
    div.className = `message ${type}`;
    div.textContent = text;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function renderStep(step) {
    // Remove empty state
    const empty = taskSteps.querySelector('.empty-state');
    if (empty) empty.remove();

    const statusIcons = {
        completed: '✅',
        failed: '❌',
        running: '⏳',
        pending: '⬜',
    };

    const div = document.createElement('div');
    div.className = `step ${step.status}`;
    div.innerHTML = `
        <span class="step-icon">${statusIcons[step.status] || '⬜'}</span>
        <div class="step-content">
            <div class="step-thought">${escapeHtml(step.thought || '...')}</div>
            <div class="step-action">${escapeHtml(step.action)} ${step.action_args ? JSON.stringify(step.action_args).slice(0, 80) : ''}</div>
        </div>
    `;
    taskSteps.appendChild(div);
    taskSteps.scrollTop = taskSteps.scrollHeight;
}

function renderTaskSummary(task) {
    if (task.result && task.result.summary) {
        addMessage('agent', `Previous: ${task.goal} → ${task.result.summary}`);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// --- User Actions ---

function sendTask() {
    const text = chatInput.value.trim();
    if (!text || !isConnected) return;

    addMessage('user', text);
    chatInput.value = '';

    ws.send(JSON.stringify({
        type: 'task',
        goal: text,
    }));
}

function navigateTo() {
    let url = urlInput.value.trim();
    if (!url || !isConnected) return;

    if (!url.startsWith('http')) {
        url = 'https://' + url;
    }

    ws.send(JSON.stringify({
        type: 'navigate',
        url: url,
    }));
    addMessage('system', `Navigating to ${url}`);
}

function stopAgent() {
    if (isConnected) {
        ws.send(JSON.stringify({ type: 'stop' }));
        addMessage('system', 'Stopping agent...');
    }
}

// --- Event Listeners ---

sendBtn.addEventListener('click', sendTask);
chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') sendTask();
});

goBtn.addEventListener('click', navigateTo);
urlInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') navigateTo();
});

stopBtn.addEventListener('click', stopAgent);

// --- Init ---
connect();
