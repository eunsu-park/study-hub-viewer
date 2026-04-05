"""Backlink index: detect cross-topic references in lesson content."""
import re
from functools import lru_cache
from pathlib import Path


def _scan_topic_mentions(text: str, topic_names: set[str], own_topic: str) -> set[str]:
    """Find which other topic names are mentioned in the text."""
    mentioned = set()
    text_lower = text.lower()
    for topic in topic_names:
        if topic == own_topic:
            continue
        # Match topic name with underscores replaced by spaces, case-insensitive
        display = topic.replace("_", " ").lower()
        # Also match the original underscore form
        if display in text_lower or topic.lower() in text_lower:
            mentioned.add(topic)
    return mentioned


def build_backlink_index(content_dir: Path, lang: str) -> dict[str, list[dict]]:
    """
    Build a reverse index of cross-topic references.

    Returns:
        dict mapping topic_name -> list of {topic, filename, title} that reference it.
    """
    lang_dir = content_dir / lang
    if not lang_dir.exists():
        return {}

    # Collect all topic names
    topic_names = {
        d.name for d in lang_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    }

    # Forward scan: for each lesson, which topics does it mention?
    forward = {}  # (topic, filename) -> set of mentioned topics
    titles = {}   # (topic, filename) -> title

    for topic_dir in sorted(lang_dir.iterdir()):
        if not topic_dir.is_dir() or topic_dir.name.startswith("."):
            continue
        for md_file in sorted(topic_dir.glob("*.md")):
            text = md_file.read_text(encoding="utf-8")
            # Extract title
            m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
            title = m.group(1).strip() if m else md_file.stem.replace("_", " ")
            key = (topic_dir.name, md_file.name)
            titles[key] = title
            mentions = _scan_topic_mentions(text, topic_names, topic_dir.name)
            if mentions:
                forward[key] = mentions

    # Build reverse index
    reverse: dict[str, list[dict]] = {}
    for (src_topic, src_file), mentioned_topics in forward.items():
        for target_topic in mentioned_topics:
            if target_topic not in reverse:
                reverse[target_topic] = []
            reverse[target_topic].append({
                "topic": src_topic,
                "filename": src_file,
                "title": titles[(src_topic, src_file)],
                "display_topic": src_topic.replace("_", " "),
            })

    # Sort each list by topic then filename
    for topic in reverse:
        reverse[topic].sort(key=lambda x: (x["topic"], x["filename"]))

    return reverse


# Cached version with mtime-based invalidation
@lru_cache(maxsize=4)
def _build_backlink_index_cached(content_dir_str: str, lang: str, mtime: float) -> dict:
    return build_backlink_index(Path(content_dir_str), lang)


def get_backlinks(content_dir: Path, lang: str, topic: str) -> list[dict]:
    """Get lessons from other topics that reference the given topic."""
    lang_dir = content_dir / lang
    if not lang_dir.exists():
        return []
    mtime = lang_dir.stat().st_mtime
    index = _build_backlink_index_cached(str(content_dir), lang, mtime)
    return index.get(topic, [])
