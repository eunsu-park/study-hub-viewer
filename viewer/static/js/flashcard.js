/**
 * Flashcard study session for concept SRS cards.
 */
document.addEventListener('DOMContentLoaded', function() {
    var loading = document.getElementById('flashcard-loading');
    var empty = document.getElementById('flashcard-empty');
    var container = document.getElementById('flashcard-container');
    var complete = document.getElementById('session-complete');
    var card = document.getElementById('flashcard');
    var inner = document.getElementById('flashcard-inner');
    var topicFilter = document.getElementById('topic-filter');

    if (!container) return;

    var cards = [];
    var currentIndex = 0;
    var correct = 0;
    var flipped = false;

    function loadSession() {
        loading.style.display = '';
        empty.style.display = 'none';
        container.style.display = 'none';
        complete.style.display = 'none';

        var topic = topicFilter ? topicFilter.value : '';
        var url = '/api/flashcard/session' + (topic ? '?topic=' + encodeURIComponent(topic) : '');

        fetch(url)
            .then(function(r) { return r.json(); })
            .then(function(data) {
                loading.style.display = 'none';
                cards = data.cards || [];
                currentIndex = 0;
                correct = 0;

                if (cards.length === 0) {
                    empty.style.display = '';
                } else {
                    container.style.display = '';
                    document.getElementById('total-cards').textContent = cards.length;
                    showCard();
                }
            });
    }

    function showCard() {
        if (currentIndex >= cards.length) {
            showComplete();
            return;
        }

        var c = cards[currentIndex];
        document.getElementById('card-topic').textContent = c.display_topic;
        document.getElementById('card-question').textContent = c.question;
        document.getElementById('card-question-back').textContent = c.question;
        document.getElementById('card-answer').textContent = c.answer;
        document.getElementById('current-card').textContent = currentIndex + 1;

        var pct = ((currentIndex) / cards.length) * 100;
        document.getElementById('progress-fill').style.width = pct + '%';

        flipped = false;
        inner.classList.remove('flipped');
    }

    function flipCard() {
        if (flipped) return;
        flipped = true;
        inner.classList.add('flipped');
    }

    function gradeCard(quality) {
        if (!flipped) return;

        var c = cards[currentIndex];
        if (quality >= 2) correct++;

        fetch('/api/flashcard/grade', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ card_id: c.id, quality: quality })
        }).then(function() {
            currentIndex++;
            showCard();
        });
    }

    function showComplete() {
        container.style.display = 'none';
        complete.style.display = '';
        document.getElementById('summary-total').textContent = cards.length;
        document.getElementById('summary-correct').textContent = correct;
        var pct = cards.length > 0 ? Math.round((correct / cards.length) * 100) : 0;
        document.getElementById('summary-accuracy').textContent = pct + '%';
    }

    // Event listeners
    card.addEventListener('click', function(e) {
        if (!e.target.closest('.grade-btn')) flipCard();
    });

    document.querySelectorAll('.grade-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            gradeCard(parseInt(this.dataset.quality));
        });
    });

    document.addEventListener('keydown', function(e) {
        var tag = document.activeElement.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

        if (e.key === ' ' || e.key === 'Enter') {
            e.preventDefault();
            flipCard();
        } else if (flipped && e.key >= '1' && e.key <= '4') {
            gradeCard(parseInt(e.key) - 1);
        }
    });

    if (topicFilter) {
        topicFilter.addEventListener('change', loadSession);
    }

    var restartBtn = document.getElementById('restart-btn');
    if (restartBtn) {
        restartBtn.addEventListener('click', loadSession);
    }

    loadSession();
});
