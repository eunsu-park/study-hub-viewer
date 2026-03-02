"""Batch progress queries to eliminate N+1 query patterns."""
from sqlalchemy import func

from models import db, LessonRead, Bookmark


def get_batch_progress(lang: str, user_id: int | None, topics: list[dict]) -> dict[str, dict]:
    """Get reading progress for all topics in a single query.

    Args:
        lang: Language code
        user_id: Current user ID (None in single-user mode)
        topics: List of topic dicts (must have 'name' and 'lesson_count' keys)

    Returns:
        dict mapping topic_name -> {"total": int, "read": int, "percentage": int}
    """
    query = db.session.query(
        LessonRead.topic,
        func.count(LessonRead.id)
    ).filter(
        LessonRead.language == lang
    )

    if user_id is not None:
        query = query.filter(LessonRead.user_id == user_id)
    else:
        query = query.filter(LessonRead.user_id.is_(None))

    read_counts = dict(query.group_by(LessonRead.topic).all())

    progress = {}
    for topic in topics:
        name = topic["name"]
        total = topic["lesson_count"]
        read = read_counts.get(name, 0)
        progress[name] = {
            "total": total,
            "read": read,
            "percentage": round(read / total * 100) if total > 0 else 0,
        }
    return progress


def get_batch_read_status(lang: str, topic: str, user_id: int | None,
                          filenames: list[str]) -> dict[str, bool]:
    """Get read status for all lessons in a topic in a single query.

    Args:
        lang: Language code
        topic: Topic name
        user_id: Current user ID or None
        filenames: List of lesson filenames

    Returns:
        dict mapping filename -> bool (True if read)
    """
    query = LessonRead.query.filter(
        LessonRead.language == lang,
        LessonRead.topic == topic,
    )
    if user_id is not None:
        query = query.filter(LessonRead.user_id == user_id)
    else:
        query = query.filter(LessonRead.user_id.is_(None))

    read_filenames = {r.filename for r in query.all()}
    return {f: f in read_filenames for f in filenames}


def get_batch_bookmark_status(lang: str, topic: str, user_id: int | None,
                              filenames: list[str]) -> dict[str, bool]:
    """Get bookmark status for all lessons in a topic in a single query.

    Args:
        lang: Language code
        topic: Topic name
        user_id: Current user ID or None
        filenames: List of lesson filenames

    Returns:
        dict mapping filename -> bool (True if bookmarked)
    """
    query = Bookmark.query.filter(
        Bookmark.language == lang,
        Bookmark.topic == topic,
    )
    if user_id is not None:
        query = query.filter(Bookmark.user_id == user_id)
    else:
        query = query.filter(Bookmark.user_id.is_(None))

    bookmarked_filenames = {b.filename for b in query.all()}
    return {f: f in bookmarked_filenames for f in filenames}
