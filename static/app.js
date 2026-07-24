// Global App State
let activeTab = 'dashboard';
let clientsList = [];
let principalsList = [];
let activeInquiryIdForComments = null;
let pipelineChart = null;
let annualReportChart = null;

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

// Format Single Currency
function formatMoney(value, currency = 'USD') {
    if (value === null || value === undefined) value = 0;
    const curr = (currency || 'USD').toUpperCase();
    if (curr === 'EUR') {
        return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(value);
    }
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
}

// Format Dual Currency string ($X | €Y)
function formatDualMoney(usdVal, eurVal) {
    const usd = formatMoney(usdVal, 'USD');
    const eur = formatMoney(eurVal, 'EUR');
    return `${usd} | ${eur}`;
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
    } else if (tabId === 'report') {
        loadAnnualReport();
    } else if (tabId === 'analytics') {
        loadAnalyticsData();
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
        document.getElementById('header-active-val').innerText = formatDualMoney(data.total_value_active_usd, data.total_value_active_eur);
        document.getElementById('header-won-val').innerText = formatDualMoney(data.total_value_won_usd, data.total_value_won_eur);
        
        // Update stats cards
        document.getElementById('stats-active').innerText = data.active_inquiries;
        document.getElementById('stats-active-val').innerText = formatDualMoney(data.total_value_active_usd, data.total_value_active_eur);
        
        document.getElementById('stats-won').innerText = data.won_inquiries;
        document.getElementById('stats-won-val').innerText = formatDualMoney(data.total_value_won_usd, data.total_value_won_eur);
        
        document.getElementById('stats-lost').innerText = data.lost_inquiries;
        document.getElementById('stats-lost-val').innerText = formatDualMoney(data.total_value_lost_usd, data.total_value_lost_eur);

        document.getElementById('stats-declined').innerText = data.declined_inquiries;

        // Render chart
        renderPipelineChart(data);
        
        // Populate alerts list: Inquiries Due (Changed Inspect -> View)
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
                    <button class="alert-action-btn" onclick="viewInquiryDetail(${inq.id})">View</button>
                </div>
            `).join('');
        }

        // Populate alerts list: Delivery Near (Changed Inspect -> View)
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
                    <button class="alert-action-btn" onclick="viewInquiryDetail(${inq.id})">View</button>
                </div>
            `).join('');
        }
    } catch (e) {
        showToast('Error loading dashboard stats', 'error');
    }
}

function renderPipelineChart(stats) {
    const ctx = document.getElementById('pipelineChart').getContext('2d');
    if (pipelineChart) pipelineChart.destroy();
    
    pipelineChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Active', 'Order', 'Lost', 'Declined'],
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
        
        populateFilters(inquiries);

        if (clientFilter) inquiries = inquiries.filter(i => i.client?.name === clientFilter);
        if (principalFilter) inquiries = inquiries.filter(i => i.principal?.name === principalFilter);
        
        const inquiriesList = document.getElementById('inquiries-list');
        if (inquiries.length === 0) {
            inquiriesList.innerHTML = `<tr><td colspan="11" class="empty-alert">No matching inquiries found in the pipeline.</td></tr>`;
            return;
        }

        inquiriesList.innerHTML = inquiries.map(inq => `
            <tr>
                <td>${inq.inquiry_date || '-'}</td>
                <td>${inq.due_date ? `<strong>${inq.due_date}</strong>` : '-'}</td>
                <td style="font-weight:600">${inq.client?.name || '-'}</td>
                <td style="color:var(--text-muted); font-size:0.875rem">${inq.principal?.name || '-'}</td>
                <td title="${inq.inquiry_reference}">${inq.inquiry_reference ? inq.inquiry_reference.substring(0, 40) + (inq.inquiry_reference.length > 40 ? '...' : '') : '-'}</td>
                <td>${inq.quotation_reference || '-'}</td>
                <td style="font-weight:600">${formatMoney(inq.value, inq.currency)}</td>
                <td><span class="status-badge" style="background:rgba(255,255,255,0.05); color:#94a3b8">${inq.offer_type || 'Firm'}</span></td>
                <td>${inq.last_update || '-'}</td>
                <td><span class="status-badge status-${inq.status.toLowerCase()}">${inq.status}</span></td>
                <td class="no-print">
                    <div style="display:flex; gap:0.4rem">
                        <button class="btn btn-secondary btn-sm" onclick="viewInquiryDetail(${inq.id})">Details</button>
                        <button class="btn btn-primary btn-sm" onclick="openEditInquiryModal(${inq.id})">Edit</button>
                        <button class="btn btn-danger btn-sm" onclick="softDeleteInquiry(${inq.id})">Delete</button>
                        ${inq.status === 'Active' ? `
                            <button class="btn btn-success btn-sm" onclick="triggerTransition(${inq.id}, 'Order')">Order</button>
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
    
    const currentClient = clientSelect.value;
    const currentPrincipal = principalSelect.value;

    const clients = [...new Set(data.map(i => i.client?.name).filter(Boolean))].sort();
    const principals = [...new Set(data.map(i => i.principal?.name).filter(Boolean))].sort();

    clientSelect.innerHTML = '<option value="">All Clients</option>' + 
        clients.map(c => `<option value="${c}">${c}</option>`).join('');
    principalSelect.innerHTML = '<option value="">All Principals</option>' + 
        principals.map(p => `<option value="${p}">${p}</option>`).join('');

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
        const res = await fetch(`/api/inquiries?status=All&search=${encodeURIComponent(query)}`);
        const searchResults = await res.json();
        
        if (activeTab === 'inquiries') {
            const list = document.getElementById('inquiries-list');
            if (searchResults.length === 0) {
                list.innerHTML = `<tr><td colspan="11" class="empty-alert">No search results matching your query.</td></tr>`;
                return;
            }
            list.innerHTML = searchResults.map(inq => `
                <tr>
                    <td>${inq.inquiry_date || '-'}</td>
                    <td>${inq.due_date || '-'}</td>
                    <td style="font-weight:600">${inq.client?.name || '-'}</td>
                    <td style="color:var(--text-muted); font-size:0.875rem">${inq.principal?.name || '-'}</td>
                    <td title="${inq.inquiry_reference}">${inq.inquiry_reference ? inq.inquiry_reference.substring(0, 40) + (inq.inquiry_reference.length > 40 ? '...' : '') : '-'}</td>
                    <td>${inq.quotation_reference || '-'}</td>
                    <td style="font-weight:600">${formatMoney(inq.value, inq.currency)}</td>
                    <td>${inq.offer_type || 'Firm'}</td>
                    <td>${inq.last_update || '-'}</td>
                    <td><span class="status-badge status-${inq.status.toLowerCase()}">${inq.status}</span></td>
                    <td class="no-print">
                        <div style="display:flex; gap:0.4rem">
                            <button class="btn btn-secondary btn-sm" onclick="viewInquiryDetail(${inq.id})">Details</button>
                            <button class="btn btn-primary btn-sm" onclick="openEditInquiryModal(${inq.id})">Edit</button>
                            <button class="btn btn-danger btn-sm" onclick="softDeleteInquiry(${inq.id})">Delete</button>
                        </div>
                    </td>
                </tr>
            `).join('');
        } else if (activeTab === 'orders') {
            const orders = searchResults.filter(inq => (inq.status === 'Won' || inq.status === 'Order') && inq.order);
            const list = document.getElementById('orders-list');
            if (orders.length === 0) {
                list.innerHTML = `<tr><td colspan="10" class="empty-alert">No orders found matching search criteria.</td></tr>`;
                return;
            }
            list.innerHTML = orders.map(inq => {
                const o = inq.order;
                return `
                    <tr>
                        <td style="font-weight:600">${inq.client?.name || '-'}</td>
                        <td style="color:var(--text-muted); font-size:0.875rem">${inq.principal?.name || '-'}</td>
                        <td><strong>${o.order_number || '-'}</strong></td>
                        <td>${o.order_date || '-'}</td>
                        <td>${o.expected_delivery_date || '-'}</td>
                        <td style="font-weight:600">${formatMoney(o.total_order_value, o.currency)}</td>
                        <td><span class="status-badge status-won">${o.order_status || 'Under Production'}</span></td>
                        <td><span class="status-badge" style="background:rgba(59,130,246,0.1); color:#60a5fa">${o.payment_status || 'CAD'}</span></td>
                        <td>${o.performance_bond_guarantee || '-'}</td>
                        <td class="no-print">
                            <button class="btn btn-secondary btn-sm" onclick="viewInquiryDetail(${inq.id})">Full Spec</button>
                            <button class="btn btn-primary btn-sm" onclick="openEditOrderModal(${inq.id})">Edit</button>
                        </td>
                    </tr>
                `;
            }).join('');
        }
    } catch (e) {
        showToast('Search query execution failed', 'error');
    }
}

// --- ORDERS CONTROLLER ---
async function loadOrders() {
    try {
        const sheetFilter = document.getElementById('order-filter-sheet').value;
        const res = await fetch('/api/inquiries?status=Order');
        let wonInquiries = await res.json();
        
        if (sheetFilter) {
            wonInquiries = wonInquiries.filter(inq => inq.order?.source_sheet === sheetFilter);
        }

        const ordersList = document.getElementById('orders-list');
        if (wonInquiries.length === 0) {
            ordersList.innerHTML = `<tr><td colspan="10" class="empty-alert">No orders recorded under this sheet.</td></tr>`;
            return;
        }

        ordersList.innerHTML = wonInquiries.map(inq => {
            const o = inq.order || {};
            return `
                <tr>
                    <td style="font-weight:600">${inq.client?.name || '-'}</td>
                    <td style="color:var(--text-muted); font-size:0.875rem">${inq.principal?.name || '-'}</td>
                    <td><strong>${o.order_number || '-'}</strong></td>
                    <td>${o.order_date || '-'}</td>
                    <td>${o.expected_delivery_date ? `<strong>${o.expected_delivery_date}</strong>` : '-'}</td>
                    <td style="font-weight:600">${formatMoney(o.total_order_value, o.currency)}</td>
                    <td><span class="status-badge status-won">${o.order_status || 'Under Production'}</span></td>
                    <td><span class="status-badge" style="background:rgba(59,130,246,0.1); color:#60a5fa">${o.payment_status || 'CAD'}</span></td>
                    <td>${o.performance_bond_guarantee || '-'}</td>
                    <td class="no-print">
                        <div style="display:flex; gap:0.4rem">
                            <button class="btn btn-secondary btn-sm" onclick="viewInquiryDetail(${inq.id})">Full Spec</button>
                            <button class="btn btn-primary btn-sm" onclick="openEditOrderModal(${inq.id})">Edit</button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (e) {
        showToast('Error loading orders list', 'error');
    }
}

// --- ANNUAL REPORT CONTROLLER ---
async function loadAnnualReport() {
    try {
        const yearSelect = document.getElementById('report-year-select').value;
        const url = yearSelect === 'All' ? '/api/annual-report' : `/api/annual-report?year=${yearSelect}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error('Annual report fetch failed');
        const data = await res.json();

        // 1) Inquiries / Tenders
        document.getElementById('rpt-tenders-count').innerText = data.tenders_total.count;
        document.getElementById('rpt-tenders-usd').innerText = formatMoney(data.tenders_total.values.usd, 'USD');
        document.getElementById('rpt-tenders-eur').innerText = formatMoney(data.tenders_total.values.eur, 'EUR');

        document.getElementById('rpt-canc-count').innerText = data.tenders_cancelled.count;
        document.getElementById('rpt-canc-usd').innerText = formatMoney(data.tenders_cancelled.values.usd, 'USD');
        document.getElementById('rpt-canc-eur').innerText = formatMoney(data.tenders_cancelled.values.eur, 'EUR');

        document.getElementById('rpt-decl-count').innerText = data.tenders_declined.count;
        document.getElementById('rpt-decl-usd').innerText = formatMoney(data.tenders_declined.values.usd, 'USD');
        document.getElementById('rpt-decl-eur').innerText = formatMoney(data.tenders_declined.values.eur, 'EUR');

        document.getElementById('rpt-firm-count').innerText = data.tenders_firm.count;
        document.getElementById('rpt-firm-usd').innerText = formatMoney(data.tenders_firm.values.usd, 'USD');
        document.getElementById('rpt-firm-eur').innerText = formatMoney(data.tenders_firm.values.eur, 'EUR');

        document.getElementById('rpt-budg-count').innerText = data.tenders_budgetary.count;
        document.getElementById('rpt-budg-usd').innerText = formatMoney(data.tenders_budgetary.values.usd, 'USD');
        document.getElementById('rpt-budg-eur').innerText = formatMoney(data.tenders_budgetary.values.eur, 'EUR');

        // 2) Submitted Offers
        document.getElementById('rpt-ong-count').innerText = data.submitted_ongoing.count;
        document.getElementById('rpt-ong-usd').innerText = formatMoney(data.submitted_ongoing.values.usd, 'USD');
        document.getElementById('rpt-ong-eur').innerText = formatMoney(data.submitted_ongoing.values.eur, 'EUR');

        document.getElementById('rpt-award-count').innerText = data.submitted_awarded.count;
        document.getElementById('rpt-award-usd').innerText = formatMoney(data.submitted_awarded.values.usd, 'USD');
        document.getElementById('rpt-award-eur').innerText = formatMoney(data.submitted_awarded.values.eur, 'EUR');

        document.getElementById('rpt-lost-count').innerText = data.submitted_lost.count;
        document.getElementById('rpt-lost-usd').innerText = formatMoney(data.submitted_lost.values.usd, 'USD');
        document.getElementById('rpt-lost-eur').innerText = formatMoney(data.submitted_lost.values.eur, 'EUR');

        // 3) Orders Breakdown
        document.getElementById('rpt-ord-prod-count').innerText = data.orders_under_production.count;
        document.getElementById('rpt-ord-prod-usd').innerText = formatMoney(data.orders_under_production.values.usd, 'USD');
        document.getElementById('rpt-ord-prod-eur').innerText = formatMoney(data.orders_under_production.values.eur, 'EUR');

        document.getElementById('rpt-ord-ship-count').innerText = data.orders_shipped.count;
        document.getElementById('rpt-ord-ship-usd').innerText = formatMoney(data.orders_shipped.values.usd, 'USD');
        document.getElementById('rpt-ord-ship-eur').innerText = formatMoney(data.orders_shipped.values.eur, 'EUR');

        document.getElementById('rpt-ord-paid-count').innerText = data.orders_paid.count;
        document.getElementById('rpt-ord-paid-usd').innerText = formatMoney(data.orders_paid.values.usd, 'USD');
        document.getElementById('rpt-ord-paid-eur').innerText = formatMoney(data.orders_paid.values.eur, 'EUR');

        document.getElementById('rpt-ord-due-count').innerText = data.orders_due_payment.count;
        document.getElementById('rpt-ord-due-usd').innerText = formatMoney(data.orders_due_payment.values.usd, 'USD');
        document.getElementById('rpt-ord-due-eur').innerText = formatMoney(data.orders_due_payment.values.eur, 'EUR');

        // Render Pie Chart for Detailed Overview
        renderAnnualReportChart(data.chart_distribution);
    } catch (e) {
        showToast('Error loading annual report', 'error');
    }
}

function renderAnnualReportChart(dist) {
    const ctx = document.getElementById('annualReportChart').getContext('2d');
    if (annualReportChart) annualReportChart.destroy();

    const labels = Object.keys(dist);
    const counts = Object.values(dist);

    annualReportChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: counts,
                backgroundColor: ['#3b82f6', '#10b981', '#ef4444', '#64748b', '#f59e0b'],
                borderWidth: 1,
                borderColor: '#1e293b'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: { color: '#f8fafc', font: { family: 'Outfit', size: 12 } }
                }
            }
        }
    });
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

// --- TRASH BIN CONTROLLER ---
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
                <td>${formatMoney(inq.value, inq.currency)}</td>
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
    const overlay = document.getElementById(modalId);
    if (overlay) {
        overlay.classList.remove('active');
        const card = overlay.querySelector('.modal-card');
        if (card) {
            card.classList.remove('modal-fullscreen');
            const btn = document.getElementById('btn-toggle-fullscreen');
            if (btn) {
                btn.innerHTML = '<i data-lucide="maximize-2"></i> Fullscreen';
                lucide.createIcons();
            }
        }
    }
}

function toggleFullscreenModal(cardId) {
    const card = document.getElementById(cardId);
    if (!card) return;
    card.classList.toggle('modal-fullscreen');
    const btn = document.getElementById('btn-toggle-fullscreen');
    if (btn) {
        const isFS = card.classList.contains('modal-fullscreen');
        btn.innerHTML = isFS ? '<i data-lucide="minimize-2"></i> Exit Fullscreen' : '<i data-lucide="maximize-2"></i> Fullscreen';
        lucide.createIcons();
    }
}

function openNewInquiryModal() {
    document.getElementById('modal-inquiry-title').innerText = 'New Inquiry';
    document.getElementById('form-inquiry').reset();
    document.getElementById('inq-id').value = '';
    document.getElementById('inq-id').removeAttribute('value');
    
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
        document.getElementById('inq-currency').value = inq.currency || 'USD';
        document.getElementById('inq-value').value = inq.value || '';
        document.getElementById('inq-offer-type').value = inq.offer_type || 'Firm';
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

async function openEditOrderModal(id) {
    try {
        const res = await fetch(`/api/inquiries/${id}`);
        const inq = await res.json();
        const o = inq.order || {};

        document.getElementById('trans-inq-id').value = inq.id;
        document.getElementById('ord-number').value = o.order_number || '';
        document.getElementById('ord-date').value = o.order_date || '';
        document.getElementById('ord-currency').value = o.currency || inq.currency || 'USD';
        document.getElementById('ord-val').value = o.order_value || inq.value || 0;
        document.getElementById('ord-additionals').value = o.additionals || 0;
        document.getElementById('ord-total').value = o.total_order_value || o.order_value || 0;
        document.getElementById('ord-status').value = o.order_status || 'Under Production';
        document.getElementById('ord-payment-status').value = o.payment_status || 'Order ready';
        document.getElementById('ord-perf-bond').value = o.performance_bond_guarantee || inq.performance_bond || '';
        document.getElementById('ord-conf-num').value = o.order_confirmation_number || '';
        document.getElementById('ord-commission').value = o.team_commission || '';
        document.getElementById('ord-expected-delivery').value = o.expected_delivery_date || '';
        document.getElementById('ord-delivery-term').value = o.delivery_term || '';
        document.getElementById('ord-payment-method').value = o.payment_method || 'CAD';

        openModal('modal-order-transition');
    } catch(e) {
        showToast('Failed to fetch order specs', 'error');
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
        currency: document.getElementById('inq-currency').value,
        value: parseFloat(document.getElementById('inq-value').value) || 0.0,
        offer_type: document.getElementById('inq-offer-type').value,
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
        
        document.getElementById('detail-client').innerText = inq.client?.name || '-';
        document.getElementById('detail-principal').innerText = inq.principal?.name || '-';
        document.getElementById('detail-date').innerText = inq.inquiry_date || '-';
        document.getElementById('detail-due').innerText = inq.due_date || '-';
        document.getElementById('detail-value').innerText = formatMoney(inq.value, inq.currency);
        document.getElementById('detail-offer-type').innerText = inq.offer_type || 'Firm';
        document.getElementById('detail-last-update').innerText = inq.last_update || '-';
        document.getElementById('detail-submission').innerText = inq.submission_method || '-';
        document.getElementById('detail-bid-bond').innerText = inq.bid_bond_value || '-';
        document.getElementById('detail-perf-bond').innerText = inq.performance_bond || '-';
        document.getElementById('detail-validity').innerText = inq.quotation_validity || '-';
        document.getElementById('detail-expire').innerText = inq.expiration_date || '-';
        document.getElementById('detail-contact').innerText = inq.contact_person || '-';
        document.getElementById('detail-ref').innerText = inq.inquiry_reference || '-';
        document.getElementById('detail-quotation').innerText = inq.quotation_reference || '-';
        
        const statusBadge = document.getElementById('detail-status');
        statusBadge.className = `status-badge status-${inq.status.toLowerCase()}`;
        statusBadge.innerText = inq.status;

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
    if (targetStatus === 'Won' || targetStatus === 'Order') {
        document.getElementById('form-order-transition').reset();
        document.getElementById('trans-inq-id').value = id;
        
        try {
            const inqRes = await fetch(`/api/inquiries/${id}`);
            const inq = await inqRes.json();
            document.getElementById('ord-val').value = inq.value || 0.0;
            document.getElementById('ord-total').value = inq.value || 0.0;
            document.getElementById('ord-currency').value = inq.currency || 'USD';
            document.getElementById('ord-perf-bond').value = inq.performance_bond || '';
            document.getElementById('ord-date').value = new Date().toISOString().split('T')[0];
        } catch(e) {}
        
        openModal('modal-order-transition');
    } else {
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
        currency: document.getElementById('ord-currency').value,
        order_value: parseFloat(document.getElementById('ord-val').value) || 0.0,
        additionals: parseFloat(document.getElementById('ord-additionals').value) || 0.0,
        total_order_value: parseFloat(document.getElementById('ord-total').value) || 0.0,
        order_status: document.getElementById('ord-status').value,
        payment_status: document.getElementById('ord-payment-status').value,
        performance_bond_guarantee: document.getElementById('ord-perf-bond').value,
        order_confirmation_number: document.getElementById('ord-conf-num').value,
        team_commission: document.getElementById('ord-commission').value,
        expected_delivery_date: document.getElementById('ord-expected-delivery').value || null,
        delivery_term: document.getElementById('ord-delivery-term').value,
        payment_method: document.getElementById('ord-payment-method').value
    };

    try {
        const res = await fetch(`/api/inquiries/${id}/transition?status=Order`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(orderPayload)
        });

        if (res.ok) {
            showToast('Order specs saved successfully!', 'success');
            closeModal('modal-order-transition');
            if (activeTab === 'orders') loadOrders();
            else loadInquiries();
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

// --- BUSINESS INTELLIGENCE & ANALYTICS CONTROLLER ---
let activeBITab = 'sales';
let biTimeSeriesChart = null;

function switchBITab(subtab) {
    activeBITab = subtab;
    document.querySelectorAll('.bi-subtab').forEach(btn => btn.classList.remove('active'));
    const btn = document.getElementById(`bi-tab-${subtab}`);
    if (btn) btn.classList.add('active');

    document.querySelectorAll('.bi-view').forEach(v => v.style.display = 'none');
    const view = document.getElementById(`bi-view-${subtab}`);
    if (view) view.style.display = 'block';

    if (subtab === 'sales') loadSalesAnalyticsDashboard();
    else if (subtab === 'company') loadCompanyReport();
    else if (subtab === 'series') loadTimeSeriesAnalysis();
    else if (subtab === 'comparison') loadComparisonAnalytics();
}

function loadAnalyticsData() {
    switchBITab(activeBITab);
    populateCompanySelector();
}

async function onCompanyTypeChange() {
    const type = document.getElementById('bi-company-type')?.value || 'client';
    const lbl = document.getElementById('bi-company-select-label');
    if (lbl) {
        lbl.textContent = type === 'principal' ? 'Select Principal / Manufacturer:' : 'Select Client / Customer:';
    }
    await populateCompanySelector(true);
}

async function populateCompanySelector(forceReload = false) {
    const sel = document.getElementById('bi-company-select');
    if (!sel) return;
    if (!forceReload && sel.options.length > 0) return;

    const type = document.getElementById('bi-company-type')?.value || 'client';
    const endpoint = type === 'principal' ? '/api/principals' : '/api/clients';

    try {
        const res = await fetch(endpoint);
        const list = await res.json();
        sel.innerHTML = list.map(item => `<option value="${item.id}">${item.name}</option>`).join('');
        if (list.length > 0) loadCompanyReport();
    } catch (e) {
        console.error(`Failed to load ${type} list`, e);
    }
}

async function loadSalesAnalyticsDashboard() {
    try {
        const res = await fetch('/api/analytics/sales-dashboard');
        const data = await res.json();

        document.getElementById('bi-daily-inqs').textContent = data.daily.new_inquiries || 0;
        document.getElementById('bi-daily-sub').textContent = `Due Today: ${data.daily.due_today || 0}`;

        const wOrders = document.getElementById('bi-weekly-orders');
        if (wOrders) wOrders.textContent = data.weekly.won_orders || 0;

        document.getElementById('bi-monthly-winrate').textContent = `${data.monthly.win_rate || 0}%`;
        document.getElementById('bi-monthly-inqs').textContent = `${data.monthly.inquiries_count || 0} Inquiries`;

        const yOrders = document.getElementById('bi-yearly-orders');
        if (yOrders) yOrders.textContent = data.yearly.won_orders || 0;

        const insightsContainer = document.getElementById('bi-sales-insights');
        if (insightsContainer) {
            insightsContainer.innerHTML = (data.insights || []).map(ins => `<p class="mb-2">• ${ins}</p>`).join('');
        }
    } catch (e) {
        showToast('Error loading Sales Analytics Dashboard', 'error');
    }
}

async function loadCompanyReport() {
    const type = document.getElementById('bi-company-type')?.value || 'client';
    const sel = document.getElementById('bi-company-select');
    const companyId = sel ? sel.value : null;

    let url = `/api/analytics/company-report?company_type=${type}`;
    if (companyId) url += `&company_id=${companyId}`;

    try {
        const res = await fetch(url);
        const data = await res.json();

        const winRateLabel = document.getElementById('bi-card-winrate-label');
        if (winRateLabel) winRateLabel.textContent = `${data.company_type} Win Rate`;

        document.getElementById('bi-company-ai-summary').textContent = data.ai_executive_summary || '-';
        document.getElementById('bi-comp-winrate').textContent = `${data.kpis.win_rate || 0}%`;
        const compWon = document.getElementById('bi-comp-won');
        if (compWon) compWon.textContent = data.kpis.won_orders || 0;
        document.getElementById('bi-comp-pipe').textContent = formatDualMoney(data.kpis.pipeline_value_usd, data.kpis.pipeline_value_eur);
        document.getElementById('bi-comp-cycle').textContent = `${data.kpis.avg_sales_cycle_days || 0} Days`;

        // Render complete inquiries list related to company
        const inqsBody = document.getElementById('bi-company-inquiries-table-body');
        const inqsTitle = document.getElementById('bi-company-inquiries-title');
        const inqsCount = document.getElementById('bi-company-inquiries-count');

        if (inqsTitle) inqsTitle.textContent = `All Inquiries Related to ${data.company_type}: ${data.company_name}`;
        if (inqsCount) inqsCount.textContent = `${(data.inquiries || []).length} Records`;

        if (inqsBody) {
            if (data.inquiries && data.inquiries.length > 0) {
                inqsBody.innerHTML = data.inquiries.map(inq => {
                    const statusClass = `status-${(inq.status || 'Active').toLowerCase()}`;
                    return `
                        <tr>
                            <td>${inq.inquiry_date || '-'}</td>
                            <td>${inq.due_date || '-'}</td>
                            <td><strong>${inq.client ? inq.client.name : '-'}</strong></td>
                            <td><strong>${inq.principal ? inq.principal.name : '-'}</strong></td>
                            <td>${inq.inquiry_reference || '-'}</td>
                            <td>${formatMoney(inq.value, inq.currency)}</td>
                            <td>${inq.last_update || '-'}</td>
                            <td><span class="status-badge ${statusClass}">${inq.status}</span></td>
                            <td>
                                <button class="btn btn-secondary btn-sm" onclick="viewInquiryDetails(${inq.id})">
                                    <i data-lucide="eye"></i> View
                                </button>
                            </td>
                        </tr>
                    `;
                }).join('');
                lucide.createIcons();
            } else {
                inqsBody.innerHTML = `<tr><td colspan="9" class="text-center">No inquiries found for this ${data.company_type.toLowerCase()}.</td></tr>`;
            }
        }

        // Render largest orders
        const ordersBody = document.getElementById('bi-company-orders-list');
        if (ordersBody) {
            if (data.largest_orders && data.largest_orders.length > 0) {
                ordersBody.innerHTML = data.largest_orders.map(o => `
                    <tr>
                        <td><strong>${o.order_number}</strong></td>
                        <td>${o.order_date}</td>
                        <td>${o.principal}</td>
                        <td>${formatMoney(o.value, o.currency)}</td>
                    </tr>
                `).join('');
            } else {
                ordersBody.innerHTML = `<tr><td colspan="4" class="text-center">No orders recorded for this company.</td></tr>`;
            }
        }
    } catch (e) {
        showToast('Error loading Company Intelligence Report', 'error');
    }
}

async function loadTimeSeriesAnalysis() {
    const period = document.getElementById('bi-series-period')?.value || 'Monthly';
    try {
        const res = await fetch(`/api/analytics/time-series?period=${period}`);
        const data = await res.json();

        const ctx = document.getElementById('biTimeSeriesChart')?.getContext('2d');
        if (!ctx) return;

        if (biTimeSeriesChart) {
            biTimeSeriesChart.destroy();
        }

        biTimeSeriesChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: 'Inquiries Count',
                        data: data.inquiries_count,
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        fill: true,
                        tension: 0.3
                    },
                    {
                        label: 'Won Orders Count',
                        data: data.won_orders_count,
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        fill: true,
                        tension: 0.3
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                    y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                    y1: { position: 'right', ticks: { color: '#f59e0b' }, grid: { drawOnChartArea: false } }
                },
                plugins: {
                    legend: { labels: { color: '#f8fafc', font: { family: 'Outfit' } } }
                }
            }
        });
    } catch (e) {
        showToast('Error loading Time Series Analysis', 'error');
    }
}

async function loadComparisonAnalytics() {
    const period = document.getElementById('bi-comparison-period')?.value || 'Monthly';
    try {
        const res = await fetch(`/api/analytics/comparison?period=${period}`);
        const data = await res.json();

        document.getElementById('bi-comparison-explanation').textContent = data.natural_explanation || '-';
        document.getElementById('bi-cmp-hdr-curr').textContent = data.current_label;
        document.getElementById('bi-cmp-hdr-prev').textContent = data.previous_label;

        const tbody = document.getElementById('bi-comparison-table-body');
        if (tbody && data.metrics) {
            tbody.innerHTML = Object.entries(data.metrics).map(([metric, cmp]) => {
                const dirClass = cmp.direction === 'up' ? 'trend-up' : (cmp.direction === 'down' ? 'trend-down' : 'trend-flat');
                const dirIcon = cmp.direction === 'up' ? '↑' : (cmp.direction === 'down' ? '↓' : '→');
                return `
                    <tr>
                        <td><strong>${metric}</strong></td>
                        <td>${typeof cmp.current === 'number' && metric.includes('USD') ? formatMoney(cmp.current, 'USD') : (metric.includes('EUR') ? formatMoney(cmp.current, 'EUR') : cmp.current)}</td>
                        <td>${typeof cmp.previous === 'number' && metric.includes('USD') ? formatMoney(cmp.previous, 'USD') : (metric.includes('EUR') ? formatMoney(cmp.previous, 'EUR') : cmp.previous)}</td>
                        <td><strong>${cmp.change_pct > 0 ? '+' : ''}${cmp.change_pct}%</strong></td>
                        <td><span class="trend-badge ${dirClass}">${dirIcon} ${cmp.direction.toUpperCase()}</span></td>
                    </tr>
                `;
            }).join('');
        }
    } catch (e) {
        showToast('Error loading Comparison Analytics', 'error');
    }
}

// --- REPORT EXPORT MODULE (WORD, EXCEL, PDF) ---

function toggleExportMenu(event, menuId) {
    if (event) event.stopPropagation();
    const menu = document.getElementById(menuId);
    if (!menu) return;
    const isVisible = menu.style.display === 'block';
    closeExportMenus();
    if (!isVisible) {
        menu.style.display = 'block';
    }
}

function closeExportMenus() {
    document.querySelectorAll('.export-menu-card').forEach(menu => {
        menu.style.display = 'none';
    });
}

document.addEventListener('click', function(event) {
    if (!event.target.closest('.export-dropdown')) {
        closeExportMenus();
    }
});

function getCleanReportContent(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return '';
    const clone = container.cloneNode(true);
    
    // Remove non-printable elements, filter ribbons, buttons, search inputs
    clone.querySelectorAll('.no-print, .filter-ribbon, button, select, input, .export-dropdown').forEach(el => el.remove());
    return clone.innerHTML;
}

function exportReportToWord(containerId) {
    closeExportMenus();
    const content = getCleanReportContent(containerId);
    if (!content) {
        showToast('No report content found to export', 'error');
        return;
    }

    const dateStr = new Date().toISOString().split('T')[0];
    const fileName = `CRM_Report_${containerId}_${dateStr}.doc`;

    const htmlDoc = `
        <html xmlns:o='urn:schemas-microsoft-microsoft-com:office:office' 
              xmlns:w='urn:schemas-microsoft-microsoft-com:office:word' 
              xmlns='http://www.w3.org/TR/REC-html40'>
        <head>
            <meta charset='utf-8'>
            <title>CRM Report</title>
            <style>
                body { font-family: 'Calibri', 'Segoe UI', Arial, sans-serif; font-size: 11pt; color: #1e293b; line-height: 1.5; }
                h1 { font-size: 20pt; color: #1e3a8a; margin-bottom: 8pt; }
                h2 { font-size: 16pt; color: #1e40af; border-bottom: 2pt solid #3b82f6; padding-bottom: 4pt; margin-top: 16pt; }
                h3 { font-size: 13pt; color: #1f2937; margin-top: 12pt; }
                h4 { font-size: 11pt; color: #374151; }
                table { border-collapse: collapse; width: 100%; margin-top: 10pt; margin-bottom: 15pt; }
                th, td { border: 1pt solid #cbd5e1; padding: 6pt 9pt; text-align: left; font-size: 10pt; }
                th { background-color: #f1f5f9; font-weight: bold; color: #0f172a; }
                .card { border: 1pt solid #e2e8f0; padding: 12pt; margin-bottom: 12pt; background-color: #f8fafc; }
                .stat-card { border: 1pt solid #cbd5e1; padding: 10pt; background: #ffffff; display: inline-block; margin: 4pt; min-width: 140pt; }
                .stat-label { font-size: 9pt; color: #64748b; font-weight: bold; }
                .stat-value { font-size: 16pt; font-weight: bold; color: #0f172a; }
                .status-badge { font-weight: bold; padding: 2pt 6pt; }
            </style>
        </head>
        <body>
            <h1 style="text-align: center;">TEAM Engineering CRM - Executive Report</h1>
            <p style="text-align: center; color: #64748b; font-size: 10pt;">Generated on: ${new Date().toLocaleString()}</p>
            <hr style="border: 0.5pt solid #cbd5e1; margin-bottom: 15pt;">
            ${content}
        </body>
        </html>
    `;

    const blob = new Blob(['\ufeff' + htmlDoc], { type: 'application/msword' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('Word report downloaded successfully', 'success');
}

function exportReportToExcel(containerId) {
    closeExportMenus();
    const container = document.getElementById(containerId);
    if (!container) {
        showToast('No report content found to export', 'error');
        return;
    }

    const tables = container.querySelectorAll('table');
    if (!tables || tables.length === 0) {
        showToast('No tabular report data found to export to Excel', 'warning');
        return;
    }

    let tablesHtml = '';
    tables.forEach((table, index) => {
        const titleEl = table.closest('.card')?.querySelector('h3, h4, h2')?.textContent || `Table ${index + 1}`;
        tablesHtml += `<h3>${titleEl}</h3>` + table.outerHTML + '<br/><br/>';
    });

    const dateStr = new Date().toISOString().split('T')[0];
    const fileName = `CRM_Report_Data_${containerId}_${dateStr}.xls`;

    const excelDoc = `
        <html xmlns:o="urn:schemas-microsoft-microsoft-com:office:office" 
              xmlns:x="urn:schemas-microsoft-microsoft-com:office:excel" 
              xmlns="http://www.w3.org/TR/REC-html40">
        <head>
            <meta charset="utf-8">
            <!--[if gte mso 9]>
            <xml>
                <x:ExcelWorkbook>
                    <x:ExcelWorksheets>
                        <x:ExcelWorksheet>
                            <x:Name>CRM Report</x:Name>
                            <x:WorksheetOptions><x:DisplayGridlines/></x:WorksheetOptions>
                        </x:ExcelWorksheet>
                    </x:ExcelWorksheets>
                </x:ExcelWorkbook>
            </xml>
            <![endif]-->
            <style>
                body { font-family: Arial, sans-serif; font-size: 10pt; }
                h3 { color: #1e3a8a; font-size: 12pt; margin-top: 12pt; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 0.5pt solid #a6a6a6; padding: 6px 10px; text-align: left; }
                th { background-color: #1e40af; color: #ffffff; font-weight: bold; }
                tr:nth-child(even) { background-color: #f8fafc; }
            </style>
        </head>
        <body>
            <h2>TEAM Engineering CRM - Tabular Report Data</h2>
            <p>Generated: ${new Date().toLocaleString()}</p>
            ${tablesHtml}
        </body>
        </html>
    `;

    const blob = new Blob(['\ufeff' + excelDoc], { type: 'application/vnd.ms-excel' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('Excel report data downloaded successfully', 'success');
}

function exportReportToPDF() {
    closeExportMenus();
    window.print();
}
