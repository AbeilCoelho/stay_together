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