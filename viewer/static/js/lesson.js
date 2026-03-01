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
                headers: { 'Content-Type': 'application/json' },
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
                headers: { 'Content-Type': 'application/json' },
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
