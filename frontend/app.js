// ── App State ─────────────────────────────────────────────────────────────────
let token = localStorage.getItem('token') || '';
let currentTab = 'pipeline';
let chatSessionId = null;
let chatMessages = [];
let isChatLoading = false;

// ── DOM Elements ──────────────────────────────────────────────────────────────
const authSection = document.getElementById('auth-section');
const mainSection = document.getElementById('main-section');
const userProfile = document.getElementById('user-profile');
const userEmailSpan = document.getElementById('user-email');
const dropZone = document.getElementById('drop-zone');
const uploadStatus = document.getElementById('upload-status');
const documentsTbody = document.getElementById('documents-tbody');

// ── Initialize App ────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    if (token) {
        showDashboard();
    } else {
        showAuth();
    }

    if (dropZone) {
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropZone.classList.add('dragover');
            }, false);
        });
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropZone.classList.remove('dragover');
            }, false);
        });
        dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) uploadFile(files[0]);
        });
    }
});

// ── UI Views ──────────────────────────────────────────────────────────────────
function showAuth() {
    authSection.classList.remove('hidden');
    mainSection.classList.add('hidden');
    userProfile.classList.add('hidden');
    if (window.pollInterval) {
        clearInterval(window.pollInterval);
        window.pollInterval = null;
    }
}

async function showDashboard() {
    authSection.classList.add('hidden');
    mainSection.classList.remove('hidden');
    userProfile.classList.remove('hidden');

    try {
        const res = await fetch('/api/v1/auth/me', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.status === 401) { logout(); return; }
        const data = await res.json();
        if (data && data.email) userEmailSpan.innerText = data.email;
    } catch (err) {
        console.error('Error fetching user info:', err);
    }

    loadDocuments();
}

// ── Tab Switching ─────────────────────────────────────────────────────────────
function switchTab(tab) {
    currentTab = tab;

    document.getElementById('view-pipeline').classList.toggle('hidden', tab !== 'pipeline');
    document.getElementById('view-chat').classList.toggle('hidden', tab !== 'chat');
    document.getElementById('tab-pipeline').classList.toggle('active', tab === 'pipeline');
    document.getElementById('tab-chat').classList.toggle('active', tab === 'chat');

    if (tab === 'chat') {
        // Stop polling when in chat view
        if (window.pollInterval) {
            clearInterval(window.pollInterval);
            window.pollInterval = null;
        }
        setTimeout(() => {
            const input = document.getElementById('chat-input');
            if (input) input.focus();
        }, 100);
    } else {
        loadDocuments();
    }
}

// ── Authentication ────────────────────────────────────────────────────────────
async function login(e) {
    e.preventDefault();
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const btn = document.getElementById('login-btn');
    btn.disabled = true;
    btn.innerHTML = 'Signing in...';

    try {
        const res = await fetch('/api/v1/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        if (!res.ok) {
            const err = await res.json();
            alert(err.detail || 'Authentication failed. Please verify credentials.');
            return;
        }
        const data = await res.json();
        token = data.access_token;
        localStorage.setItem('token', token);
        showDashboard();
    } catch (err) {
        alert('Server connection error. Please try again.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Sign In <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"></path></svg>';
    }
}

function logout() {
    token = '';
    chatSessionId = null;
    chatMessages = [];
    localStorage.removeItem('token');
    showAuth();
}

// ── Document Management ───────────────────────────────────────────────────────
function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) uploadFile(files[0]);
}

async function uploadFile(file) {
    uploadStatus.style.display = 'block';
    uploadStatus.className = 'upload-status info';
    uploadStatus.innerHTML = `Uploading <span style="font-weight:600;">${escapeHtml(file.name)}</span>...`;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch('/api/v1/documents/upload', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });
        if (!res.ok) {
            const err = await res.json();
            uploadStatus.className = 'upload-status error';
            uploadStatus.innerText = `Upload failed: ${err.detail || 'Unknown error'}`;
            return;
        }
        uploadStatus.className = 'upload-status success';
        uploadStatus.innerText = 'File successfully uploaded & queued for ingestion!';
        loadDocuments();
        setTimeout(() => { uploadStatus.style.display = 'none'; }, 5000);
    } catch (err) {
        uploadStatus.className = 'upload-status error';
        uploadStatus.innerText = 'Upload failed: server connection issue';
    }
}

async function loadDocuments() {
    if (!token) return;
    try {
        const res = await fetch('/api/v1/documents?page=1&page_size=50', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) return;
        const data = await res.json();

        if (!data.documents || data.documents.length === 0) {
            documentsTbody.innerHTML = `
                <tr><td colspan="6" class="table-empty">
                    <div class="empty-state">
                        <svg class="empty-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"></path></svg>
                        <p>No documents in ingestion pipeline</p>
                        <span>Upload a file on the left to start analysis</span>
                    </div>
                </td></tr>`;
            if (window.pollInterval) { clearInterval(window.pollInterval); window.pollInterval = null; }
            return;
        }

        documentsTbody.innerHTML = data.documents.map(doc => {
            const sizeKB = (doc.size_bytes / 1024).toFixed(1) + ' KB';
            const chunks = doc.chunk_count !== null ? doc.chunk_count : '—';
            const taskId = doc.metadata && doc.metadata.object_name ? doc.metadata.object_name.split('.')[0] : '—';
            return `
                <tr>
                    <td style="font-weight:600;color:var(--text-primary);">${escapeHtml(doc.filename)}</td>
                    <td style="color:var(--text-secondary);">${sizeKB}</td>
                    <td><span class="badge badge-${doc.status}">${doc.status}</span></td>
                    <td style="font-family:var(--font-mono);color:var(--text-secondary);">${chunks}</td>
                    <td style="font-family:var(--font-mono);font-size:0.8rem;color:var(--text-muted);">${escapeHtml(taskId)}</td>
                    <td class="text-right">
                        <button class="btn btn-secondary btn-sm btn-danger-hover" onclick="deleteDoc('${doc.document_id}')" title="Delete">Delete</button>
                    </td>
                </tr>`;
        }).join('');

        const hasActiveTasks = data.documents.some(d => d.status === 'pending' || d.status === 'processing');
        if (hasActiveTasks && currentTab === 'pipeline') {
            if (!window.pollInterval) window.pollInterval = setInterval(loadDocuments, 3000);
        } else {
            if (window.pollInterval) { clearInterval(window.pollInterval); window.pollInterval = null; }
        }
    } catch (err) {
        console.error('Error fetching documents:', err);
    }
}

async function deleteDoc(docId) {
    if (!confirm('Are you sure you want to delete this document?')) return;
    try {
        const res = await fetch(`/api/v1/documents/${docId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) loadDocuments();
        else alert('Failed to delete document.');
    } catch (err) {
        alert('Server connection error.');
    }
}

// ── Chat Functions ────────────────────────────────────────────────────────────

function handleChatKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function autoResizeTextarea(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 150) + 'px';
}

function setQuickPrompt(text) {
    const input = document.getElementById('chat-input');
    input.value = text;
    autoResizeTextarea(input);
    input.focus();
}

function clearChat() {
    chatSessionId = null;
    chatMessages = [];
    const messagesEl = document.getElementById('chat-messages');
    messagesEl.innerHTML = `
        <div class="message message-assistant" id="chat-welcome">
            <div class="message-avatar">🏦</div>
            <div class="message-content">
                <div class="message-bubble assistant-bubble">
                    <p>Chat cleared. How can I help you with your financial documents?</p>
                </div>
                <div class="message-meta">Helix AI · just now</div>
            </div>
        </div>`;
    document.getElementById('chat-latency').textContent = '';
}

async function sendMessage() {
    if (isChatLoading) return;
    const input = document.getElementById('chat-input');
    const query = input.value.trim();
    if (!query) return;

    input.value = '';
    autoResizeTextarea(input);

    // Append user message
    appendMessage('user', query);
    isChatLoading = true;

    // Show typing indicator
    const typingEl = document.getElementById('typing-indicator');
    typingEl.classList.remove('hidden');
    scrollChatToBottom();

    const sendBtn = document.getElementById('chat-send-btn');
    sendBtn.disabled = true;

    try {
        const body = {
            query,
            session_id: chatSessionId,
        };

        const res = await fetch('/api/v1/chat/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify(body),
        });

        typingEl.classList.add('hidden');

        if (!res.ok) {
            const err = await res.json();
            appendErrorMessage(`Error ${res.status}: ${err.detail || 'Query failed'}`);
            return;
        }

        const data = await res.json();
        chatSessionId = data.session_id;

        // Show latency
        if (data.latency_ms) {
            document.getElementById('chat-latency').textContent = `${data.latency_ms}ms`;
        }

        appendAssistantMessage(data.answer, data.sources || [], data.latency_ms);
    } catch (err) {
        typingEl.classList.add('hidden');
        appendErrorMessage('Network error. Please check your connection and try again.');
    } finally {
        isChatLoading = false;
        sendBtn.disabled = false;
        input.focus();
    }
}

function appendMessage(role, text) {
    const messagesEl = document.getElementById('chat-messages');
    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const div = document.createElement('div');
    div.className = `message message-${role}`;
    div.innerHTML = `
        <div class="message-avatar">${role === 'user' ? '👤' : '🏦'}</div>
        <div class="message-content">
            <div class="message-bubble ${role === 'user' ? 'user-bubble' : 'assistant-bubble'}">
                ${escapeHtml(text).replace(/\n/g, '<br>')}
            </div>
            <div class="message-meta">${role === 'user' ? 'You' : 'Helix AI'} · ${now}</div>
        </div>`;
    messagesEl.appendChild(div);
    scrollChatToBottom();
}

function appendAssistantMessage(answer, sources, latencyMs) {
    const messagesEl = document.getElementById('chat-messages');
    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // Format answer: convert **bold** to <strong>, [Source N] to badges
    let formattedAnswer = escapeHtml(answer)
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\[Source (\d+)\]/g, '<span style="display:inline-flex;align-items:center;gap:2px;background:rgba(99,102,241,0.15);color:#a5b4fc;font-size:0.75rem;font-weight:700;padding:0.05rem 0.4rem;border-radius:4px;border:1px solid rgba(99,102,241,0.2)">📄 Source $1</span>');

    // Sources HTML
    let sourcesHtml = '';
    if (sources && sources.length > 0) {
        const sourceCards = sources.map((src, i) => `
            <div class="source-card" onclick="this.classList.toggle('source-card-expanded')">
                <div class="source-card-header">
                    <span class="source-card-title">📄 [Source ${i + 1}] ${escapeHtml(src.title || 'Unknown')}</span>
                    <span class="source-card-score">${(src.score * 100).toFixed(1)}%</span>
                </div>
                <div class="source-card-text">${escapeHtml(src.chunk_text || '')}</div>
            </div>`).join('');
        sourcesHtml = `
            <div class="sources-section">
                <p class="sources-title">📚 Sources (${sources.length})</p>
                <div class="source-cards">${sourceCards}</div>
            </div>`;
    }

    const div = document.createElement('div');
    div.className = 'message message-assistant';
    div.innerHTML = `
        <div class="message-avatar">🏦</div>
        <div class="message-content" style="max-width:85%;">
            <div class="message-bubble assistant-bubble">
                <div>${formattedAnswer}</div>
                ${sourcesHtml}
            </div>
            <div class="message-meta">Helix AI · ${now}${latencyMs ? ' · ' + latencyMs + 'ms' : ''}</div>
        </div>`;
    messagesEl.appendChild(div);
    scrollChatToBottom();
}

function appendErrorMessage(text) {
    const messagesEl = document.getElementById('chat-messages');
    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const div = document.createElement('div');
    div.className = 'message message-assistant';
    div.innerHTML = `
        <div class="message-avatar">🏦</div>
        <div class="message-content">
            <div class="message-bubble error-bubble">⚠️ ${escapeHtml(text)}</div>
            <div class="message-meta">Helix AI · ${now}</div>
        </div>`;
    document.getElementById('chat-messages').appendChild(div);
    scrollChatToBottom();
}

function scrollChatToBottom() {
    const el = document.getElementById('chat-messages');
    if (el) el.scrollTop = el.scrollHeight;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
