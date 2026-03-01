/**
 * Bookmarks page: remove bookmark with undo toast.
 */
document.addEventListener('DOMContentLoaded', function() {
    const page = document.querySelector('.bookmarks-page');
    if (!page) return;

    const lang = page.dataset.lang;

    // Create toast container
    var toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        document.body.appendChild(toastContainer);
    }

    document.querySelectorAll('.btn-remove-bookmark').forEach(btn => {
        btn.addEventListener('click', async function() {
            const item = this.closest('.bookmark-item');
            const topic = item.dataset.topic;
            const filename = item.dataset.filename;

            // Remove via API
            const response = await fetch('/api/bookmark', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ lang, topic, filename })
            });

            if (response.ok) {
                // Hide item (don't remove yet — undo needs it)
                item.style.display = 'none';
                updateCount();

                // Show undo toast
                showUndoToast(item, topic, filename);
            }
        });
    });

    function showUndoToast(item, topic, filename) {
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.innerHTML = '<span>Bookmark removed</span><button class="toast-undo">Undo</button>';

        const undoBtn = toast.querySelector('.toast-undo');
        var undone = false;

        undoBtn.addEventListener('click', async function() {
            undone = true;
            // Re-add bookmark via API
            await fetch('/api/bookmark', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ lang, topic, filename })
            });
            // Restore item visibility
            item.style.display = '';
            updateCount();
            toast.remove();
        });

        toastContainer.appendChild(toast);

        // Auto-dismiss after 5 seconds
        setTimeout(function() {
            if (!undone) {
                toast.remove();
                // Permanently remove the item from DOM
                item.remove();
                if (document.querySelectorAll('.bookmark-item').length === 0) {
                    location.reload();
                }
            }
        }, 5000);
    }

    function updateCount() {
        const visible = document.querySelectorAll('.bookmark-item:not([style*="display: none"])');
        const subtitle = document.querySelector('.header-subtitle');
        if (subtitle) {
            subtitle.textContent = visible.length + ' bookmarked lessons';
        }
    }
});
