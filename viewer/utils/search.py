"""Full-text search utilities using SQLite FTS5 with language support."""
import sqlite3
from pathlib import Path
from typing import Optional

from .markdown_parser import extract_title, extract_excerpt


SKIP_EXTENSIONS = {
    ".pyc", ".o", ".so", ".dylib", ".class", ".exe",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
    ".pdf", ".zip", ".tar", ".gz", ".bz2",
    ".pkl", ".npy", ".npz", ".h5", ".hdf5",
    ".db", ".sqlite", ".sqlite3",
    ".woff", ".woff2", ".ttf", ".eot",
}


def create_fts_table(db_path: Path):
    """Create FTS5 virtual table for full-text search."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Drop existing table to recreate
    cursor.execute("DROP TABLE IF EXISTS search_fts")

    # Create FTS5 virtual table with content_type column
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS search_fts USING fts5(
            language,
            content_type,
            topic,
            filename,
            title,
            content,
            tokenize='unicode61'
        )
    """)

    conn.commit()
    conn.close()


def build_search_index(content_dir: Path, db_path: Path, lang: str = "ko"):
    """Build or rebuild the search index for a specific language."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Delete existing lesson entries for this language
    cursor.execute("DELETE FROM search_fts WHERE language = ? AND content_type = 'lesson'", (lang,))

    # Index all markdown files for this language
    count = 0
    for topic_dir in content_dir.iterdir():
        if not topic_dir.is_dir() or topic_dir.name.startswith("."):
            continue

        topic = topic_dir.name
        for md_file in topic_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                title = extract_title(content) or md_file.stem
                cursor.execute(
                    "INSERT INTO search_fts (language, content_type, topic, filename, title, content) VALUES (?, ?, ?, ?, ?, ?)",
                    (lang, "lesson", topic, md_file.name, title, content),
                )
                count += 1
            except Exception as e:
                print(f"Error indexing {md_file}: {e}")

    conn.commit()
    conn.close()
    print(f"Search index built: {count} lessons for {lang}.")


def build_example_index(examples_dir: Path, db_path: Path):
    """Build or rebuild the search index for example code files."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Delete existing example entries
    cursor.execute("DELETE FROM search_fts WHERE content_type = 'example'")

    count = 0
    for topic_dir in examples_dir.iterdir():
        if not topic_dir.is_dir() or topic_dir.name.startswith("."):
            continue

        topic = topic_dir.name
        for filepath in topic_dir.rglob("*"):
            if not filepath.is_file():
                continue
            if filepath.suffix in SKIP_EXTENSIONS:
                continue
            if "__pycache__" in str(filepath) or ".DS_Store" in filepath.name:
                continue

            try:
                content = filepath.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue

            rel_path = filepath.relative_to(topic_dir)
            try:
                cursor.execute(
                    "INSERT INTO search_fts (language, content_type, topic, filename, title, content) VALUES (?, ?, ?, ?, ?, ?)",
                    ("example", "example", topic, str(rel_path), filepath.name, content),
                )
                count += 1
            except Exception as e:
                print(f"Error indexing {filepath}: {e}")

    conn.commit()
    conn.close()
    print(f"Example index built: {count} files.")


def build_exercise_index(exercises_dir: Path, db_path: Path):
    """Build or rebuild the search index for exercise files."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM search_fts WHERE content_type = 'exercise'")

    count = 0
    for topic_dir in exercises_dir.iterdir():
        if not topic_dir.is_dir() or topic_dir.name.startswith("."):
            continue

        topic = topic_dir.name
        for filepath in topic_dir.rglob("*"):
            if not filepath.is_file():
                continue
            if filepath.suffix in SKIP_EXTENSIONS:
                continue
            if "__pycache__" in str(filepath) or ".DS_Store" in filepath.name:
                continue

            try:
                content = filepath.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue

            rel_path = filepath.relative_to(topic_dir)
            try:
                cursor.execute(
                    "INSERT INTO search_fts (language, content_type, topic, filename, title, content) VALUES (?, ?, ?, ?, ?, ?)",
                    ("exercise", "exercise", topic, str(rel_path), filepath.name, content),
                )
                count += 1
            except Exception as e:
                print(f"Error indexing {filepath}: {e}")

    conn.commit()
    conn.close()
    print(f"Exercise index built: {count} files.")


def search(db_path: Path, query: str, lang: str = "ko", topic: str = "",
           content_type: str = "", limit: int = 50) -> list[dict]:
    """
    Search the index for matching documents.

    Args:
        db_path: Path to the SQLite database
        query: Search query string
        lang: Language code to search in
        topic: Optional topic filter
        content_type: Optional content type filter ('lesson', 'example', or '' for all)
        limit: Maximum number of results

    Returns:
        list of dicts with topic, filename, title, snippet, and content_type
    """
    if len(query.strip()) < 2:
        return []

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Escape special FTS5 characters
    safe_query = query.replace('"', '""')

    # Build FTS5 query: if user wraps in quotes, use phrase search; otherwise OR
    stripped = query.strip()
    if stripped.startswith('"') and stripped.endswith('"') and len(stripped) > 2:
        fts_query = f'"{safe_query}"'
    else:
        words = safe_query.split()
        if len(words) == 1:
            fts_query = f'"{words[0]}"'
        else:
            fts_query = " OR ".join(f'"{w}"' for w in words if w)

    # Build WHERE clause
    conditions = ["search_fts MATCH ?"]
    params = [fts_query]

    # Language filter: for lessons use lang; for examples/exercises use content_type; for all, OR all
    if content_type == "lesson":
        conditions.append("language = ?")
        params.append(lang)
    elif content_type == "example":
        conditions.append("content_type = 'example'")
    elif content_type == "exercise":
        conditions.append("content_type = 'exercise'")
    else:
        conditions.append("(language = ? OR content_type IN ('example', 'exercise'))")
        params.append(lang)

    if topic:
        conditions.append("topic = ?")
        params.append(topic)

    params.append(limit)
    where_clause = " AND ".join(conditions)

    try:
        cursor.execute(
            f"""
            SELECT topic, filename, title,
                   snippet(search_fts, 5, '<mark>', '</mark>', '...', 50) as snippet,
                   content_type
            FROM search_fts
            WHERE {where_clause}
            ORDER BY rank
            LIMIT ?
            """,
            params,
        )
        results = cursor.fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()

    return [
        {
            "topic": row[0],
            "filename": row[1],
            "title": row[2],
            "snippet": row[3],
            "content_type": row[4],
        }
        for row in results
    ]
