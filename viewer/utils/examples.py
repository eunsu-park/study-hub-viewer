"""Example code browsing utilities."""
from pathlib import Path

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, TextLexer


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

SKIP_PATTERNS = {
    "__pycache__", ".DS_Store", ".pyc", ".o", ".so",
    ".dylib", ".class", ".exe",
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


def get_lexer_name(filepath: Path) -> str:
    """Get Pygments lexer name from file extension."""
    if filepath.name in ("Makefile", "makefile"):
        return "makefile"
    if filepath.name == "Dockerfile":
        return "docker"
    return EXTENSION_TO_LANGUAGE.get(filepath.suffix.lower(), "text")


def get_example_topics(examples_dir: Path) -> list[dict]:
    """Get list of example topics with file counts."""
    topics = []
    if not examples_dir.exists():
        return topics

    for topic_dir in sorted(examples_dir.iterdir()):
        if not topic_dir.is_dir() or topic_dir.name.startswith("."):
            continue
        files = [f for f in topic_dir.rglob("*") if f.is_file() and not should_skip_file(f)]
        topics.append({
            "name": topic_dir.name,
            "display_name": topic_dir.name.replace("_", " "),
            "file_count": len(files),
        })
    return topics


def get_example_files(topic_dir: Path) -> list[dict]:
    """Get list of files in an example topic directory (recursive)."""
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


def highlight_file(filepath: Path) -> dict:
    """Read and syntax-highlight a file. Returns dict with html, language, lines, size."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = filepath.read_text(encoding="latin-1")

    lang = get_lexer_name(filepath)
    try:
        lexer = get_lexer_by_name(lang)
    except Exception:
        lexer = TextLexer()

    formatter = HtmlFormatter(
        cssclass="highlight",
        linenos=True,
        linenostart=1,
    )
    html = highlight(content, lexer, formatter)

    return {
        "html": html,
        "raw": content,
        "language": lang,
        "lines": content.count("\n") + 1,
        "size": format_file_size(filepath.stat().st_size),
    }


def _count_lines(filepath: Path) -> int:
    """Count lines in a text file. Returns 0 for unreadable files."""
    try:
        return filepath.read_text(encoding="utf-8").count("\n") + 1
    except Exception:
        return 0
