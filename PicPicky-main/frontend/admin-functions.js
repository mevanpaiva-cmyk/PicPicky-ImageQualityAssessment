// admin-functions.js - Connected to Real Backend

const API_BASE_URL = 'http://127.0.0.1:8000';
let currentDateRange = { start: null, end: null };
let autoRefreshInterval;

// ─────────────────────────────────────────
// Get admin token from session
// ─────────────────────────────────────────
function getAdminToken() {
    const adminSession = sessionStorage.getItem('adminSession');
    if (adminSession) {
        const data = JSON.parse(adminSession);
        return data.token || null;
    }
    return null;
}

// ─────────────────────────────────────────
// API Helper
// ─────────────────────────────────────────
async function apiRequest(endpoint, method = 'GET', body = null) {
    const token = getAdminToken();
    const headers = { 'Content-Type': 'application/json' };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const options = { method, headers };
    if (body && method !== 'GET') {
        options.body = JSON.stringify(body);
    }

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, options);

        if (!response.ok) {
            if (response.status === 401) {
                logout();
                return null;
            }
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        return await response.json();

    } catch (error) {
        console.error(`API Error [${endpoint}]:`, error);
        showNotification(`API Error: ${error.message}`, 'error');
        return null;
    }
}

// ─────────────────────────────────────────
// Fetch Functions
// ─────────────────────────────────────────
async function fetchMetrics() {
    return await apiRequest('/admin/metrics');
}

async function fetchUsers(start = null, end = null) {
    let url = '/admin/users';
    if (start && end) url += `?start=${start}&end=${end}`;
    return await apiRequest(url) || [];
}

async function fetchActivity(start = null, end = null, limit = 50) {
    let url = `/admin/activity?limit=${limit}`;
    if (start && end) url += `&start=${start}&end=${end}`;
    return await apiRequest(url) || [];
}

async function fetchAlerts() {
    return await apiRequest('/admin/alerts') || [];
}

async function fetchChartData(period = '24H') {
    return await apiRequest(`/admin/chart-data?period=${period}`) || [];
}

async function fetchExportStats(start = null, end = null) {
    let url = '/admin/stats/export';
    if (start && end) url += `?start=${start}&end=${end}`;
    return await apiRequest(url);
}

// ─────────────────────────────────────────
// Initialize Dashboard
// ─────────────────────────────────────────
async function initializeDashboard() {
    showLoadingState();

    try {
        const [metrics, users, activity, alerts] = await Promise.all([
            fetchMetrics(),
            fetchUsers(),
            fetchActivity(),
            fetchAlerts()
        ]);

        if (metrics) updateMetrics(metrics);

        window.usersData = users || [];
        window.activityData = activity || [];
        window.alertsData = alerts || [];

        renderActivityTable();
        renderAlerts();
        setupChartControls();
        setupNavigationLinks();
        setupExportButtons();
        setupDateRangeFilter();
        startAutoRefresh();

        hideLoadingState();
        showNotification('Dashboard loaded successfully', 'success');

    } catch (error) {
        console.error('Dashboard init error:', error);
        hideLoadingState();
        showNotification('Failed to load dashboard data', 'error');
    }
}

// ─────────────────────────────────────────
// Loading State
// ─────────────────────────────────────────
function showLoadingState() {
    if (document.getElementById('dashboardLoader')) return;
    const loader = document.createElement('div');
    loader.id = 'dashboardLoader';
    loader.className = 'fixed inset-0 bg-black/60 backdrop-blur-sm z-[100] flex items-center justify-center';
    loader.innerHTML = `
        <div class="glass-card p-10 rounded-2xl text-center">
            <div class="animate-spin rounded-full h-16 w-16 border-b-4 border-primary mx-auto mb-6"></div>
            <p class="text-on-surface font-semibold text-lg">Loading dashboard...</p>
            <p class="text-on-surface-variant text-sm mt-2">Fetching real data from server</p>
        </div>
    `;
    document.body.appendChild(loader);
}

function hideLoadingState() {
    const loader = document.getElementById('dashboardLoader');
    if (loader) loader.remove();
}

// ─────────────────────────────────────────
// Update Metrics
// ─────────────────────────────────────────
function updateMetrics(metrics) {
    if (!metrics) return;

    // Total Users (blue text)
    const totalUsersEl = document.querySelector(
        '.text-3xl.font-bold.tracking-tight.text-primary'
    );
    if (totalUsersEl) {
        totalUsersEl.textContent = formatNumber(metrics.totalUsers || 0);
    }

    // Other metrics (white text)
    const metricEls = document.querySelectorAll(
        '.text-3xl.font-bold.tracking-tight.text-on-surface'
    );
    if (metricEls[0]) metricEls[0].textContent = formatNumber(metrics.totalUploads || 0);
    if (metricEls[1]) metricEls[1].textContent = formatNumber(metrics.processedToday || 0);
    if (metricEls[2]) metricEls[2].textContent = (metrics.avgAnalysisTime || 0) + 's';
    if (metricEls[3]) metricEls[3].textContent = formatNumber(metrics.totalViews || 0);
}

// ─────────────────────────────────────────
// Format Helpers
// ─────────────────────────────────────────
function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
    return num.toString();
}

function formatTimeAgo(timestamp) {
    if (!timestamp) return 'Unknown';
    if (typeof timestamp === 'string' && timestamp.includes('ago')) return timestamp;

    const date = new Date(timestamp);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)} mins ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;
    return `${Math.floor(seconds / 86400)} days ago`;
}

function getInitials(name) {
    if (!name) return '??';
    return name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2);
}

function getStatusClass(status) {
    switch (status?.toLowerCase()) {
        case 'success': return 'bg-green-500/10 text-green-400';
        case 'info': return 'bg-primary/10 text-primary';
        case 'pending': return 'bg-secondary/10 text-secondary';
        case 'error':
        case 'failed': return 'bg-error/10 text-error';
        default: return 'bg-primary/10 text-primary';
    }
}

function getStatusBorderClass(status) {
    switch (status?.toLowerCase()) {
        case 'success': return 'border-green-500/20';
        case 'info': return 'border-primary/20';
        case 'pending': return 'border-secondary/20';
        case 'error':
        case 'failed': return 'border-error/20';
        default: return 'border-primary/20';
    }
}

// ─────────────────────────────────────────
// Render Activity Table
// ─────────────────────────────────────────
function renderActivityTable() {
    const tbody = document.querySelector('tbody');
    if (!tbody) return;

    if (!window.activityData || window.activityData.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="py-8 text-center text-on-surface-variant text-sm">
                    No activity found
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = window.activityData.slice(0, 10).map(activity => `
        <tr class="hover:bg-surface-container-low transition-colors group">
            <td class="py-4 flex items-center space-x-3">
                <div class="w-8 h-8 rounded-full bg-surface-container-highest flex items-center justify-center text-[10px] font-bold text-primary">
                    ${getInitials(activity.user || activity.userName)}
                </div>
                <span class="font-medium">${activity.user || activity.userName || 'Unknown'}</span>
            </td>
            <td class="py-4 text-on-surface-variant text-sm">${activity.action || 'Unknown action'}</td>
            <td class="py-4">
                <span class="px-2 py-0.5 rounded-full ${getStatusClass(activity.status)} text-[10px] font-bold border ${getStatusBorderClass(activity.status)}">
                    ${(activity.status || 'unknown').toUpperCase()}
                </span>
            </td>
            <td class="py-4 text-right text-on-surface-variant text-[11px]">
                ${formatTimeAgo(activity.timestamp || activity.time)}
            </td>
        </tr>
    `).join('');
}

// ─────────────────────────────────────────
// Render Alerts
// ─────────────────────────────────────────
function renderAlerts() {
    const alertsContainer = document.querySelector('.space-y-6');
    if (!alertsContainer || !window.alertsData) return;

    const header = alertsContainer.querySelector('.flex.justify-between.items-center');
    alertsContainer.innerHTML = '';
    if (header) alertsContainer.appendChild(header);

    const activeAlerts = window.alertsData.filter(a => !a.resolved);

    if (activeAlerts.length === 0) {
        alertsContainer.innerHTML += `
            <div class="glass-card p-5 rounded-lg border-l-4 border-green-500">
                <div class="flex items-center gap-3">
                    <span class="material-symbols-outlined text-green-400" style="font-variation-settings: 'FILL' 1;">check_circle</span>
                    <p class="text-sm font-bold text-on-surface">All clear! No active alerts.</p>
                </div>
            </div>
        `;
    } else {
        alertsContainer.innerHTML += activeAlerts.map(alert => `
            <div class="glass-card p-5 rounded-lg border-l-4 ${alert.type === 'error' ? 'border-error' : alert.type === 'warning' ? 'border-tertiary' : 'border-primary'} hover:translate-x-1 transition-transform cursor-pointer" onclick="viewAlertDetails(${alert.id})">
                <div class="flex justify-between items-start mb-2">
                    <span class="material-symbols-outlined ${alert.type === 'error' ? 'text-error' : alert.type === 'warning' ? 'text-tertiary' : 'text-primary'}" style="font-variation-settings: 'FILL' 1;">
                        ${alert.icon || 'warning'}
                    </span>
                    <div class="flex items-center gap-2">
                        <span class="text-[10px] text-on-surface-variant uppercase font-bold">Priority: ${alert.priority}</span>
                        <button onclick="resolveAlert(event, ${alert.id})" class="text-[10px] px-2 py-1 bg-primary/20 text-primary rounded hover:bg-primary/30 transition-colors">
                            Resolve
                        </button>
                    </div>
                </div>
                <h4 class="text-sm font-bold text-on-surface">${alert.title}</h4>
                <p class="text-xs text-on-surface-variant mt-1">${alert.description}</p>
            </div>
        `).join('');
    }

    updateAlertCount();
}

// Update alert badge
function updateAlertCount() {
    if (!window.alertsData) return;
    const count = window.alertsData.filter(a => !a.resolved).length;
    const badge = document.querySelector('.w-5.h-5.bg-error');
    if (badge) badge.textContent = count;
}

// View alert details
function viewAlertDetails(alertId) {
    const alert = window.alertsData.find(a => a.id === alertId);
    if (!alert) return;

    showModal('Alert Details', `
        <div class="space-y-4">
            <div class="flex items-center gap-3">
                <span class="material-symbols-outlined text-4xl ${alert.type === 'error' ? 'text-error' : 'text-tertiary'}" style="font-variation-settings: 'FILL' 1;">
                    ${alert.icon || 'warning'}
                </span>
                <div>
                    <h3 class="text-lg font-bold text-on-surface">${alert.title}</h3>
                    <span class="text-xs text-on-surface-variant uppercase tracking-widest">Priority: ${alert.priority}</span>
                </div>
            </div>
            <p class="text-sm text-on-surface-variant leading-relaxed">${alert.description}</p>
            <div class="flex gap-3 pt-4">
                <button onclick="resolveAlert(event, ${alert.id}); closeModal();" class="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors text-sm font-bold">
                    Mark as Resolved
                </button>
                <button onclick="closeModal()" class="px-4 py-2 bg-surface-container-high text-on-surface rounded-lg hover:bg-surface-container-highest transition-colors text-sm">
                    Close
                </button>
            </div>
        </div>
    `);
}

// Resolve alert
async function resolveAlert(event, alertId) {
    event.stopPropagation();
    await apiRequest(`/admin/alerts/${alertId}/resolve`, 'PATCH');
    const alert = window.alertsData.find(a => a.id === alertId);
    if (alert) {
        alert.resolved = true;
        renderAlerts();
        showNotification('Alert resolved successfully', 'success');
    }
}

// ─────────────────────────────────────────
// Chart Controls
// ─────────────────────────────────────────
function setupChartControls() {
    const buttons = document.querySelectorAll(
        '.flex.bg-surface-container-high.rounded-full button'
    );
    buttons.forEach(button => {
        button.addEventListener('click', async () => {
            buttons.forEach(btn => {
                btn.classList.remove('bg-primary', 'text-on-primary');
                btn.classList.add('text-on-surface-variant');
            });
            button.classList.add('bg-primary', 'text-on-primary');
            button.classList.remove('text-on-surface-variant');

            const period = button.textContent.trim();
            await updateChart(period);
        });
    });
}

// Update chart with real data
async function updateChart(period) {
    const data = await fetchChartData(period);
    const bars = document.querySelectorAll('.h-64 > div');

    if (!data || data.length === 0 || bars.length === 0) return;

    const maxValue = Math.max(...data.map(d => d.value || 0), 1);

    data.forEach((item, index) => {
        if (bars[index]) {
            const value = item.value || 0;
            const heightPercent = Math.max((value / maxValue) * 100, 3);
            bars[index].style.height = heightPercent + '%';

            const tooltip = bars[index].querySelector('.absolute');
            if (tooltip) tooltip.textContent = formatNumber(value);
        }
    });
}

// ─────────────────────────────────────────
// Navigation Links
// ─────────────────────────────────────────
function setupNavigationLinks() {
    const navLinks = document.querySelectorAll('nav a[href="#"]');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const page = link.textContent.trim();
            if (page === 'Dashboard') {
                showNotification('Already on Dashboard', 'info');
            } else if (page === 'Users') {
                showUsersPage();
            } else if (page === 'Alert') {
                showAlertsPage();
            }
        });
    });

    const viewAllBtn = document.querySelector(
        '.text-primary.text-xs.font-bold.uppercase.tracking-widest'
    );
    if (viewAllBtn) {
        viewAllBtn.addEventListener('click', showAllActivity);
    }
}

// ─────────────────────────────────────────
// Export Buttons in Navbar
// ─────────────────────────────────────────
function setupExportButtons() {
    const nav = document.querySelector('nav');
    if (!nav || document.getElementById('exportButtons')) return;

    const exportContainer = document.createElement('div');
    exportContainer.id = 'exportButtons';
    exportContainer.className = 'hidden md:flex items-center gap-2';
    exportContainer.innerHTML = `
        <button onclick="exportUsersToCSV()" class="px-3 py-1.5 bg-primary/20 text-primary rounded-lg hover:bg-primary/30 transition-colors text-xs font-bold flex items-center gap-1.5">
            <span class="material-symbols-outlined text-sm">download</span>
            Export CSV
        </button>
        <button onclick="exportDashboardToPDF()" class="px-3 py-1.5 bg-primary/20 text-primary rounded-lg hover:bg-primary/30 transition-colors text-xs font-bold flex items-center gap-1.5">
            <span class="material-symbols-outlined text-sm">picture_as_pdf</span>
            Export PDF
        </button>
    `;

    const profileSection = nav.querySelector('.flex.items-center.space-x-6');
    if (profileSection) nav.insertBefore(exportContainer, profileSection);
}

// ─────────────────────────────────────────
// Date Range Filter
// ─────────────────────────────────────────
function setupDateRangeFilter() {
    const main = document.querySelector('main');
    if (!main || document.getElementById('dateRangeFilter')) return;

    const filterContainer = document.createElement('div');
    filterContainer.id = 'dateRangeFilter';
    filterContainer.className = 'glass-card p-4 rounded-lg flex items-center gap-4 flex-wrap mb-4';
    filterContainer.innerHTML = `
        <span class="material-symbols-outlined text-primary">date_range</span>
        <span class="text-sm font-bold text-on-surface">Filter by Date:</span>
        <div class="flex items-center gap-2">
            <input type="date" id="startDate"
                class="px-3 py-2 bg-surface-container-high rounded-lg text-on-surface outline-none focus:ring-2 focus:ring-primary/50 text-sm">
            <span class="text-on-surface-variant text-sm">to</span>
            <input type="date" id="endDate"
                class="px-3 py-2 bg-surface-container-high rounded-lg text-on-surface outline-none focus:ring-2 focus:ring-primary/50 text-sm">
        </div>
        <button onclick="applyDateFilter()" class="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors text-sm font-bold">
            Apply Filter
        </button>
        <button onclick="clearDateFilter()" class="px-4 py-2 bg-surface-container-high text-on-surface rounded-lg hover:bg-surface-container-highest transition-colors text-sm">
            Clear
        </button>
        <span id="filterStatus" class="text-xs text-on-surface-variant"></span>
    `;

    // Set default dates (last 30 days)
    const today = new Date();
    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(today.getDate() - 30);

    main.insertBefore(filterContainer, main.firstChild);

    document.getElementById('endDate').value = today.toISOString().split('T')[0];
    document.getElementById('startDate').value = thirtyDaysAgo.toISOString().split('T')[0];
}

// Apply date filter
async function applyDateFilter() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;

    if (!startDate || !endDate) {
        showNotification('Please select both start and end dates', 'error');
        return;
    }

    if (new Date(startDate) > new Date(endDate)) {
        showNotification('Start date must be before end date', 'error');
        return;
    }

    currentDateRange = { start: startDate, end: endDate };

    const filterStatus = document.getElementById('filterStatus');
    if (filterStatus) filterStatus.textContent = 'Loading...';

    showLoadingState();

    try {
        const [users, activity, metrics] = await Promise.all([
            fetchUsers(startDate, endDate),
            fetchActivity(startDate, endDate),
            fetchMetrics()
        ]);

        if (users) window.usersData = users;
        if (activity) window.activityData = activity;
        if (metrics) updateMetrics(metrics);

        renderActivityTable();

        hideLoadingState();

        if (filterStatus) {
            filterStatus.textContent = `Showing data from ${startDate} to ${endDate}`;
        }

        showNotification(`Filtered from ${startDate} to ${endDate}`, 'success');

    } catch (error) {
        hideLoadingState();
        showNotification('Failed to apply date filter', 'error');
    }
}

// Clear date filter
async function clearDateFilter() {
    const today = new Date();
    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(today.getDate() - 30);

    document.getElementById('startDate').value = thirtyDaysAgo.toISOString().split('T')[0];
    document.getElementById('endDate').value = today.toISOString().split('T')[0];
    currentDateRange = { start: null, end: null };

    const filterStatus = document.getElementById('filterStatus');
    if (filterStatus) filterStatus.textContent = '';

    showLoadingState();

    const [users, activity] = await Promise.all([
        fetchUsers(),
        fetchActivity()
    ]);

    if (users) window.usersData = users;
    if (activity) window.activityData = activity;

    renderActivityTable();
    hideLoadingState();
    showNotification('Filter cleared - showing all data', 'info');
}

// ─────────────────────────────────────────
// Users Page Modal
// ─────────────────────────────────────────
async function showUsersPage() {
    const users = window.usersData || await fetchUsers();

    showModal('All Users', `
        <div class="space-y-4">
            <div class="flex justify-between items-center">
                <input type="text" placeholder="Search by name or email..."
                    class="px-4 py-2 bg-surface-container-high rounded-lg text-on-surface outline-none focus:ring-2 focus:ring-primary/50 text-sm w-64"
                    onkeyup="filterUsers(this.value)">
                <button onclick="exportUsersToCSV()" class="px-3 py-2 bg-primary/20 text-primary rounded-lg hover:bg-primary/30 transition-colors text-sm flex items-center gap-2 font-bold">
                    <span class="material-symbols-outlined text-sm">download</span>
                    Export CSV
                </button>
            </div>
            <div class="overflow-y-auto max-h-96 custom-scrollbar">
                <table class="w-full" id="usersTable">
                    <thead class="sticky top-0 bg-surface-container">
                        <tr class="text-left border-b border-outline-variant/10">
                            <th class="pb-3 pt-2 text-xs text-on-surface-variant font-bold uppercase tracking-widest">Name</th>
                            <th class="pb-3 pt-2 text-xs text-on-surface-variant font-bold uppercase tracking-widest">Email</th>
                            <th class="pb-3 pt-2 text-xs text-on-surface-variant font-bold uppercase tracking-widest">Uploads</th>
                            <th class="pb-3 pt-2 text-xs text-on-surface-variant font-bold uppercase tracking-widest">Level</th>
                            <th class="pb-3 pt-2 text-xs text-on-surface-variant font-bold uppercase tracking-widest">Score</th>
                            <th class="pb-3 pt-2 text-xs text-on-surface-variant font-bold uppercase tracking-widest">Status</th>
                            <th class="pb-3 pt-2 text-xs text-on-surface-variant font-bold uppercase tracking-widest">Actions</th>
                        </tr>
                    </thead>
                    <tbody id="usersTableBody">
                        ${renderUsersRows(users)}
                    </tbody>
                </table>
            </div>
            <p class="text-xs text-on-surface-variant">Total: ${users.length} users</p>
        </div>
    `);
}

function renderUsersRows(users) {
    if (!users || users.length === 0) {
        return `<tr><td colspan="7" class="py-8 text-center text-on-surface-variant text-sm">No users found</td></tr>`;
    }

    return users.map(user => `
        <tr class="border-b border-outline-variant/5 hover:bg-surface-container-low transition-colors">
            <td class="py-3 text-sm font-medium">${user.name}</td>
            <td class="py-3 text-sm text-on-surface-variant">${user.email}</td>
            <td class="py-3 text-sm">${user.uploads || 0}</td>
            <td class="py-3">
                <span class="px-2 py-1 rounded-full text-xs font-bold ${getLevelClass(user.level)}">
                    ${user.level || 'Beginner'}
                </span>
            </td>
            <td class="py-3 text-sm font-bold text-primary">${user.profileScore || 0}</td>
            <td class="py-3">
                <span class="px-2 py-1 rounded-full text-xs ${user.status === 'active' ? 'bg-green-500/10 text-green-400' : 'bg-error/10 text-error'}">
                    ${user.status || 'active'}
                </span>
            </td>
            <td class="py-3">
                <button onclick="viewUserDetails('${user.id}')"
                    class="text-primary hover:underline text-xs font-bold mr-2">
                    View
                </button>
            </td>
        </tr>
    `).join('');
}

function getLevelClass(level) {
    switch (level) {
        case 'Expert': return 'bg-primary/20 text-primary';
        case 'Advanced': return 'bg-green-500/20 text-green-400';
        case 'Intermediate': return 'bg-tertiary/20 text-tertiary';
        default: return 'bg-secondary/20 text-secondary';
    }
}

// Filter users in table
function filterUsers(searchTerm) {
    const filtered = window.usersData.filter(user =>
        user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        user.email.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const tbody = document.getElementById('usersTableBody');
    if (tbody) tbody.innerHTML = renderUsersRows(filtered);
}

// ─────────────────────────────────────────
// Activity Modal
// ─────────────────────────────────────────
function showAllActivity() {
    const activity = window.activityData || [];

    showModal('All Activity', `
        <div class="space-y-3">
            <div class="flex justify-end mb-2">
                <button onclick="exportActivityToCSV()" class="px-3 py-2 bg-primary/20 text-primary rounded-lg hover:bg-primary/30 transition-colors text-sm flex items-center gap-2 font-bold">
                    <span class="material-symbols-outlined text-sm">download</span>
                    Export Activity CSV
                </button>
            </div>
            <div class="overflow-y-auto max-h-96 custom-scrollbar space-y-2">
                ${activity.length === 0 ? '<p class="text-center text-on-surface-variant py-8">No activity found</p>' :
                    activity.map(act => `
                        <div class="p-4 bg-surface-container-low rounded-lg flex justify-between items-center hover:bg-surface-container transition-colors">
                            <div class="flex items-center gap-3">
                                <div class="w-10 h-10 rounded-full bg-surface-container-highest flex items-center justify-center text-xs font-bold text-primary">
                                    ${getInitials(act.user || act.userName)}
                                </div>
                                <div>
                                    <p class="text-sm font-medium text-on-surface">${act.user || act.userName || 'Unknown'}</p>
                                    <p class="text-xs text-on-surface-variant">${act.action}</p>
                                    ${act.technicalScore ? `<p class="text-xs text-primary/70 mt-0.5">Score: ${act.technicalScore}</p>` : ''}
                                </div>
                            </div>
                            <div class="text-right">
                                <span class="px-2 py-1 rounded-full ${getStatusClass(act.status)} text-xs font-bold">
                                    ${(act.status || 'unknown').toUpperCase()}
                                </span>
                                <p class="text-xs text-on-surface-variant mt-1">
                                    ${formatTimeAgo(act.timestamp || act.time)}
                                </p>
                            </div>
                        </div>
                    `).join('')
                }
            </div>
        </div>
    `);
}

// ─────────────────────────────────────────
// Alerts Modal
// ─────────────────────────────────────────
function showAlertsPage() {
    const alerts = window.alertsData || [];

    showModal('All Alerts', `
        <div class="overflow-y-auto max-h-96 custom-scrollbar space-y-3">
            ${alerts.length === 0 ? '<p class="text-center text-on-surface-variant py-8">No alerts found</p>' :
                alerts.map(alert => `
                    <div class="p-4 bg-surface-container-low rounded-lg border-l-4 ${alert.resolved ? 'border-green-500 opacity-60' : alert.type === 'error' ? 'border-error' : 'border-tertiary'}">
                        <div class="flex justify-between items-start mb-2">
                            <span class="material-symbols-outlined ${alert.type === 'error' ? 'text-error' : 'text-tertiary'}">
                                ${alert.icon || 'warning'}
                            </span>
                            <div class="flex items-center gap-2">
                                <span class="text-xs text-on-surface-variant">Priority: ${alert.priority}</span>
                                ${!alert.resolved ?
                                    `<button onclick="resolveAlert(event, ${alert.id}); showAlertsPage();" class="text-xs px-2 py-1 bg-primary/20 text-primary rounded hover:bg-primary/30 transition-colors">
                                        Resolve
                                    </button>` :
                                    '<span class="text-xs text-green-400 font-bold">✓ Resolved</span>'
                                }
                            </div>
                        </div>
                        <h4 class="text-sm font-bold text-on-surface">${alert.title}</h4>
                        <p class="text-xs text-on-surface-variant mt-1">${alert.description}</p>
                    </div>
                `).join('')
            }
        </div>
    `);
}

// ─────────────────────────────────────────
// User Details Modal (REAL DATA)
// ─────────────────────────────────────────
async function viewUserDetails(userId) {
    showLoadingState();

    const user = await apiRequest(`/admin/users/${userId}`);
    hideLoadingState();

    if (!user) {
        showNotification('Failed to load user details', 'error');
        return;
    }

    showModal('User Details', `
        <div class="space-y-6">
            <!-- Header -->
            <div class="flex items-center gap-4">
                <div class="w-20 h-20 rounded-full bg-surface-container-highest flex items-center justify-center text-2xl font-bold text-primary">
                    ${getInitials(user.name)}
                </div>
                <div>
                    <h3 class="text-xl font-bold text-on-surface">${user.name}</h3>
                    <p class="text-sm text-on-surface-variant">${user.email}</p>
                    <span class="px-2 py-1 rounded-full text-xs font-bold mt-1 inline-block ${getLevelClass(user.level)}">
                        ${user.level || 'Beginner'}
                    </span>
                </div>
            </div>

            <!-- Stats Grid -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div class="p-3 bg-surface-container-low rounded-lg text-center">
                    <p class="text-xs text-on-surface-variant uppercase tracking-widest mb-1">Uploads</p>
                    <p class="text-2xl font-bold text-primary">${user.uploads || 0}</p>
                </div>
                <div class="p-3 bg-surface-container-low rounded-lg text-center">
                    <p class="text-xs text-on-surface-variant uppercase tracking-widest mb-1">Profile Score</p>
                    <p class="text-2xl font-bold text-on-surface">${user.profileScore || 0}</p>
                </div>
                <div class="p-3 bg-surface-container-low rounded-lg text-center">
                    <p class="text-xs text-on-surface-variant uppercase tracking-widest mb-1">Blurry</p>
                    <p class="text-2xl font-bold text-error">${user.blurry || 0}</p>
                </div>
                <div class="p-3 bg-surface-container-low rounded-lg text-center">
                    <p class="text-xs text-on-surface-variant uppercase tracking-widest mb-1">Duplicates</p>
                    <p class="text-2xl font-bold text-tertiary">${user.duplicates || 0}</p>
                </div>
            </div>

            <!-- Score Breakdown -->
            <div class="grid grid-cols-2 gap-3">
                <div class="p-3 bg-surface-container-low rounded-lg">
                    <p class="text-xs text-on-surface-variant uppercase tracking-widest mb-1">Avg Technical Score</p>
                    <p class="text-xl font-bold text-on-surface">${user.avgTechnicalScore || 0}</p>
                </div>
                <div class="p-3 bg-surface-container-low rounded-lg">
                    <p class="text-xs text-on-surface-variant uppercase tracking-widest mb-1">Avg Aesthetic Score</p>
                    <p class="text-xl font-bold text-on-surface">${user.avgAestheticScore || 0}</p>
                </div>
                <div class="p-3 bg-surface-container-low rounded-lg">
                    <p class="text-xs text-on-surface-variant uppercase tracking-widest mb-1">Avg Sharpness</p>
                    <p class="text-xl font-bold text-on-surface">${user.avgSharpness || 0}</p>
                </div>
                <div class="p-3 bg-surface-container-low rounded-lg">
                    <p class="text-xs text-on-surface-variant uppercase tracking-widest mb-1">Member Since</p>
                    <p class="text-sm font-bold text-on-surface">${user.joinDate ? new Date(user.joinDate).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : 'N/A'}</p>
                </div>
            </div>

            <!-- Actions -->
            <div class="flex gap-3 pt-2">
                ${user.status !== 'suspended' ?
                    `<button onclick="suspendUser('${user.id}')" class="px-4 py-2 bg-error/20 text-error rounded-lg hover:bg-error/30 transition-colors text-sm font-bold">
                        Suspend User
                    </button>` :
                    `<button onclick="activateUser('${user.id}')" class="px-4 py-2 bg-green-500/20 text-green-400 rounded-lg hover:bg-green-500/30 transition-colors text-sm font-bold">
                        Activate User
                    </button>`
                }
                <button onclick="closeModal()" class="px-4 py-2 bg-surface-container-high text-on-surface rounded-lg hover:bg-surface-container-highest transition-colors text-sm">
                    Close
                </button>
            </div>
        </div>
    `);
}

// Suspend user
async function suspendUser(userId) {
    const result = await apiRequest(`/admin/users/${userId}/suspend`, 'PATCH');
    if (result) {
        const user = window.usersData.find(u => u.id === userId);
        if (user) user.status = 'suspended';
        showNotification('User suspended successfully', 'success');
        closeModal();
    }
}

// Activate user
async function activateUser(userId) {
    const result = await apiRequest(`/admin/users/${userId}/activate`, 'PATCH');
    if (result) {
        const user = window.usersData.find(u => u.id === userId);
        if (user) user.status = 'active';
        showNotification('User activated successfully', 'success');
        closeModal();
    }
}

// ─────────────────────────────────────────
// Export Functions
// ─────────────────────────────────────────
function exportToCSV(data, filename) {
    if (!data || data.length === 0) {
        showNotification('No data to export', 'error');
        return;
    }

    const headers = Object.keys(data[0]);
    const csvContent = [
        headers.join(','),
        ...data.map(row =>
            headers.map(header => {
                const val = row[header];
                return typeof val === 'string' && (val.includes(',') || val.includes('"'))
                    ? `"${val.replace(/"/g, '""')}"`
                    : val ?? '';
            }).join(',')
        )
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    showNotification('CSV exported successfully!', 'success');
}

async function exportUsersToCSV() {
    const data = await fetchExportStats(
        currentDateRange.start,
        currentDateRange.end
    );

    if (!data || !data.users) {
        showNotification('No user data available', 'error');
        return;
    }

    exportToCSV(
        data.users,
        `picpicky-users-${new Date().toISOString().split('T')[0]}.csv`
    );
}

async function exportActivityToCSV() {
    const activity = window.activityData || [];

    if (activity.length === 0) {
        showNotification('No activity data available', 'error');
        return;
    }

    const csvData = activity.map(act => ({
        'User': act.user || act.userName || '',
        'Email': act.userEmail || '',
        'Action': act.action || '',
        'Status': act.status || '',
        'Technical Score': act.technicalScore || '',
        'Aesthetic Score': act.aestheticScore || '',
        'Is Blurry': act.isBlurry || false,
        'Is Duplicate': act.isDuplicate || false,
        'Timestamp': act.timestamp || ''
    }));

    exportToCSV(
        csvData,
        `picpicky-activity-${new Date().toISOString().split('T')[0]}.csv`
    );
}

async function exportDashboardToPDF() {
    const data = await fetchExportStats(
        currentDateRange.start,
        currentDateRange.end
    );

    if (!data) {
        showNotification('Failed to fetch export data', 'error');
        return;
    }

    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>PicPicky Admin Report</title>
            <style>
                * { box-sizing: border-box; }
                body { font-family: Arial, sans-serif; padding: 40px; color: #333; margin: 0; }
                h1 { color: #207fdf; border-bottom: 3px solid #207fdf; padding-bottom: 12px; margin-bottom: 8px; }
                h2 { color: #444; margin-top: 30px; font-size: 18px; }
                .meta { color: #777; font-size: 13px; margin-bottom: 30px; }
                .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 24px 0; }
                .stat-box { background: #f0f7ff; border: 1px solid #bbd6f5; border-radius: 8px; padding: 16px; text-align: center; }
                .stat-box .label { font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: 1px; }
                .stat-box .value { font-size: 28px; font-weight: 900; color: #207fdf; margin-top: 6px; }
                table { width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 13px; }
                th { background: #207fdf; color: white; padding: 10px 12px; text-align: left; }
                td { border-bottom: 1px solid #eee; padding: 10px 12px; }
                tr:nth-child(even) td { background: #f9f9f9; }
                .footer { margin-top: 50px; text-align: center; color: #aaa; font-size: 11px; border-top: 1px solid #eee; padding-top: 20px; }
                @media print { body { padding: 20px; } }
            </style>
        </head>
        <body>
            <h1>🎯 PicPicky Admin Report</h1>
            <p class="meta">Generated: ${new Date().toLocaleString()} | Total Users: ${data.totalUsers} | Total Images: ${data.totalImages}</p>

            <div class="stats-grid">
                <div class="stat-box">
                    <div class="label">Total Users</div>
                    <div class="value">${data.totalUsers}</div>
                </div>
                <div class="stat-box">
                    <div class="label">Total Images</div>
                    <div class="value">${data.totalImages}</div>
                </div>
                <div class="stat-box">
                    <div class="label">Active Users</div>
                    <div class="value">${data.users.filter(u => u.status === 'active').length}</div>
                </div>
                <div class="stat-box">
                    <div class="label">Avg Uploads/User</div>
                    <div class="value">${data.totalUsers ? Math.round(data.totalImages / data.totalUsers) : 0}</div>
                </div>
            </div>

            <h2>Users (${data.users.length})</h2>
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Email</th>
                        <th>Uploads</th>
                        <th>Status</th>
                        <th>Join Date</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.users.slice(0, 50).map(u => `
                        <tr>
                            <td>${u.name}</td>
                            <td>${u.email}</td>
                            <td>${u.uploads}</td>
                            <td>${u.status}</td>
                            <td>${u.joinDate ? new Date(u.joinDate).toLocaleDateString() : 'N/A'}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>

            <h2>Recent Uploads (${Math.min(data.images.length, 30)})</h2>
            <table>
                <thead>
                    <tr>
                        <th>Filename</th>
                        <th>User</th>
                        <th>Technical</th>
                        <th>Aesthetic</th>
                        <th>Blurry</th>
                        <th>Duplicate</th>
                        <th>Uploaded</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.images.slice(0, 30).map(img => `
                        <tr>
                            <td>${img.filename}</td>
                            <td>${img.userEmail}</td>
                            <td>${img.technicalScore}</td>
                            <td>${img.aestheticScore}</td>
                            <td>${img.isBlurry ? '⚠️ Yes' : 'No'}</td>
                            <td>${img.isDuplicate ? '⚠️ Yes' : 'No'}</td>
                            <td>${img.uploadedAt ? new Date(img.uploadedAt).toLocaleDateString() : 'N/A'}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>

            <div class="footer">
                <p>PicPicky Admin Dashboard - Confidential Report | Generated ${new Date().toLocaleString()}</p>
            </div>
        </body>
        </html>
    `);

    printWindow.document.close();
    setTimeout(() => printWindow.print(), 500);

    showNotification('PDF export initiated - save as PDF in print dialog', 'info');
}

// ─────────────────────────────────────────
// Modal
// ─────────────────────────────────────────
function showModal(title, content) {
    const existing = document.getElementById('adminModal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.id = 'adminModal';
    modal.className = 'fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4';
    modal.innerHTML = `
        <div class="glass-card max-w-4xl w-full p-8 rounded-2xl animate-scale-in max-h-[90vh] overflow-y-auto custom-scrollbar">
            <div class="flex justify-between items-center mb-6">
                <h2 class="text-2xl font-bold text-on-surface">${title}</h2>
                <button onclick="closeModal()" class="text-on-surface-variant hover:text-on-surface transition-colors p-1">
                    <span class="material-symbols-outlined">close</span>
                </button>
            </div>
            <div>${content}</div>
        </div>
    `;

    document.body.appendChild(modal);
    modal.addEventListener('click', e => {
        if (e.target === modal) closeModal();
    });
}

function closeModal() {
    const modal = document.getElementById('adminModal');
    if (modal) modal.remove();
}

// ─────────────────────────────────────────
// Notifications
// ─────────────────────────────────────────
function showNotification(message, type = 'info') {
    const existing = document.querySelectorAll('.admin-notification');
    existing.forEach(n => n.remove());

    const notification = document.createElement('div');
    notification.className = `admin-notification fixed top-24 right-8 z-[200] px-6 py-4 rounded-xl shadow-2xl animate-slide-in flex items-center gap-3 ${
        type === 'success' ? 'bg-green-500/20 border border-green-500/30 text-green-400' :
        type === 'error' ? 'bg-red-500/20 border border-red-500/30 text-red-400' :
        'bg-primary/20 border border-primary/30 text-primary'
    }`;

    notification.innerHTML = `
        <span class="material-symbols-outlined text-xl" style="font-variation-settings: 'FILL' 1;">${
            type === 'success' ? 'check_circle' :
            type === 'error' ? 'error' :
            'info'
        }</span>
        <span class="font-medium text-sm">${message}</span>
    `;

    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3500);
}

// ─────────────────────────────────────────
// Auto Refresh (every 30 seconds)
// ─────────────────────────────────────────
function startAutoRefresh() {
    if (autoRefreshInterval) clearInterval(autoRefreshInterval);

    autoRefreshInterval = setInterval(async () => {
        try {
            const [metrics, activity, alerts] = await Promise.all([
                fetchMetrics(),
                fetchActivity(currentDateRange.start, currentDateRange.end),
                fetchAlerts()
            ]);

            if (metrics) updateMetrics(metrics);
            if (activity) {
                window.activityData = activity;
                renderActivityTable();
            }
            if (alerts) {
                window.alertsData = alerts;
                renderAlerts();
            }

            console.log('✅ Dashboard auto-refreshed');

        } catch (error) {
            console.error('Auto-refresh error:', error);
        }
    }, 30000);
}

function stopAutoRefresh() {
    if (autoRefreshInterval) clearInterval(autoRefreshInterval);
}

// ─────────────────────────────────────────
// CSS Animations
// ─────────────────────────────────────────
const style = document.createElement('style');
style.textContent = `
    @keyframes scale-in {
        from { transform: scale(0.92); opacity: 0; }
        to { transform: scale(1); opacity: 1; }
    }
    @keyframes slide-in {
        from { transform: translateX(110%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    .animate-scale-in { animation: scale-in 0.2s ease-out; }
    .animate-slide-in { animation: slide-in 0.3s ease-out; }
`;
document.head.appendChild(style);

// ─────────────────────────────────────────
// Cleanup
// ─────────────────────────────────────────
window.addEventListener('beforeunload', stopAutoRefresh);

// ─────────────────────────────────────────
// Init
// ─────────────────────────────────────────
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeDashboard);
} else {
    initializeDashboard();
}