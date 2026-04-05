/**
 * Lesson page interactivity: mark-read, bookmark, copy, code blocks, scroll-to-top, keyboard nav.
 */
document.addEventListener('DOMContentLoaded', function() {
    const article = document.querySelector('.lesson-article');
    if (!article) return;

    const lang = article.dataset.lang;
    const topic = article.dataset.topic;
    const filename = article.dataset.filename;

    // Mark as read - sync all instances (icon swap handled by CSS via .active class)
    document.querySelectorAll('[data-action="mark-read"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const isRead = !this.classList.contains('active');
            const response = await fetch('/api/mark-read', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
                body: JSON.stringify({ lang, topic, filename, is_read: isRead })
            });
            if (response.ok) {
                document.querySelectorAll('[data-action="mark-read"]').forEach(b => {
                    b.classList.toggle('active', isRead);
                    b.setAttribute('aria-pressed', isRead);
                    b.querySelector('.text').textContent = isRead ? 'Read' : 'Mark as read';
                });
            }
        });
    });

    // Bookmark - sync all instances
    document.querySelectorAll('[data-action="bookmark"]').forEach(btn => {
        btn.addEventListener('click', async function() {
            const response = await fetch('/api/bookmark', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
                body: JSON.stringify({ lang, topic, filename })
            });
            if (response.ok) {
                const data = await response.json();
                document.querySelectorAll('[data-action="bookmark"]').forEach(b => {
                    b.classList.toggle('active', data.bookmarked);
                    b.setAttribute('aria-pressed', data.bookmarked);
                    b.querySelector('.text').textContent = data.bookmarked ? 'Bookmarked' : 'Bookmark';
                });
            }
        });
    });

    // Copy link - independent feedback per button
    document.querySelectorAll('[data-action="copy-link"]').forEach(btn => {
        btn.addEventListener('click', function() {
            navigator.clipboard.writeText(window.location.href);
            const textEl = this.querySelector('.text');
            const originalText = textEl.textContent;
            textEl.textContent = 'Copied!';
            setTimeout(() => { textEl.textContent = originalText; }, 2000);
        });
    });

    // Add copy buttons to code blocks
    document.querySelectorAll('pre code').forEach((block) => {
        const pre = block.parentNode;
        const wrapper = document.createElement('div');
        wrapper.className = 'code-block-wrapper';
        pre.parentNode.insertBefore(wrapper, pre);
        wrapper.appendChild(pre);

        const copyBtn = document.createElement('button');
        copyBtn.className = 'code-copy-btn';
        copyBtn.textContent = 'Copy';
        copyBtn.addEventListener('click', () => {
            navigator.clipboard.writeText(block.textContent);
            copyBtn.textContent = 'Copied!';
            setTimeout(() => copyBtn.textContent = 'Copy', 2000);
        });
        wrapper.appendChild(copyBtn);
    });

    // Scroll to top button
    const scrollBtn = document.getElementById('scroll-to-top');
    if (scrollBtn) {
        window.addEventListener('scroll', function() {
            scrollBtn.classList.toggle('visible', window.scrollY > 300);
        });
        scrollBtn.addEventListener('click', function() {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // Cloze deletion: click or Enter/Space to reveal hidden text
    (function initCloze() {
        document.querySelectorAll('.cloze').forEach(function(el) {
            function toggle() {
                el.classList.toggle('revealed');
            }
            el.addEventListener('click', toggle);
            el.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    toggle();
                }
            });
        });
    })();

    // Create Flashcard from lesson
    (function initCreateCard() {
        document.querySelectorAll('[data-action="create-card"]').forEach(function(btn) {
            btn.addEventListener('click', function() {
                var selection = window.getSelection().toString().trim();

                // Build modal
                var modal = document.createElement('div');
                modal.className = 'create-card-modal';
                modal.innerHTML =
                    '<div class="create-card-modal__content">' +
                    '<h3>Create Flashcard</h3>' +
                    '<label for="card-question">Question (front)</label>' +
                    '<textarea id="card-question" rows="3" placeholder="What is...?"></textarea>' +
                    '<label for="card-answer">Answer (back)</label>' +
                    '<textarea id="card-answer" rows="3" placeholder="The answer...">' +
                    (selection || '') + '</textarea>' +
                    '<div class="create-card-modal__actions">' +
                    '<button class="btn" id="card-cancel">Cancel</button>' +
                    '<button class="btn btn-read active" id="card-save">Save</button>' +
                    '</div></div>';

                document.body.appendChild(modal);

                document.getElementById('card-cancel').addEventListener('click', function() {
                    modal.remove();
                });

                modal.addEventListener('click', function(e) {
                    if (e.target === modal) modal.remove();
                });

                document.getElementById('card-save').addEventListener('click', function() {
                    var q = document.getElementById('card-question').value.trim();
                    var a = document.getElementById('card-answer').value.trim();
                    if (!q || !a) return;

                    fetch('/api/flashcard/create', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCsrfToken()
                        },
                        body: JSON.stringify({
                            question: q,
                            answer: a,
                            topic: topic,
                            filename: filename
                        })
                    }).then(function(r) { return r.json(); })
                    .then(function(data) {
                        if (data.success) {
                            modal.remove();
                            // Brief feedback
                            btn.querySelector('.text').textContent = 'Saved!';
                            setTimeout(function() {
                                btn.querySelector('.text').textContent = 'Flashcard';
                            }, 2000);
                        } else {
                            alert(data.error || 'Failed to save card');
                        }
                    });
                });

                // Focus question input
                document.getElementById('card-question').focus();
            });
        });
    })();

    // Reading position memory (localStorage)
    (function initReadingPosition() {
        var key = 'reading-pos:' + topic + '/' + filename;
        var saved = localStorage.getItem(key);

        // Restore position after a short delay so the page is fully rendered
        if (saved) {
            var pos = JSON.parse(saved);
            // Only restore if user hasn't finished (not at top, not fully read)
            if (pos.scrollY > 100) {
                requestAnimationFrame(function() {
                    window.scrollTo(0, pos.scrollY);
                });
            }
        }

        // Debounced save on scroll
        var saveTimer = null;
        window.addEventListener('scroll', function() {
            if (saveTimer) clearTimeout(saveTimer);
            saveTimer = setTimeout(function() {
                localStorage.setItem(key, JSON.stringify({
                    scrollY: window.scrollY,
                    ts: Date.now()
                }));
            }, 300);
        });

        // Clean up old entries (keep last 100)
        try {
            var posKeys = [];
            for (var i = 0; i < localStorage.length; i++) {
                var k = localStorage.key(i);
                if (k && k.startsWith('reading-pos:')) posKeys.push(k);
            }
            if (posKeys.length > 100) {
                var entries = posKeys.map(function(k) {
                    var v = JSON.parse(localStorage.getItem(k) || '{}');
                    return { key: k, ts: v.ts || 0 };
                }).sort(function(a, b) { return a.ts - b.ts; });
                // Remove oldest
                entries.slice(0, entries.length - 100).forEach(function(e) {
                    localStorage.removeItem(e.key);
                });
            }
        } catch(_) {}
    })();

    // Floating TOC with scroll-spy
    (function initFloatingToc() {
        var tocNav = document.getElementById('floating-toc');
        var content = document.querySelector('.lesson-content');
        if (!tocNav || !content) return;

        var headings = content.querySelectorAll('h2, h3');
        if (headings.length < 2) return;

        // Ensure all headings have ids
        headings.forEach(function(h, i) {
            if (!h.id) h.id = 'heading-' + i;
        });

        // Build TOC HTML
        var html = '<div class="ftoc-title">On this page</div><ul>';
        headings.forEach(function(h) {
            var level = h.tagName === 'H3' ? ' class="ftoc-h3"' : '';
            html += '<li' + level + '><a href="#' + h.id + '">' + h.textContent + '</a></li>';
        });
        html += '</ul>';
        tocNav.innerHTML = html;

        var links = tocNav.querySelectorAll('a');

        // Scroll-spy via IntersectionObserver
        var activeIndex = 0;

        function setActive(index) {
            if (index === activeIndex && links[index].classList.contains('active')) return;
            links.forEach(function(a) { a.classList.remove('active'); });
            if (links[index]) {
                links[index].classList.add('active');
                activeIndex = index;
                // Scroll the TOC so the active item is visible
                links[index].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
            }
        }

        var observer = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    var idx = Array.prototype.indexOf.call(headings, entry.target);
                    if (idx !== -1) setActive(idx);
                }
            });
        }, {
            rootMargin: '-80px 0px -70% 0px',
            threshold: 0
        });

        headings.forEach(function(h) { observer.observe(h); });

        // Smooth scroll on click
        tocNav.addEventListener('click', function(e) {
            var link = e.target.closest('a');
            if (!link) return;
            e.preventDefault();
            var target = document.getElementById(link.getAttribute('href').slice(1));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });

        setActive(0);
    })();

    // Keyboard shortcuts: <- -> for lesson navigation
    document.addEventListener('keydown', function(e) {
        const tag = document.activeElement.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

        if (e.key === 'ArrowLeft') {
            const prevLink = document.querySelector('.nav-prev');
            if (prevLink) { prevLink.click(); }
        } else if (e.key === 'ArrowRight') {
            const nextLink = document.querySelector('.nav-next');
            if (nextLink) { nextLink.click(); }
        }
    });
});
