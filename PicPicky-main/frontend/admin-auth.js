// admin-auth.js

function checkAdminAuth() {
    const adminSession = sessionStorage.getItem('adminSession');

    if (!adminSession) {
        window.location.href = 'login.html';
        return false;
    }

    try {
        const adminData = JSON.parse(adminSession);
        updateAdminInfo(adminData);
        return true;
    } catch (error) {
        sessionStorage.removeItem('adminSession');
        window.location.href = 'login.html';
        return false;
    }
}

// ✅ FIXED - uses getElementById instead of fragile class selectors
function updateAdminInfo(adminData) {
    const adminNameElement = document.getElementById('adminName');
    const adminRoleElement = document.getElementById('adminRole');

    if (adminNameElement) {
        adminNameElement.textContent = adminData.name || 'Admin';
    }
    if (adminRoleElement) {
        adminRoleElement.textContent = (adminData.role || 'Admin').toUpperCase();
    }
}

function logout() {
    sessionStorage.removeItem('adminSession');
    window.location.href = 'login.html';
}

// ✅ Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', checkAdminAuth);
} else {
    checkAdminAuth();
}