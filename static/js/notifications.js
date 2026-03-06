// Notification System
let notificationCheckInterval;

// Format notification time
function formatNotificationTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000); // difference in seconds
    
    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
    return date.toLocaleDateString();
}

// Get notification icon based on type
function getNotificationIcon(type) {
    switch(type) {
        case 'vehicle_entry':
            return '🚗';
        case 'vehicle_exit':
            return '🚪';
        case 'payment_completed':
            return '✅';
        case 'payment_failed':
            return '❌';
        default:
            return '🔔';
    }
}

// Fetch and display notifications
async function fetchNotifications() {
    try {
        const response = await fetch('/api/notifications');
        const data = await response.json();
        
        updateNotificationBadge(data.unread_count);
        updateNotificationDropdown(data.notifications);
    } catch (error) {
        console.error('Error fetching notifications:', error);
    }
}

// Update notification badge count
function updateNotificationBadge(count) {
    const badge = document.getElementById('notification-badge');
    if (badge) {
        if (count > 0) {
            badge.textContent = count > 99 ? '99+' : count;
            badge.style.display = 'flex';
        } else {
            badge.style.display = 'none';
        }
    }
}

// Update notification dropdown content
function updateNotificationDropdown(notifications) {
    const dropdown = document.getElementById('notification-dropdown');
    if (!dropdown) return;
    
    if (notifications.length === 0) {
        dropdown.innerHTML = `
            <div class="p-8 text-center text-gray-400">
                <svg class="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"></path>
                </svg>
                <p>No notifications yet</p>
            </div>
        `;
        return;
    }
    
    let html = '<div class="max-h-96 overflow-y-auto">';
    
    notifications.forEach(notif => {
        const isUnread = notif.is_read === 0;
        html += `
            <div class="notification-item ${isUnread ? 'unread' : ''}" 
                 data-id="${notif.id}"
                 onclick="markAsRead(${notif.id})">
                <div class="notification-icon">${getNotificationIcon(notif.type)}</div>
                <div class="notification-content">
                    <p class="notification-message">${notif.message}</p>
                    <span class="notification-time">${formatNotificationTime(notif.created_at)}</span>
                </div>
                ${isUnread ? '<div class="unread-dot"></div>' : ''}
            </div>
        `;
    });
    
    html += '</div>';
    
    // Add footer with "Mark all as read" button
    if (notifications.some(n => n.is_read === 0)) {
        html += `
            <div class="notification-footer">
                <button onclick="markAllAsRead()" class="mark-all-read-btn">
                    Mark all as read
                </button>
            </div>
        `;
    }
    
    dropdown.innerHTML = html;
}

// Toggle notification dropdown
function toggleNotifications() {
    const dropdown = document.getElementById('notification-dropdown');
    if (dropdown) {
        dropdown.classList.toggle('show');
        // Fetch latest notifications when opening
        if (dropdown.classList.contains('show')) {
            fetchNotifications();
        }
    }
}

// Mark single notification as read
async function markAsRead(notificationId) {
    try {
        await fetch(`/api/notifications/${notificationId}/read`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        // Refresh notifications
        fetchNotifications();
    } catch (error) {
        console.error('Error marking notification as read:', error);
    }
}

// Mark all notifications as read
async function markAllAsRead() {
    try {
        await fetch('/api/notifications/read-all', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        // Refresh notifications
        fetchNotifications();
    } catch (error) {
        console.error('Error marking all notifications as read:', error);
    }
}

// Close dropdown when clicking outside
document.addEventListener('click', function(event) {
    const notificationBtn = document.querySelector('.notification-btn');
    const dropdown = document.getElementById('notification-dropdown');
    
    if (notificationBtn && dropdown) {
        if (!notificationBtn.contains(event.target) && !dropdown.contains(event.target)) {
            dropdown.classList.remove('show');
        }
    }
});

// Initialize notification system
function initNotifications() {
    // Fetch notifications immediately
    fetchNotifications();
    
    // Set up periodic refresh (every 30 seconds)
    if (notificationCheckInterval) {
        clearInterval(notificationCheckInterval);
    }
    notificationCheckInterval = setInterval(fetchNotifications, 30000);
}

// Start notification system when page loads
document.addEventListener('DOMContentLoaded', function() {
    initNotifications();
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (notificationCheckInterval) {
        clearInterval(notificationCheckInterval);
    }
});
