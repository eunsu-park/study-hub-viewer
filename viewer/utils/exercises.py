"""Exercise browsing utilities."""
import re
from pathlib import Path

from .examples import (
    should_skip_file,
    format_file_size,
    get_lexer_name,
    _count_lines,
)


def get_exercise_topics(exercises_dir: Path) -> list[dict]:
    """Get list of exercise topics with file counts."""
    topics = []
    if not exercises_dir.exists():
        return topics

    for topic_dir in sorted(exercises_dir.iterdir()):
        if not topic_dir.is_dir() or topic_dir.name.startswith("."):
            continue
        files = [f for f in topic_dir.rglob("*") if f.is_file() and not should_skip_file(f)]
        topics.append({
            "name": topic_dir.name,
            "display_name": topic_dir.name.replace("_", " "),
            "file_count": len(files),
        })
    return topics


def get_exercise_files(topic_dir: Path) -> list[dict]:
    """Get list of exercise files for a topic."""
    files = []
    if not topic_dir.exists():
        return files

    for filepath in sorted(topic_dir.rglob("*")):
        if not filepath.is_file() or should_skip_file(filepath):
            continue
        rel_path = filepath.relative_to(topic_dir)
        files.append({
            "path": str(rel_path),
            "name": filepath.name,
            "language": get_lexer_name(filepath),
            "size": format_file_size(filepath.stat().st_size),
            "lines": _count_lines(filepath),
            "subdir": str(rel_path.parent) if rel_path.parent != Path(".") else None,
        })
    return files


def find_exercise_for_lesson(exercises_dir: Path, topic: str, lesson_filename: str) -> dict | None:
    """Find exercise file matching a lesson by numeric prefix.

    E.g. lesson '05_Gradient_Descent.md' matches exercise '05_gradient_descent.py'.
    Returns dict with path and name, or None.
    """
    prefix_match = re.match(r"^(\d+)_", lesson_filename)
    if not prefix_match:
        return None

    prefix = prefix_match.group(1)
    topic_dir = exercises_dir / topic
    if not topic_dir.is_dir():
        return None

    for filepath in topic_dir.iterdir():
        if filepath.is_file() and filepath.name.startswith(f"{prefix}_") and not should_skip_file(filepath):
            return {
                "path": filepath.name,
                "name": filepath.name,
            }
    return None
