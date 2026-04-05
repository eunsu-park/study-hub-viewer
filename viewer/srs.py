"""SM-2 Spaced Repetition System for concept cards."""
from datetime import datetime, timedelta, timezone

from models import db, ConceptCard


def calculate_next_review(
    ease_factor: float,
    interval: int,
    repetitions: int,
    quality: int,
) -> dict:
    """Apply the SM-2 algorithm and return updated card state.

    Parameters
    ----------
    quality : int
        0 = Again, 1 = Hard, 2 = Good, 3 = Easy.
    """
    quality = max(0, min(3, quality))

    ef = ease_factor + (0.1 - (3 - quality) * (0.08 + (3 - quality) * 0.02))
    ef = max(ef, 1.3)

    if quality < 2:
        repetitions = 0
        interval = 1
    else:
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 6
        else:
            interval = round(interval * ef)
        repetitions += 1

    next_review = datetime.now(timezone.utc) + timedelta(days=interval)

    return {
        "ease_factor": round(ef, 4),
        "interval": interval,
        "repetitions": repetitions,
        "next_review": next_review,
    }


def get_due_cards(user_id: int | None, topic: str | None = None, limit: int = 20) -> list[ConceptCard]:
    """Get cards due for review, ordered by most overdue first."""
    now = datetime.now(timezone.utc)
    query = ConceptCard.query.filter(ConceptCard.next_review <= now)

    if user_id is not None:
        query = query.filter(ConceptCard.user_id == user_id)
    else:
        query = query.filter(ConceptCard.user_id.is_(None))

    if topic:
        query = query.filter(ConceptCard.topic == topic)

    return query.order_by(ConceptCard.next_review.asc()).limit(limit).all()


def get_new_cards(user_id: int | None, topic: str | None = None, limit: int = 10) -> list[ConceptCard]:
    """Get cards that have never been reviewed."""
    query = ConceptCard.query.filter(ConceptCard.next_review.is_(None))

    if user_id is not None:
        query = query.filter(ConceptCard.user_id == user_id)
    else:
        query = query.filter(ConceptCard.user_id.is_(None))

    if topic:
        query = query.filter(ConceptCard.topic == topic)

    return query.order_by(ConceptCard.created_at.asc()).limit(limit).all()


def get_session_cards(
    user_id: int | None,
    topic: str | None = None,
    new_limit: int = 10,
    review_limit: int = 20,
) -> list[dict]:
    """Build a study session: due cards first, then new cards."""
    due = get_due_cards(user_id, topic, limit=review_limit)
    new = get_new_cards(user_id, topic, limit=new_limit)

    cards = []
    for card in due:
        cards.append(_card_to_dict(card, "review"))
    for card in new:
        cards.append(_card_to_dict(card, "new"))
    return cards


def get_srs_stats(user_id: int | None) -> dict:
    """Get SRS statistics for the dashboard."""
    now = datetime.now(timezone.utc)
    base = ConceptCard.query
    if user_id is not None:
        base = base.filter(ConceptCard.user_id == user_id)
    else:
        base = base.filter(ConceptCard.user_id.is_(None))

    total = base.count()
    new = base.filter(ConceptCard.next_review.is_(None)).count()
    learning = base.filter(
        ConceptCard.next_review.isnot(None),
        ConceptCard.repetitions < 3,
    ).count()
    mastered = base.filter(ConceptCard.repetitions >= 3).count()
    due_today = base.filter(ConceptCard.next_review <= now).count()

    return {
        "total": total,
        "new": new,
        "learning": learning,
        "mastered": mastered,
        "due_today": due_today,
    }


def _card_to_dict(card: ConceptCard, card_type: str) -> dict:
    return {
        "type": card_type,
        "id": card.id,
        "topic": card.topic,
        "filename": card.filename,
        "question": card.question,
        "answer": card.answer,
        "ease_factor": card.ease_factor,
        "interval": card.interval,
        "repetitions": card.repetitions,
        "display_topic": card.topic.replace("_", " "),
    }
