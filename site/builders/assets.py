"""Asset builder: copies CSS, JS, and vendor files to output."""

import shutil
from pathlib import Path

from config import BuildConfig


class AssetBuilder:
    def __init__(self, config: BuildConfig):
        self.config = config
        # Locate viewer static relative to this file (site/builders/ -> viewer/static)
        self.viewer_static = Path(__file__).resolve().parent.parent.parent / "viewer" / "static"

    def build(self):
        self._copy_css()
        self._copy_js()
        self._vendor_lunr()

    def _copy_css(self):
        css_out = self.config.output_dir / "static" / "css"
        css_out.mkdir(parents=True, exist_ok=True)

        # Copy style.css and highlight.css as-is from viewer
        for name in ("style.css", "highlight.css"):
            src = self.viewer_static / "css" / name
            if src.exists():
                shutil.copy2(src, css_out / name)

    def _copy_js(self):
        js_out = self.config.output_dir / "static" / "js"
        js_out.mkdir(parents=True, exist_ok=True)

        # Write adapted app.js (sidebar search submits removed, search.js handles it)
        app_js = self._get_adapted_app_js()
        (js_out / "app.js").write_text(app_js, encoding="utf-8")

        # Write search.js
        search_js = self._get_search_js()
        (js_out / "search.js").write_text(search_js, encoding="utf-8")

        # Copy graph.js from viewer
        graph_src = self.viewer_static / "js" / "graph.js"
        if graph_src.exists():
            shutil.copy2(graph_src, js_out / "graph.js")

    def _vendor_lunr(self):
        """Write a bundled lunr.min.js. We embed it directly to avoid CDN dependency."""
        js_out = self.config.output_dir / "static" / "js"
        js_out.mkdir(parents=True, exist_ok=True)

        # Check if lunr.min.js already exists (may have been placed manually)
        lunr_path = js_out / "lunr.min.js"
        if lunr_path.exists():
            return

        # Write a placeholder that will be replaced by actual lunr.js
        # The build script will download it if missing
        lunr_path.write_text(
            "// lunr.js placeholder - run: curl -o static/js/lunr.min.js "
            "https://unpkg.com/lunr@2.3.9/lunr.min.js\n",
            encoding="utf-8",
        )

    def _get_adapted_app_js(self) -> str:
        return """/**
 * Study Materials - Main JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    initTheme();
    initSidebar();
    initTierFilter();
});

/**
 * Theme Management
 */
function initTheme() {
    var themeToggle = document.getElementById('theme-toggle');
    var html = document.documentElement;

    // Theme already set by inline script in <head> to prevent FOUC.
    // If somehow missing, detect system preference.
    if (!html.getAttribute('data-theme')) {
        var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        html.setAttribute('data-theme', localStorage.getItem('theme') || (prefersDark ? 'dark' : 'light'));
    }

    // Toggle theme on button click
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            var currentTheme = html.getAttribute('data-theme');
            var newTheme = currentTheme === 'light' ? 'dark' : 'light';
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
    var sidebar = document.getElementById('sidebar');
    var menuToggle = document.getElementById('menu-toggle');
    var sidebarToggle = document.getElementById('sidebar-toggle');

    function openSidebar() {
        sidebar.classList.add('open');
        document.body.style.overflow = 'hidden';
    }

    function closeSidebar() {
        sidebar.classList.remove('open');
        document.body.style.overflow = '';
    }

    if (menuToggle) {
        menuToggle.addEventListener('click', openSidebar);
    }

    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', closeSidebar);
    }

    document.addEventListener('click', function(e) {
        if (sidebar && sidebar.classList.contains('open')) {
            if (!sidebar.contains(e.target) && e.target !== menuToggle) {
                closeSidebar();
            }
        }
    });
}

/**
 * Tier Filter
 */
function initTierFilter() {
    var filterBtns = document.querySelectorAll('.tier-filter-btn');
    if (!filterBtns.length) return;

    var tierGroups = document.querySelectorAll('.tier-group');

    var savedTier = localStorage.getItem('tierFilter') || 'all';
    applyTierFilter(savedTier, filterBtns, tierGroups);

    filterBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
            var tier = this.getAttribute('data-tier');
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
        var searchInput = document.getElementById('search-sidebar-input');
        if (searchInput) {
            searchInput.focus();
        }
    }

    // Escape to close sidebar on mobile
    if (e.key === 'Escape') {
        var sidebar = document.getElementById('sidebar');
        if (sidebar && sidebar.classList.contains('open')) {
            sidebar.classList.remove('open');
            document.body.style.overflow = '';
        }
    }
});
"""

    def _get_search_js(self) -> str:
        return """/**
 * Client-side search using lunr.js
 */

var searchIndex = null;
var searchDocuments = null;

function initSearch(lang, baseUrl) {
    var input = document.getElementById('search-input');
    var resultsDiv = document.getElementById('search-results');
    if (!input || !resultsDiv) return;

    // Load search index
    fetch(baseUrl + '/search-index/' + lang + '.json')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            searchDocuments = {};
            data.documents.forEach(function(doc) {
                searchDocuments[doc.id] = doc;
            });

            searchIndex = lunr(function() {
                this.ref('id');
                this.field('title', { boost: 10 });
                this.field('topic', { boost: 5 });
                this.field('body');
                var self = this;
                data.documents.forEach(function(doc) { self.add(doc); });
            });

            // Check URL for initial query
            var params = new URLSearchParams(window.location.search);
            var q = params.get('q');
            if (q) {
                input.value = q;
                performSearch(q, resultsDiv);
            }
        })
        .catch(function(err) {
            console.error('Failed to load search index:', err);
        });

    // Debounced search on input
    var timeout;
    input.addEventListener('input', function() {
        clearTimeout(timeout);
        var value = this.value.trim();
        timeout = setTimeout(function() {
            if (value.length >= 2) {
                performSearch(value, resultsDiv);
                var url = new URL(window.location);
                url.searchParams.set('q', value);
                history.replaceState(null, '', url);
            } else {
                resultsDiv.innerHTML = '<div class="search-hint"><p>Enter a search term to find lessons across all topics.</p></div>';
            }
        }, 300);
    });

    // Submit sidebar search form to search page
    var sidebarForm = document.getElementById('search-form');
    if (sidebarForm) {
        sidebarForm.addEventListener('submit', function(e) {
            var sidebarInput = document.getElementById('search-sidebar-input');
            if (sidebarInput && sidebarInput.value.trim().length >= 2) {
                // Let the form submit normally to search.html
                return true;
            }
            e.preventDefault();
            return false;
        });
    }
}

function performSearch(query, resultsDiv) {
    if (!searchIndex) return;

    var results;
    try {
        results = searchIndex.search(query);
    } catch (e) {
        // If lunr query parsing fails, try as a simple term
        try {
            results = searchIndex.search(query.replace(/[:\\~\\^\\+\\-]/g, ' '));
        } catch (e2) {
            results = [];
        }
    }

    if (results.length === 0) {
        resultsDiv.innerHTML =
            '<p class="results-count">0 results for "' + escapeHtml(query) + '"</p>' +
            '<div class="no-results"><p>No results found. Try different keywords.</p></div>';
        return;
    }

    var html = '<p class="results-count">' + results.length + ' results for "' + escapeHtml(query) + '"</p>';
    html += '<div class="results-list">';
    results.forEach(function(result) {
        var doc = searchDocuments[result.ref];
        if (!doc) return;
        var snippet = generateSnippet(doc.body, query);
        html += '<a href="' + doc.url + '" class="result-item">' +
            '<div class="result-header">' +
            '<span class="result-topic">' + escapeHtml(doc.topic_display) + '</span>' +
            '<h3 class="result-title">' + escapeHtml(doc.title) + '</h3>' +
            '</div>' +
            '<p class="result-snippet">' + snippet + '</p>' +
            '</a>';
    });
    html += '</div>';
    resultsDiv.innerHTML = html;
}

function generateSnippet(body, query) {
    if (!body) return '';
    var terms = query.toLowerCase().split(/\\s+/);
    var lowerBody = body.toLowerCase();
    var bestPos = 0;
    for (var i = 0; i < terms.length; i++) {
        var idx = lowerBody.indexOf(terms[i]);
        if (idx !== -1) { bestPos = idx; break; }
    }
    var start = Math.max(0, bestPos - 60);
    var end = Math.min(body.length, bestPos + 200);
    var snippet = (start > 0 ? '...' : '') + body.slice(start, end) + (end < body.length ? '...' : '');
    snippet = escapeHtml(snippet);
    for (var j = 0; j < terms.length; j++) {
        if (terms[j].length < 2) continue;
        var regex = new RegExp('(' + escapeRegex(terms[j]) + ')', 'gi');
        snippet = snippet.replace(regex, '<mark>$1</mark>');
    }
    return snippet;
}

function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
}

function escapeRegex(str) {
    return str.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
}
"""
