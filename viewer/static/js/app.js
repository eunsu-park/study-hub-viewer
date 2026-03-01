/**
 * Study Viewer - Main JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // Theme Toggle
    initTheme();

    // Sidebar Toggle (Mobile)
    initSidebar();

    // Search
    initSearch();

    // Tier Filter
    initTierFilter();

    // Lesson Filter (topic page)
    initLessonFilter();

    // Topic Sort (home page)
    initTopicSort();

    // Sidebar Collapse (desktop)
    initSidebarCollapse();
});

/**
 * Theme Management
 */
function initTheme() {
    const themeToggle = document.getElementById('theme-toggle');
    const html = document.documentElement;

    // Theme already set by inline script in <head> to prevent FOUC.
    // If somehow missing, detect system preference.
    if (!html.getAttribute('data-theme')) {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        html.setAttribute('data-theme', localStorage.getItem('theme') || (prefersDark ? 'dark' : 'light'));
    }

    // Toggle theme on button click (saves to localStorage as manual override)
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const currentTheme = html.getAttribute('data-theme');
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            html.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        });
    }

    // Follow system preference changes when no manual override exists
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
        if (!localStorage.getItem('theme')) {
            html.setAttribute('data-theme', e.matches ? 'dark' : 'light');
        }
    });
}

/**
 * Sidebar Management (Mobile)
 */
function initSidebar() {
    const sidebar = document.getElementById('sidebar');
    const menuToggle = document.getElementById('menu-toggle');
    const sidebarToggle = document.getElementById('sidebar-toggle');

    function openSidebar() {
        sidebar.classList.add('open');
        document.body.style.overflow = 'hidden';
    }

    function closeSidebar() {
        sidebar.classList.remove('open');
        document.body.style.overflow = '';
    }

    // Open sidebar
    if (menuToggle) {
        menuToggle.addEventListener('click', openSidebar);
    }

    // Close sidebar
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', closeSidebar);
    }

    // Close sidebar when clicking outside
    document.addEventListener('click', function(e) {
        if (sidebar && sidebar.classList.contains('open')) {
            if (!sidebar.contains(e.target) && e.target !== menuToggle) {
                closeSidebar();
            }
        }
    });
}

/**
 * Search Functionality
 */
function initSearch() {
    const searchInput = document.querySelector('.sidebar-search input');

    if (searchInput) {
        // Debounce search
        let timeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                // Only submit if there's a value
                if (this.value.trim().length >= 2) {
                    this.form.submit();
                }
            }, 500);
        });

        // Submit on Enter (clear debounce to prevent double submit)
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && this.value.trim().length >= 2) {
                clearTimeout(timeout);
                this.form.submit();
            }
        });
    }
}

/**
 * Tier Filter
 */
function initTierFilter() {
    const filterBtns = document.querySelectorAll('.tier-filter-btn');
    if (!filterBtns.length) return;

    const tierGroups = document.querySelectorAll('.tier-group');

    // Restore saved filter
    const savedTier = localStorage.getItem('tierFilter') || 'all';
    applyTierFilter(savedTier, filterBtns, tierGroups);

    filterBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
            const tier = this.getAttribute('data-tier');
            applyTierFilter(tier, filterBtns, tierGroups);
            localStorage.setItem('tierFilter', tier);
        });
    });
}

function applyTierFilter(tier, filterBtns, tierGroups) {
    filterBtns.forEach(function(btn) {
        btn.classList.toggle('active', btn.getAttribute('data-tier') === tier);
    });

    tierGroups.forEach(function(group) {
        if (tier === 'all') {
            group.style.display = '';
        } else {
            group.style.display = group.getAttribute('data-tier') === tier ? '' : 'none';
        }
    });
}

/**
 * Sidebar Collapse (desktop: toggle between full and icon-only)
 */
function initSidebarCollapse() {
    const collapseBtn = document.getElementById('sidebar-collapse');
    const sidebar = document.getElementById('sidebar');
    if (!collapseBtn || !sidebar) return;

    // Restore saved state
    if (localStorage.getItem('sidebarCollapsed') === 'true') {
        sidebar.classList.add('collapsed');
        collapseBtn.innerHTML = '&raquo;';
    }

    collapseBtn.addEventListener('click', function() {
        sidebar.classList.toggle('collapsed');
        const isCollapsed = sidebar.classList.contains('collapsed');
        localStorage.setItem('sidebarCollapsed', isCollapsed);
        this.innerHTML = isCollapsed ? '&raquo;' : '&laquo;';
    });
}

/**
 * Lesson Filter (topic page: all/unread/read/bookmarked)
 */
function initLessonFilter() {
    const filterBtns = document.querySelectorAll('.lesson-filter-btn');
    if (!filterBtns.length) return;

    const lessons = document.querySelectorAll('.lesson-item');

    filterBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
            const filter = this.getAttribute('data-filter');

            filterBtns.forEach(function(b) {
                b.classList.toggle('active', b.getAttribute('data-filter') === filter);
            });

            lessons.forEach(function(item) {
                if (filter === 'all') {
                    item.style.display = '';
                } else if (filter === 'unread') {
                    item.style.display = item.dataset.read === 'false' ? '' : 'none';
                } else if (filter === 'read') {
                    item.style.display = item.dataset.read === 'true' ? '' : 'none';
                } else if (filter === 'bookmarked') {
                    item.style.display = item.dataset.bookmarked === 'true' ? '' : 'none';
                }
            });
        });
    });
}

/**
 * Topic Sort (home page: sort within each tier group)
 */
function initTopicSort() {
    const sortBtns = document.querySelectorAll('.topic-sort-btn');
    if (!sortBtns.length) return;

    sortBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
            var sortBy = this.getAttribute('data-sort');
            sortBtns.forEach(function(b) {
                b.classList.toggle('active', b.getAttribute('data-sort') === sortBy);
            });

            document.querySelectorAll('.topics-grid').forEach(function(grid) {
                var cards = Array.from(grid.querySelectorAll('.topic-card'));
                cards.sort(function(a, b) {
                    if (sortBy === 'name') {
                        return a.dataset.name.localeCompare(b.dataset.name);
                    } else if (sortBy === 'progress') {
                        return parseFloat(b.dataset.progress) - parseFloat(a.dataset.progress);
                    } else if (sortBy === 'lessons') {
                        return parseInt(b.dataset.lessons) - parseInt(a.dataset.lessons);
                    }
                    return 0;
                });
                cards.forEach(function(card) { grid.appendChild(card); });
            });
        });
    });
}

/**
 * bfcache: reload when navigating back to a cached page
 */
window.addEventListener('pageshow', function(e) {
    if (e.persisted) location.reload();
});

/**
 * Keyboard shortcuts
 */
document.addEventListener('keydown', function(e) {
    // Cmd/Ctrl + K for search
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.querySelector('.sidebar-search input');
        if (searchInput) {
            searchInput.focus();
        }
    }

    // Escape to close sidebar on mobile
    if (e.key === 'Escape') {
        const sidebar = document.getElementById('sidebar');
        if (sidebar && sidebar.classList.contains('open')) {
            sidebar.classList.remove('open');
        }
    }
});
