self.addEventListener('push', function (event) {
    if (event.data) {
        const data = event.data.json();
        const options = {
            body: data.body,
            icon: '/static/icon.png', // Add a 192x192 icon to static folder later
            vibrate: [200, 100, 200]
        };
        event.waitUntil(self.registration.showNotification(data.title, options));
    }
});

self.addEventListener('notificationclick', function (event) {
    event.notification.close();
    event.waitUntil(clients.openWindow('/'));
});

// Global fetch wrapper with CSRF injection
async function secureFetch(url, options = {}) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    const headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,  // Mandatory for Flask-WTF
        ...(options.headers || {})
    };

    return fetch(url, { ...options, headers });
}

// Fetch Widget Data periodically
async function updateWidget() {
    const res = await secureFetch('/api/ephemeral/widget');
    const data = await res.json();
    document.getElementById('secret-count').innerText = data.unread_count;
}
setInterval(updateWidget, 60000); // Check every minute