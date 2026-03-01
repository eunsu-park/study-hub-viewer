/**
 * Dashboard page: clear data confirmation dialog.
 */
document.addEventListener('DOMContentLoaded', function() {
    const btnClear = document.getElementById('btn-clear-data');
    const dialog = document.getElementById('confirm-clear-dialog');
    const btnCancel = document.getElementById('btn-cancel-clear');
    const btnConfirm = document.getElementById('btn-confirm-clear');

    if (!btnClear || !dialog) return;

    btnClear.addEventListener('click', () => dialog.showModal());
    btnCancel.addEventListener('click', () => dialog.close());

    btnConfirm.addEventListener('click', async () => {
        btnConfirm.disabled = true;
        btnConfirm.textContent = 'Deleting...';

        const response = await fetch('/api/clear-user-data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
        });

        if (response.ok) {
            dialog.close();
            location.reload();
        } else {
            btnConfirm.disabled = false;
            btnConfirm.textContent = 'Delete All';
            alert('Failed to clear data. Please try again.');
        }
    });

    dialog.addEventListener('click', (e) => {
        if (e.target === dialog) dialog.close();
    });
});
