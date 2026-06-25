// Global App State
let activeTab = 'dashboard';
let clientsList = [];
let principalsList = [];
let activeInquiryIdForComments = null;
let pipelineChart = null;

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();
    switchTab('dashboard');
    loadDropdownAutocompletes();
});

// Toast notification helper
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let icon = 'info';
    if (type === 'success') icon = 'check-circle';
    if (type === 'error') icon = 'alert-triangle';
    if (type === 'warning') icon = 'alert-circle';
    
    toast.innerHTML = `
        <i data-lucide="${icon}"></i>
        <span>${message}</span>
    `;
    container.appendChild(toast);
    lucide.createIcons();
    
    // Auto-remove after 4 seconds
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.2s reverse forwards';
        setTimeout(() => toast.remove(), 200);
    }, 4000);
}

// Format Currency
function formatMoney(value) {
    if (value === null || value === undefined) return '$0.00';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
}

// Navigation Tab Switcher
function switchTab(tabId) {
    activeTab = tabId;
    
    // Update sidebar navigation active state
    document.querySelectorAll('.menu-item').forEach(item => {
        item.classList.remove('active');
    });
    const activeNav = document.getElementById(`nav-${tabId}`);
    if (activeNav) activeNav.classList.add('active');
    
    // Toggle main content panels
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.remove('active');
    });
    document.getElementById(`tab-${tabId}`).classList.add('active');
    
    // Load data specific to tab
    if (tabId === 'dashboard') {
        loadDashboardData();
    } else if (tabId === 'inquiries') {
        loadInquiries();
    } else if (tabId === 'orders') {
        loadOrders();
    } else if (tabId === 'logs') {
        loadActivityLogs();
    } else if (tabId === 'trash') {
        loadTrash();
    }
}

// Fetch Master lists for dropdown datalist autocomplete
async function loadDropdownAutocompletes() {
    try {
        const clientsRes = await fetch('/api/clients');
        clientsList = await clientsRes.json();
        const clientsDatalist = document.getElementById('client-list-dl');
        clientsDatalist.innerHTML = clientsList.map(c => `<option value="${c.name}">`).join('');

        const principalsRes = await fetch('/api/principals');
        principalsList = await principalsRes.json();
        const principalsDatalist = document.getElementById('principal-list-dl');
        principalsDatalist.innerHTML = principalsList.map(p => `<option value="${p.name}">`).join('');
    } catch (e) {
        console.error('Failed to load autocompletes:', e);
    }
}

// --- DASHBOARD CONTROLLER ---
async function loadDashboardData() {
    try {
        const res = await fetch('/api/dashboard');
        if (!res.ok) throw new Error('Dashboard stats fetch failed');
        const data = await res.json();
        
        // Update header values
        document.getElementById('header-active-val').innerText = formatMoney(data.total_value_active);
        document.getElementById('header-won-val').innerText = formatMoney(data.total_value_won);
        
        // Update stats cards
        document.getElementById('stats-active').innerText = data.active_inquiries;
        document.getElementById('stats-active-val').innerText = `${formatMoney(data.total_value_active)} Active`;
        
        document.getElementById('stats-won').innerText = data.won_inquiries;
        document.getElementById('stats-won-val').innerText = `${formatMoney(data.total_value_won)} Contracts`;
        
        document.getElementById('stats-lost').innerText = data.lost_inquiries;
        document.getElementById('stats-declined').innerText = data.declined_inquiries;

        // Render chart
        renderPipelineChart(data);
        
        // Populate alerts list: Inquiries Due
        const inqAlertsList = document.getElementById('alerts-due-week');
        if (data.due_this_week_alerts.length === 0) {
            inqAlertsList.innerHTML = '<div class="empty-alert">No urgent inquiries due this week.</div>';
        } else {
            inqAlertsList.innerHTML = data.due_this_week_alerts.map(inq => `
                <div class="alert-box">
                    <div class="alert-box-info">
                        <span class="alert-title">${inq.client?.name} &rarr; ${inq.principal?.name}</span>
                        <span class="alert-desc">Ref: ${inq.inquiry_reference || 'N/A'} | Due: <strong>${inq.due_date}</strong></span>
                    </div>
                    <button class="alert-action-btn" onclick="viewInquiryDetail(${inq.id})">Inspect</button>
                </div>
            `).join('');
        }

        // Populate alerts list: Delivery Near
        const delAlertsList = document.getElementById('alerts-delivery');
        if (data.near_delivery_alerts.length === 0) {
            delAlertsList.innerHTML = '<div class="empty-alert">No orders close to delivery deadlines.</div>';
        } else {
            delAlertsList.innerHTML = data.near_delivery_alerts.map(inq => `
                <div class="alert-box" style="border-color: rgba(16, 185, 129, 0.3); background-color: rgba(16, 185, 129, 0.05);">
                    <div class="alert-box-info">
                        <span class="alert-title" style="color: #34d399">${inq.client?.name} / Order ${inq.order?.order_number || 'N/A'}</span>
                        <span class="alert-desc">Principal: ${inq.principal?.name} | Delivery: <strong>${inq.order?.expected_delivery_date || 'N/A'}</strong></span>
                    </div>
                    <button class="alert-action-btn" onclick="viewInquiryDetail(${inq.id})">Inspect</button>
                </div>
            `).join('');
        }
    } catch (e) {
        showToast('Error loading dashboard stats', 'error');
    }
}

function renderPipelineChart(stats) {
    const ctx = document.getElementById('pipelineChart').getContext('2d');
    
    if (pipelineChart) {
        pipelineChart.destroy();
    }
    
    pipelineChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Active', 'Won', 'Lost', 'Declined'],
            datasets: [{
                data: [stats.active_inquiries, stats.won_inquiries, stats.lost_inquiries, stats.declined_inquiries],
                backgroundColor: ['#3b82f6', '#10b981', '#ef4444', '#64748b'],
                borderWidth: 1,
                borderColor: '#1e293b'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#f8fafc', font: { family: 'Outfit', size: 12 } }
                }
            }
        }
    });
}

// --- INQUIRIES CONTROLLER ---
async function loadInquiries() {
    try {
        const statusFilter = document.getElementById('inquiry-filter-status').value;
        const clientFilter = document.getElementById('inquiry-filter-client').value;
        const principalFilter = document.getElementById('inquiry-filter-principal').value;
        
        let url = '/api/inquiries?';
        if (statusFilter) url += `status=${statusFilter}&`;
        
        const res = await fetch(url);
        let inquiries = await res.json();
        
        // Populate Client & Principal Filter Options on first load or status refresh
        populateFilters(inquiries);

        // Apply Client & Principal filters in JS
        if (clientFilter) {
            inquiries = inquiries.filter(i => i.client?.name === clientFilter);
        }
        if (principalFilter) {
            inquiries = inquiries.filter(i => i.principal?.name === principalFilter);
        }
        
        const inquiriesList = document.getElementById('inquiries-list');
        if (inquiries.length === 0) {
            inquiriesList.innerHTML = `<tr><td colspan="8" class="empty-alert">No matching inquiries found in the pipeline.</td></tr>`;
            return;
        }

        inquiriesList.innerHTML = inquiries.map(inq => `
            <tr>
                <td>${inq.inquiry_date || '-'}</td>
                <td>
                    <div style="font-weight:600">${inq.client?.name || '-'}</div>
                    <div style="color:var(--text-muted); font-size:0.75rem">${inq.principal?.name || '-'}</div>
                </td>
                <td title="${inq.inquiry_reference}">${inq.inquiry_reference ? inq.inquiry_reference.substring(0, 45) + (inq.inquiry_reference.length > 45 ? '...' : '') : '-'}</td>
                <td>${inq.quotation_reference || '-'}</td>
                <td style="font-weight:600">${formatMoney(inq.value)}</td>
                <td><span class="status-badge status-${inq.status.toLowerCase()}">${inq.status}</span></td>
                <td>${inq.due_date ? `<strong>${inq.due_date}</strong>` : '-'}</td>
                <td>
                    <div style="display:flex; gap:0.5rem">
                        <button class="btn btn-secondary btn-sm" onclick="viewInquiryDetail(${inq.id})">Details</button>
                        <button class="btn btn-primary btn-sm" onclick="openEditInquiryModal(${inq.id})">Edit</button>
                        <button class="btn btn-danger btn-sm" onclick="softDeleteInquiry(${inq.id})">Delete</button>
                        
                        <!-- Status Transitions Dropdown or Quick Trigger -->
                        ${inq.status === 'Active' ? `
                            <button class="btn btn-success btn-sm" onclick="triggerTransition(${inq.id}, 'Won')">Won</button>
                            <button class="btn btn-danger btn-sm" style="background:#ef4444" onclick="triggerTransition(${inq.id}, 'Lost')">Lost</button>
                            <button class="btn btn-secondary btn-sm" onclick="triggerTransition(${inq.id}, 'Declined')">Declined</button>
                        ` : `
                            <button class="btn btn-secondary btn-sm" onclick="triggerTransition(${inq.id}, 'Active')">Reset Active</button>
                        `}
                    </div>
                </td>
            </tr>
        `).join('');
    } catch (e) {
        showToast('Error loading inquiries list', 'error');
    }
}

function populateFilters(data) {
    const clientSelect = document.getElementById('inquiry-filter-client');
    const principalSelect = document.getElementById('inquiry-filter-principal');
    
    // Save selected values
    const currentClient = clientSelect.value;
    const currentPrincipal = principalSelect.value;

    const clients = [...new Set(data.map(i => i.client?.name).filter(Boolean))].sort();
    const principals = [...new Set(data.map(i => i.principal?.name).filter(Boolean))].sort();

    clientSelect.innerHTML = '<option value="">All Clients</option>' + 
        clients.map(c => `<option value="${c}">${c}</option>`).join('');
    principalSelect.innerHTML = '<option value="">All Principals</option>' + 
        principals.map(p => `<option value="${p}">${p}</option>`).join('');

    // Restore selected values if still valid
    if (clients.includes(currentClient)) clientSelect.value = currentClient;
    if (principals.includes(currentPrincipal)) principalSelect.value = currentPrincipal;
}

// Global search handling
async function onGlobalSearch(query) {
    if (query.trim().length === 0) {
        if (activeTab === 'inquiries') loadInquiries();
        if (activeTab === 'orders') loadOrders();
        return;
    }
    
    try {
        const res = await fetch(`/api/inquiries?search=${encodeURIComponent(query)}`);
        const searchResults = await res.json();
        
        if (activeTab === 'inquiries') {
            const list = document.getElementById('inquiries-list');
            if (searchResults.length === 0) {
                list.innerHTML = `<tr><td colspan="8" class="empty-alert">No search results matching your query.</td></tr>`;
                return;
            }
            list.innerHTML = searchResults.map(inq => `
                <tr>
                    <td>${inq.inquiry_date || '-'}</td>
                    <td>
                        <div style="font-weight:600">${inq.client?.name || '-'}</div>
                        <div style="color:var(--text-muted); font-size:0.75rem">${inq.principal?.name || '-'}</div>
                    </td>
                    <td title="${inq.inquiry_reference}">${inq.inquiry_reference ? inq.inquiry_reference.substring(0, 45) + (inq.inquiry_reference.length > 45 ? '...' : '') : '-'}</td>
                    <td>${inq.quotation_reference || '-'}</td>
                    <td style="font-weight:600">${formatMoney(inq.value)}</td>
                    <td><span class="status-badge status-${inq.status.toLowerCase()}">${inq.status}</span></td>
                    <td>${inq.due_date || '-'}</td>
                    <td>
                        <div style="display:flex; gap:0.5rem">
                            <button class="btn btn-secondary btn-sm" onclick="viewInquiryDetail(${inq.id})">Details</button>
                            <button class="btn btn-primary btn-sm" onclick="openEditInquiryModal(${inq.id})">Edit</button>
                            <button class="btn btn-danger btn-sm" onclick="softDeleteInquiry(${inq.id})">Delete</button>
                        </div>
                    </td>
                </tr>
            `).join('');
        } else if (activeTab === 'orders') {
            const orders = searchResults.filter(inq => inq.status === 'Won' && inq.order);
            const list = document.getElementById('orders-list');
            if (orders.length === 0) {
                list.innerHTML = `<tr><td colspan="8" class="empty-alert">No won orders found matching search criteria.</td></tr>`;
                return;
            }
            list.innerHTML = orders.map(inq => {
                const o = inq.order;
                return `
                    <tr>
                        <td>${o.order_date || '-'}</td>
                        <td><strong>${o.order_number || '-'}</strong></td>
                        <td>
                            <div style="font-weight:600">${inq.client?.name || '-'}</div>
                            <div style="color:var(--text-muted); font-size:0.75rem">${inq.principal?.name || '-'}</div>
                        </td>
                        <td>${o.expected_delivery_date || '-'}</td>
                        <td style="font-weight:600">${formatMoney(o.total_order_value)}</td>
                        <td>${o.team_commission || '-'}</td>
                        <td><span class="status-badge status-won">${o.payment_status || 'CAD'}</span></td>
                        <td>
                            <button class="btn btn-secondary btn-sm" onclick="viewInquiryDetail(${inq.id})">Full Spec</button>
                            <button class="btn btn-primary btn-sm" onclick="openEditInquiryModal(${inq.id})">Edit</button>
                        </td>
                    </tr>
                `;
            }).join('');
        }
    } catch (e) {
        showToast('Search query execution failed', 'error');
    }
}

// --- WON ORDERS CONTROLLER ---
async function loadOrders() {
    try {
        const sheetFilter = document.getElementById('order-filter-sheet').value;
        const res = await fetch('/api/inquiries?status=Won');
        let wonInquiries = await res.json();
        
        // Filter orders based on sheet
        if (sheetFilter) {
            wonInquiries = wonInquiries.filter(inq => inq.order?.source_sheet === sheetFilter);
        }

        const ordersList = document.getElementById('orders-list');
        if (wonInquiries.length === 0) {
            ordersList.innerHTML = `<tr><td colspan="8" class="empty-alert">No won orders recorded under this sheet.</td></tr>`;
            return;
        }

        ordersList.innerHTML = wonInquiries.map(inq => {
            const o = inq.order || {};
            return `
                <tr>
                    <td>${o.order_date || '-'}</td>
                    <td><strong>${o.order_number || '-'}</strong></td>
                    <td>
                        <div style="font-weight:600">${inq.client?.name || '-'}</div>
                        <div style="color:var(--text-muted); font-size:0.75rem">${inq.principal?.name || '-'}</div>
                    </td>
                    <td>${o.expected_delivery_date ? `<strong>${o.expected_delivery_date}</strong>` : '-'}</td>
                    <td style="font-weight:600">${formatMoney(o.total_order_value)}</td>
                    <td>${o.team_commission || '-'}</td>
                    <td><span class="status-badge status-won">${o.payment_status || 'CAD'}</span></td>
                    <td>
                        <div style="display:flex; gap:0.5rem">
                            <button class="btn btn-secondary btn-sm" onclick="viewInquiryDetail(${inq.id})">Full Spec</button>
                            <button class="btn btn-primary btn-sm" onclick="openEditInquiryModal(${inq.id})">Edit</button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (e) {
        showToast('Error loading orders', 'error');
    }
}

// --- ACTIVITY AUDIT LOG CONTROLLER ---
async function loadActivityLogs() {
    try {
        const res = await fetch('/api/activity-logs');
        const logs = await res.json();
        
        const timeline = document.getElementById('activity-timeline');
        if (logs.length === 0) {
            timeline.innerHTML = '<div class="empty-alert">No system logs recorded yet.</div>';
            return;
        }

        timeline.innerHTML = logs.map(log => {
            const dt = new Date(log.timestamp).toLocaleString();
            return `
                <div class="timeline-item">
                    <div class="timeline-dot"></div>
                    <div class="timeline-content">
                        <div class="timeline-time">${dt}</div>
                        <div>Inquiry #${log.inquiry_id} &rarr; <strong>${log.action}</strong></div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (e) {
        showToast('Error fetching activity logs', 'error');
    }
}

// --- TRASH BIN CONTROLLER (Soft delete recovery) ---
async function loadTrash() {
    try {
        const res = await fetch('/api/inquiries?show_deleted=true');
        const deleted = await res.json();
        
        const trashList = document.getElementById('trash-list');
        if (deleted.length === 0) {
            trashList.innerHTML = `<tr><td colspan="6" class="empty-alert">Trash bin is empty.</td></tr>`;
            return;
        }

        trashList.innerHTML = deleted.map(inq => `
            <tr>
                <td>${inq.inquiry_date || '-'}</td>
                <td>
                    <div style="font-weight:600">${inq.client?.name || '-'}</div>
                    <div style="color:var(--text-muted); font-size:0.75rem">${inq.principal?.name || '-'}</div>
                </td>
                <td>${inq.inquiry_reference || '-'}</td>
                <td>${inq.quotation_reference || '-'}</td>
                <td>${formatMoney(inq.value)}</td>
                <td>
                    <button class="btn btn-success btn-sm" onclick="restoreInquiry(${inq.id})">
                        <i data-lucide="rotate-ccw"></i> Restore
                    </button>
                </td>
            </tr>
        `).join('');
        lucide.createIcons();
    } catch (e) {
        showToast('Error loading trash items', 'error');
    }
}

// --- CRUD FORMS & MODALS ---
function openModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

function openNewInquiryModal() {
    document.getElementById('modal-inquiry-title').innerText = 'New Inquiry';
    document.getElementById('form-inquiry').reset();
    document.getElementById('inq-id').value = '';
    document.getElementById('inq-id').removeAttribute('value');
    
    // Set default dates to today
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('inq-date').value = today;
    
    openModal('modal-inquiry');
}

async function openEditInquiryModal(id) {
    try {
        const res = await fetch(`/api/inquiries/${id}`);
        const inq = await res.json();
        
        document.getElementById('modal-inquiry-title').innerText = 'Modify Inquiry Specs';
        document.getElementById('inq-id').value = inq.id;
        document.getElementById('inq-date').value = inq.inquiry_date || '';
        document.getElementById('inq-due').value = inq.due_date || '';
        document.getElementById('inq-client').value = inq.client?.name || '';
        document.getElementById('inq-principal').value = inq.principal?.name || '';
        document.getElementById('inq-ref').value = inq.inquiry_reference || '';
        document.getElementById('inq-quotation').value = inq.quotation_reference || '';
        document.getElementById('inq-value').value = inq.value || '';
        document.getElementById('inq-submission').value = inq.submission_method || 'email';
        document.getElementById('inq-bid-bond').value = inq.bid_bond_value || '';
        document.getElementById('inq-perf-bond').value = inq.performance_bond || '';
        document.getElementById('inq-validity').value = inq.quotation_validity || '';
        document.getElementById('inq-expire').value = inq.expiration_date || '';
        document.getElementById('inq-contact').value = inq.contact_person || '';

        openModal('modal-inquiry');
    } catch (e) {
        showToast('Failed to fetch inquiry details', 'error');
    }
}

async function saveInquiry(e) {
    e.preventDefault();
    const id = document.getElementById('inq-id').value;
    
    const payload = {
        inquiry_date: document.getElementById('inq-date').value,
        due_date: document.getElementById('inq-due').value || null,
        client_name: document.getElementById('inq-client').value,
        principal_name: document.getElementById('inq-principal').value,
        inquiry_reference: document.getElementById('inq-ref').value,
        quotation_reference: document.getElementById('inq-quotation').value,
        value: parseFloat(document.getElementById('inq-value').value) || 0.0,
        submission_method: document.getElementById('inq-submission').value,
        bid_bond_value: document.getElementById('inq-bid-bond').value,
        performance_bond: document.getElementById('inq-perf-bond').value,
        quotation_validity: document.getElementById('inq-validity').value,
        expiration_date: document.getElementById('inq-expire').value || null,
        contact_person: document.getElementById('inq-contact').value
    };

    const method = id ? 'PUT' : 'POST';
    const url = id ? `/api/inquiries/${id}` : '/api/inquiries';

    try {
        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            showToast(id ? 'Inquiry specs updated!' : 'New inquiry created!');
            closeModal('modal-inquiry');
            loadInquiries();
            loadDropdownAutocompletes();
        } else {
            const err = await res.json();
            showToast(err.detail || 'Failed to save inquiry', 'error');
        }
    } catch (e) {
        showToast('Server network error', 'error');
    }
}

async function softDeleteInquiry(id) {
    if (!confirm('Are you sure you want to soft delete this inquiry?')) return;
    try {
        const res = await fetch(`/api/inquiries/${id}`, { method: 'DELETE' });
        if (res.ok) {
            showToast('Inquiry moved to Trash Bin');
            loadInquiries();
        } else {
            showToast('Delete operation failed', 'error');
        }
    } catch (e) {
        showToast('Network error during deletion', 'error');
    }
}

async function restoreInquiry(id) {
    try {
        const res = await fetch(`/api/inquiries/${id}/restore`, { method: 'POST' });
        if (res.ok) {
            showToast('Inquiry successfully restored');
            loadTrash();
        } else {
            showToast('Restore operation failed', 'error');
        }
    } catch (e) {
        showToast('Network error during restore', 'error');
    }
}

// --- SPEC DETAIL VIEW & COMMENTS CONTROLLER ---
async function viewInquiryDetail(id) {
    try {
        const res = await fetch(`/api/inquiries/${id}`);
        const inq = await res.json();
        
        activeInquiryIdForComments = inq.id;
        
        // Fields
        document.getElementById('detail-client').innerText = inq.client?.name || '-';
        document.getElementById('detail-principal').innerText = inq.principal?.name || '-';
        document.getElementById('detail-date').innerText = inq.inquiry_date || '-';
        document.getElementById('detail-due').innerText = inq.due_date || '-';
        document.getElementById('detail-value').innerText = formatMoney(inq.value);
        document.getElementById('detail-submission').innerText = inq.submission_method || '-';
        document.getElementById('detail-bid-bond').innerText = inq.bid_bond_value || '-';
        document.getElementById('detail-perf-bond').innerText = inq.performance_bond || '-';
        document.getElementById('detail-validity').innerText = inq.quotation_validity || '-';
        document.getElementById('detail-expire').innerText = inq.expiration_date || '-';
        document.getElementById('detail-contact').innerText = inq.contact_person || '-';
        document.getElementById('detail-ref').innerText = inq.inquiry_reference || '-';
        document.getElementById('detail-quotation').innerText = inq.quotation_reference || '-';
        
        // Status Badge
        const statusBadge = document.getElementById('detail-status');
        statusBadge.className = `status-badge status-${inq.status.toLowerCase()}`;
        statusBadge.innerText = inq.status;

        // Comments
        renderCommentsList(inq.comments);

        openModal('modal-details');
    } catch (e) {
        showToast('Could not load detail specifications', 'error');
    }
}

function renderCommentsList(comments) {
    const listContainer = document.getElementById('detail-comments-list');
    if (!comments || comments.length === 0) {
        listContainer.innerHTML = '<div class="empty-alert">No comment logs for this inquiry.</div>';
        return;
    }
    listContainer.innerHTML = comments.map(c => `
        <div class="comment-bubble">
            <div>${c.content}</div>
            <div class="comment-meta">${new Date(c.created_at).toLocaleString()}</div>
        </div>
    `).join('');
    listContainer.scrollTop = listContainer.scrollHeight;
}

async function submitNewComment() {
    const textInput = document.getElementById('new-comment-text');
    const content = textInput.value.trim();
    if (!content) return;

    try {
        const res = await fetch(`/api/inquiries/${activeInquiryIdForComments}/comments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: content })
        });
        
        if (res.ok) {
            textInput.value = '';
            // Reload comments
            const commentsRes = await fetch(`/api/inquiries/${activeInquiryIdForComments}/comments`);
            const updatedComments = await commentsRes.json();
            renderCommentsList(updatedComments);
            showToast('Comment recorded');
        } else {
            showToast('Failed to save comment', 'error');
        }
    } catch (e) {
        showToast('Network error adding comment', 'error');
    }
}

// --- STATUS TRANSITIONS ---
async function triggerTransition(id, targetStatus) {
    if (targetStatus === 'Won') {
        // Must show Order Form to transition
        document.getElementById('form-order-transition').reset();
        document.getElementById('trans-inq-id').value = id;
        
        // Pre-fill some defaults if possible
        try {
            const inqRes = await fetch(`/api/inquiries/${id}`);
            const inq = await inqRes.json();
            document.getElementById('ord-val').value = inq.value || 0.0;
            document.getElementById('ord-total').value = inq.value || 0.0;
            document.getElementById('ord-date').value = new Date().toISOString().split('T')[0];
        } catch(e) {}
        
        openModal('modal-order-transition');
    } else {
        // Direct transition
        if (!confirm(`Are you sure you want to transition this inquiry to "${targetStatus}"?`)) return;
        try {
            const res = await fetch(`/api/inquiries/${id}/transition?status=${targetStatus}`, {
                method: 'POST'
            });
            if (res.ok) {
                showToast(`Status updated to ${targetStatus}`);
                loadInquiries();
            } else {
                const err = await res.json();
                showToast(err.detail || 'Transition blocked by business rules.', 'error');
            }
        } catch (e) {
            showToast('Network error transitioning status', 'error');
        }
    }
}

async function saveOrderTransition(e) {
    e.preventDefault();
    const id = document.getElementById('trans-inq-id').value;
    
    const orderPayload = {
        order_number: document.getElementById('ord-number').value,
        order_date: document.getElementById('ord-date').value,
        order_value: parseFloat(document.getElementById('ord-val').value) || 0.0,
        additionals: parseFloat(document.getElementById('ord-additionals').value) || 0.0,
        total_order_value: parseFloat(document.getElementById('ord-total').value) || 0.0,
        order_confirmation_number: document.getElementById('ord-conf-num').value,
        team_commission: document.getElementById('ord-commission').value,
        order_confirmations: "",
        delivery_term: document.getElementById('ord-delivery-term').value,
        cargo_x: "",
        delay_penalty: "",
        delivery_period: "",
        expected_delivery_date: document.getElementById('ord-expected-delivery').value || null,
        performance_bond_guarantee: "",
        payment_method: document.getElementById('ord-payment-method').value,
        payment_status: document.getElementById('ord-payment-status').value
    };

    try {
        const res = await fetch(`/api/inquiries/${id}/transition?status=Won`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(orderPayload)
        });

        if (res.ok) {
            showToast('Inquiry transitioned to Won Order successfully!', 'success');
            closeModal('modal-order-transition');
            loadInquiries();
        } else {
            const err = await res.json();
            showToast(err.detail || 'Failed to complete order transition', 'error');
        }
    } catch (e) {
        showToast('Network error during order transition', 'error');
    }
}

// --- EXCEL SYNC CONTROLLER ---
async function syncExcel() {
    showToast('Syncing database with Excel file...', 'warning');
    try {
        const res = await fetch('/api/sync/export', { method: 'POST' });
        if (res.ok) {
            const data = await res.json();
            showToast(data.message, 'success');
            loadDashboardData();
        } else {
            showToast('Excel synchronization failed', 'error');
        }
    } catch (e) {
        showToast('Excel synchronization endpoint failed', 'error');
    }
}
