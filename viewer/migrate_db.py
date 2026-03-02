#!/usr/bin/env python3
"""Migrate existing viewer database to unified schema.

Adds user_id column (nullable) to lessons_read and bookmarks tables,
creates the users table, and preserves all existing data.

Usage:
    python migrate_db.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data.db"


def migrate():
    if not DB_PATH.exists():
        print("No database found. Use 'flask init-db' to create a new one.")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Check if migration is needed
    c.execute("PRAGMA table_info(lessons_read)")
    columns = {row[1] for row in c.fetchall()}
    if "user_id" in columns:
        print("Database already has user_id column. No migration needed.")
        conn.close()
        return

    print(f"Migrating database: {DB_PATH}")

    # Read existing data
    c.execute("SELECT language, topic, filename, read_at FROM lessons_read")
    reads = c.fetchall()
    print(f"  Found {len(reads)} lesson reads")

    c.execute("SELECT language, topic, filename, created_at FROM bookmarks")
    bookmarks = c.fetchall()
    print(f"  Found {len(bookmarks)} bookmarks")

    # Recreate tables with user_id column
    c.execute("DROP TABLE IF EXISTS lessons_read")
    c.execute("DROP TABLE IF EXISTS bookmarks")

    # Create users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username VARCHAR(80) UNIQUE NOT NULL,
            email VARCHAR(120) UNIQUE,
            password_hash VARCHAR(128) NOT NULL,
            display_name VARCHAR(100),
            created_at DATETIME,
            last_login_at DATETIME,
            is_active BOOLEAN DEFAULT 1
        )
    """)

    # Recreate lessons_read with user_id
    c.execute("""
        CREATE TABLE lessons_read (
            id INTEGER PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            language VARCHAR(10) NOT NULL DEFAULT 'ko',
            topic VARCHAR(100) NOT NULL,
            filename VARCHAR(200) NOT NULL,
            read_at DATETIME,
            UNIQUE(user_id, language, topic, filename)
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS ix_lessons_read_user_id ON lessons_read(user_id)")

    # Recreate bookmarks with user_id
    c.execute("""
        CREATE TABLE bookmarks (
            id INTEGER PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            language VARCHAR(10) NOT NULL DEFAULT 'ko',
            topic VARCHAR(100) NOT NULL,
            filename VARCHAR(200) NOT NULL,
            created_at DATETIME,
            UNIQUE(user_id, language, topic, filename)
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS ix_bookmarks_user_id ON bookmarks(user_id)")

    # Re-insert data with user_id=NULL (single-user mode)
    for r in reads:
        c.execute(
            "INSERT INTO lessons_read (user_id, language, topic, filename, read_at) VALUES (NULL, ?, ?, ?, ?)",
            r,
        )
    for b in bookmarks:
        c.execute(
            "INSERT INTO bookmarks (user_id, language, topic, filename, created_at) VALUES (NULL, ?, ?, ?, ?)",
            b,
        )

    conn.commit()
    conn.close()
    print(f"Migration complete. Preserved {len(reads)} reads and {len(bookmarks)} bookmarks.")


if __name__ == "__main__":
    migrate()
