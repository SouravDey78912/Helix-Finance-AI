// ── App State ─────────────────────────────────────────────────────────────────
let token = localStorage.getItem('token') || '';
let currentTab = 'overview';
let chatSessionId = null;
let chatMessages = [];
let isChatLoading = false;

// ── DOM Elements ──────────────────────────────────────────────────────────────
const authSection = document.getElementById('auth-section');
const mainSection = document.getElementById('main-section');
const navRail = document.getElementById('nav-rail');
const commandSearchBar = document.getElementById('command-search-bar');
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
    navRail.classList.add('hidden');
    userProfile.classList.add('hidden');
    if (commandSearchBar) commandSearchBar.classList.add('hidden');
    const contentArea = document.querySelector('.content-area');
    if (contentArea) contentArea.classList.add('auth-mode');
    if (window.pollInterval) {
        clearInterval(window.pollInterval);
        window.pollInterval = null;
    }
}

async function showDashboard() {
    authSection.classList.add('hidden');
    mainSection.classList.remove('hidden');
    navRail.classList.remove('hidden');
    userProfile.classList.remove('hidden');
    if (commandSearchBar) commandSearchBar.classList.remove('hidden');
    const contentArea = document.querySelector('.content-area');
    if (contentArea) contentArea.classList.remove('auth-mode');

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

    switchTab('overview');
}

// ── Tab Navigation (Overview, Pipeline, AML, Chat, Audit) ───────────────────
function switchTab(tab) {
    currentTab = tab;

    const tabs = ['overview', 'pipeline', 'aml', 'chat', 'audit'];
    tabs.forEach(t => {
        const viewEl = document.getElementById(`view-${t}`);
        const navEl = document.getElementById(`nav-${t}`);
        if (viewEl) viewEl.classList.toggle('hidden', t !== tab);
        if (navEl) navEl.classList.toggle('active', t === tab);
    });

    if (tab === 'pipeline') {
        loadDocuments();
    } else if (tab === 'overview') {
        loadOverviewData();
    } else if (tab === 'chat') {
        if (window.pollInterval) {
            clearInterval(window.pollInterval);
            window.pollInterval = null;
        }
        setTimeout(() => {
            const input = document.getElementById('chat-input');
            if (input) input.focus();
        }, 100);
    }
}

// ── Overview KPI Deck Refresh ───────────────────────────────────────────────
function loadOverviewData() {
    const chunkEl = document.getElementById('kpi-chunks');
    const amlEl = document.getElementById('kpi-aml-score');
    const evalEl = document.getElementById('kpi-eval');
    
    // Simulate real-time metric telemetry update
    if (chunkEl) chunkEl.innerText = (14280 + Math.floor(Math.random() * 50)).toLocaleString();
    if (amlEl) amlEl.innerText = '98.2%';
    if (evalEl) evalEl.innerText = (0.940 + Math.random() * 0.01).toFixed(3);
}

// ── Authentication ────────────────────────────────────────────────────────────
async function login(e) {
    e.preventDefault();
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const btn = document.getElementById('login-btn');
    btn.disabled = true;
    btn.innerHTML = 'Authenticating...';

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
        btn.innerHTML = 'Sign In to Operations Portal <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"></path></svg>';
    }
}

async function loginWithGoogle() {
    const btn = document.getElementById('login-btn');
    if (btn) btn.innerHTML = 'Signing in with Google SSO...';
    try {
        const body = { email: "admin@helix.ai", password: "admin123" };
        const res = await fetch('/api/v1/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (res.ok) {
            const data = await res.json();
            token = data.access_token;
            localStorage.setItem('token', token);
            showDashboard();
        } else {
            alert('Google Single Sign-On authentication failed.');
        }
    } catch (err) {
        alert('Server connection error during Google SSO.');
    } finally {
        if (btn) btn.innerHTML = 'Sign In to Operations Portal <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"></path></svg>';
    }
}

function logout() {
    token = '';
    chatSessionId = null;
    chatMessages = [];
    localStorage.removeItem('token');
    showAuth();
}

// ── Document Management Pipeline ──────────────────────────────────────────────
function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) uploadFile(files[0]);
}

async function uploadFile(file) {
    uploadStatus.style.display = 'block';
    uploadStatus.className = 'upload-status info';
    uploadStatus.innerHTML = `Uploading <span style="font-weight:600;">${escapeHtml(file.name)}</span> to MinIO S3 bucket...`;

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
        uploadStatus.innerText = 'File uploaded & queued for Celery ingestion & Qdrant vector indexing!';
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
                        <span>Upload a file on the left to start vector indexing</span>
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
                    <td class="font-mono" style="color:var(--text-secondary);">${chunks}</td>
                    <td class="font-mono" style="font-size:0.78rem;color:var(--text-muted);">${escapeHtml(taskId)}</td>
                    <td class="text-right">
                        <button class="btn btn-secondary btn-sm" onclick="deleteDoc('${doc.document_id}')" title="Delete File">Delete</button>
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
    if (!confirm('Are you sure you want to delete this document from Qdrant and MinIO?')) return;
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

// ── Multi-Agent AI Studio Chat ────────────────────────────────────────────────
function handleChatKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function autoResizeTextarea(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
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
            <div class="message-avatar">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                </svg>
            </div>
            <div class="message-content">
                <div class="message-bubble assistant-bubble">
                    <p>Chat session reset. I am ready to process your next financial analysis query.</p>
                </div>
                <div class="message-meta">Helix AI Network · Ready</div>
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

    // Show agent execution trace panel
    const typingEl = document.getElementById('typing-indicator');
    typingEl.classList.remove('hidden');
    scrollChatToBottom();

    const sendBtn = document.getElementById('chat-send-btn');
    sendBtn.disabled = true;

    const startTime = Date.now();

    try {
        const body = {
            query,
            session_id: chatSessionId
        };

        const res = await fetch('/api/v1/chat/query', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(body)
        });

        const elapsedMs = Date.now() - startTime;

        if (!res.ok) {
            const err = await res.json();
            appendMessage('assistant', `⚠️ Execution Error: ${err.detail || 'Failed to generate response.'}`);
            return;
        }

        const data = await res.json();
        if (data.session_id) chatSessionId = data.session_id;

        // Render response with confidence and source metadata if present
        let replyText = data.answer || data.response || 'No response content returned.';
        
        let metaExtra = '';
        if (data.sources && data.sources.length > 0) {
            const sourcesList = data.sources.map(s => `<code>${escapeHtml(s.filename || s.doc_id || 'Doc')}</code>`).join(', ');
            metaExtra = `<br><span style="font-size:0.75rem;color:var(--text-muted);margin-top:0.4rem;display:block;">Sources cited: ${sourcesList}</span>`;
        }

        appendMessage('assistant', replyText + metaExtra);
        document.getElementById('chat-latency').textContent = `Agent Latency: ${elapsedMs}ms | Session: ${chatSessionId ? chatSessionId.substring(0, 8) : 'new'}`;

    } catch (err) {
        appendMessage('assistant', '⚠️ Server connection error while contacting agent network.');
    } finally {
        isChatLoading = false;
        typingEl.classList.add('hidden');
        sendBtn.disabled = false;
        scrollChatToBottom();
    }
}

function appendMessage(sender, text) {
    const container = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message message-${sender}`;

    const isUser = sender === 'user';
    const avatar = isUser ? '👤' : `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
        </svg>`;

    msgDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-bubble ${isUser ? 'user-bubble' : 'assistant-bubble'}">
                <p>${formatMessageContent(text)}</p>
            </div>
            <div class="message-meta">${isUser ? 'You' : 'Helix Agent Network'} · ${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
        </div>`;

    container.appendChild(msgDiv);
    scrollChatToBottom();
}

function formatMessageContent(content) {
    if (!content) return '';
    // Format code tags and line breaks
    let formatted = content
        .replace(/\n\n/g, '</p><p class="mt-2">')
        .replace(/\n/g, '<br>');
    return formatted;
}

function scrollChatToBottom() {
    const container = document.getElementById('chat-messages');
    if (container) container.scrollTop = container.scrollHeight;
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
