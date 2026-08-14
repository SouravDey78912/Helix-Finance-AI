// App State
let token = localStorage.getItem('token') || '';

// DOM Elements
const authSection = document.getElementById('auth-section');
const mainSection = document.getElementById('main-section');
const userProfile = document.getElementById('user-profile');
const userEmailSpan = document.getElementById('user-email');
const dropZone = document.getElementById('drop-zone');
const uploadStatus = document.getElementById('upload-status');
const documentsTbody = document.getElementById('documents-tbody');

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
    if (token) {
        showDashboard();
    } else {
        showAuth();
    }

    // Drag and Drop event listeners
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
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) {
                uploadFile(files[0]);
            }
        });
    }
});

// UI Views
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
        const response = await fetch('/api/v1/auth/me', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.status === 401) {
            logout();
            return;
        }
        
        const data = await response.json();
        if (data && data.email) {
            userEmailSpan.innerText = data.email;
        }
    } catch (err) {
        console.error('Error fetching user info:', err);
    }

    loadDocuments();
    
    // Polling every 3 seconds for document status updates
    if (window.pollInterval) clearInterval(window.pollInterval);
    window.pollInterval = setInterval(loadDocuments, 3000);
}

// Authentication
async function login(e) {
    e.preventDefault();
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    try {
        const response = await fetch('/api/v1/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        
        if (!response.ok) {
            const err = await response.json();
            alert(err.detail || 'Authentication failed. Please verify credentials.');
            return;
        }
        
        const data = await response.json();
        token = data.access_token;
        localStorage.setItem('token', token);
        showDashboard();
    } catch (err) {
        alert('Server connection error. Please try again.');
    }
}

function logout() {
    token = '';
    localStorage.removeItem('token');
    showAuth();
}

// Document Management
function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        uploadFile(files[0]);
    }
}

async function uploadFile(file) {
    uploadStatus.style.display = 'block';
    uploadStatus.className = 'upload-status info';
    uploadStatus.innerHTML = `Uploading <span style="font-weight:600;">${escapeHtml(file.name)}</span>...`;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/v1/documents/upload', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });
        
        if (!response.ok) {
            const err = await response.json();
            uploadStatus.className = 'upload-status error';
            uploadStatus.innerText = `Upload failed: ${err.detail || 'Unknown error'}`;
            return;
        }
        
        uploadStatus.className = 'upload-status success';
        uploadStatus.innerText = 'File successfully uploaded & queued for ingestion!';
        loadDocuments();
        
        // Hide upload status after 5 seconds
        setTimeout(() => {
            uploadStatus.style.display = 'none';
        }, 5000);
    } catch (err) {
        uploadStatus.className = 'upload-status error';
        uploadStatus.innerText = 'Upload failed: server connection issue';
    }
}

async function loadDocuments() {
    if (!token) return;
    try {
        const response = await fetch('/api/v1/documents?page=1&page_size=50', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) return;
        
        const data = await response.json();
        
        if (!data.documents || data.documents.length === 0) {
            documentsTbody.innerHTML = `
                <tr>
                    <td colspan="6" class="table-empty">
                        <div class="empty-state">
                            <svg class="empty-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"></path></svg>
                            <p>No documents in ingestion pipeline</p>
                            <span>Upload a file on the left to start analysis</span>
                        </div>
                    </td>
                </tr>`;
            return;
        }
        
        documentsTbody.innerHTML = data.documents.map(doc => {
            const sizeKB = (doc.size_bytes / 1024).toFixed(1) + ' KB';
            const chunks = doc.chunk_count !== null ? doc.chunk_count : '—';
            const taskId = doc.metadata && doc.metadata.object_name ? doc.metadata.object_name.split('.')[0] : '—';
            
            return `
                <tr>
                    <td style="font-weight: 600; color: var(--text-primary);">${escapeHtml(doc.filename)}</td>
                    <td style="color: var(--text-secondary);">${sizeKB}</td>
                    <td><span class="badge badge-${doc.status}">${doc.status}</span></td>
                    <td style="font-family: var(--font-mono); color: var(--text-secondary);">${chunks}</td>
                    <td style="font-family: var(--font-mono); font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(taskId)}</td>
                    <td class="text-right">
                        <button class="btn btn-secondary btn-sm btn-danger-hover" onclick="deleteDoc('${doc.document_id}')" title="Delete file">
                            Delete
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        console.error('Error fetching documents:', err);
    }
}

async function deleteDoc(docId) {
    if (!confirm('Are you sure you want to delete this document from the pipeline?')) return;
    try {
        const response = await fetch(`/api/v1/documents/${docId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
            loadDocuments();
        } else {
            alert('Failed to delete document. Please try again.');
        }
    } catch (err) {
        alert('Server connection error. Please try again.');
    }
}

// Helpers
function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
