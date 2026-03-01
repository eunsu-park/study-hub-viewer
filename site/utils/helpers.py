"""Helper functions for content discovery and URL generation."""

import re
from collections import OrderedDict
from pathlib import Path

import yaml

from utils.markdown_parser import extract_title, estimate_reading_time

_topic_metadata_cache = None


def load_topic_metadata(content_dir: Path) -> dict:
    """Load tier definitions and topic assignments from topic_metadata.yaml."""
    global _topic_metadata_cache
    if _topic_metadata_cache is not None:
        return _topic_metadata_cache

    yaml_path = content_dir / "topic_metadata.yaml"
    if not yaml_path.exists():
        _topic_metadata_cache = {"tiers": [], "topics": {}}
        return _topic_metadata_cache

    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    _topic_metadata_cache = data or {"tiers": [], "topics": {}}
    return _topic_metadata_cache


def get_tier_for_topic(content_dir: Path, topic_name: str) -> dict | None:
    """Get tier info for a single topic."""
    meta = load_topic_metadata(content_dir)
    topic_meta = meta.get("topics", {}).get(topic_name)
    if not topic_meta:
        return None
    tier_id = topic_meta.get("tier")
    for tier in meta.get("tiers", []):
        if tier["id"] == tier_id:
            return tier
    return None


def get_tier_groups(content_dir: Path, topics: list[dict]) -> OrderedDict:
    """Group topics by tier. Returns OrderedDict keyed by tier id."""
    meta = load_topic_metadata(content_dir)
    tiers = meta.get("tiers", [])
    topic_assignments = meta.get("topics", {})

    groups = OrderedDict()
    for tier in tiers:
        groups[tier["id"]] = []

    for topic in topics:
        assignment = topic_assignments.get(topic["name"])
        tier_id = assignment["tier"] if assignment else None
        if tier_id and tier_id in groups:
            groups[tier_id].append(topic)
        else:
            groups.setdefault("uncategorized", []).append(topic)

    return groups


def get_topics(content_dir: Path, lang: str) -> list[dict]:
    """Scan content/<lang>/ for topic directories and return sorted list."""
    lang_dir = content_dir / lang
    if not lang_dir.is_dir():
        return []

    topics = []
    for d in sorted(lang_dir.iterdir()):
        if d.is_dir() and not d.name.startswith("."):
            lessons = list(d.glob("*.md"))
            topics.append(
                {
                    "name": d.name,
                    "display_name": d.name.replace("_", " "),
                    "lesson_count": len(lessons),
                }
            )
    return topics


def get_lessons(content_dir: Path, lang: str, topic: str) -> list[dict]:
    """List all markdown files in a topic directory with metadata."""
    topic_dir = content_dir / lang / topic
    if not topic_dir.is_dir():
        return []

    lessons = []
    for md_file in sorted(topic_dir.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        title = extract_title(content)
        stem = md_file.stem
        display_name = stem.replace("_", " ")

        lessons.append(
            {
                "filename": md_file.name,
                "stem": stem,
                "title": title or display_name,
                "display_name": display_name,
                "reading_time": estimate_reading_time(content),
            }
        )
    return lessons


def get_example_topics(examples_dir: Path) -> list[str]:
    """Return sorted list of topic names that have example files."""
    if not examples_dir.is_dir():
        return []
    return sorted(
        d.name
        for d in examples_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )


SKIP_PATTERNS = {
    "__pycache__",
    ".DS_Store",
    ".pyc",
    ".o",
    ".so",
    ".dylib",
    ".class",
    ".exe",
}

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
    ".pdf", ".zip", ".tar", ".gz", ".bz2",
    ".pkl", ".npy", ".npz", ".h5", ".hdf5",
    ".db", ".sqlite", ".sqlite3",
    ".woff", ".woff2", ".ttf", ".eot",
}


def should_skip_file(path: Path) -> bool:
    """Check if a file should be skipped during example processing."""
    for part in path.parts:
        if part in SKIP_PATTERNS or part.endswith(".pyc"):
            return True
    return path.suffix in BINARY_EXTENSIONS


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable form."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".js": "javascript",
    ".ts": "typescript",
    ".html": "html",
    ".css": "css",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "zsh",
    ".sql": "sql",
    ".tex": "latex",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".json": "json",
    ".xml": "xml",
    ".md": "markdown",
    ".txt": "text",
    ".toml": "toml",
    ".ini": "ini",
    ".cfg": "ini",
    ".conf": "text",
    ".ino": "cpp",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".rb": "ruby",
    ".r": "r",
    ".R": "r",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".ipynb": "json",
    ".dockerfile": "docker",
    ".tf": "terraform",
}


def get_lexer_name(filepath: Path) -> str:
    """Get Pygments lexer name from file extension."""
    if filepath.name == "Makefile" or filepath.name == "makefile":
        return "makefile"
    if filepath.name == "Dockerfile":
        return "docker"
    return EXTENSION_TO_LANGUAGE.get(filepath.suffix.lower(), "text")
