#!/usr/bin/env python3
"""Build the full-text search index for the Study Viewer."""

import os
import sys
from pathlib import Path

# Add parent dir to path for shared/ package
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.utils.search import build_search_index, build_example_index, create_fts_table

# Paths
BASE_DIR = Path(__file__).parent
_STUDY_HUB = Path(os.environ.get("STUDY_HUB_PATH", BASE_DIR.parent))
CONTENT_DIR = _STUDY_HUB / "content"
EXAMPLES_DIR = _STUDY_HUB / "examples"
DB_PATH = BASE_DIR / "data.db"

SUPPORTED_LANGUAGES = ["ko", "en"]

if __name__ == "__main__":
    print("Building search index...")
    print(f"  Content directory: {CONTENT_DIR}")
    print(f"  Examples directory: {EXAMPLES_DIR}")
    print(f"  Database: {DB_PATH}")

    # Create FTS table and build index for all languages
    create_fts_table(DB_PATH)
    for lang in SUPPORTED_LANGUAGES:
        lang_dir = CONTENT_DIR / lang
        if lang_dir.exists():
            print(f"  Indexing {lang} lessons...")
            build_search_index(lang_dir, DB_PATH, lang=lang)

    # Index example code files
    if EXAMPLES_DIR.exists():
        print("  Indexing example code...")
        build_example_index(EXAMPLES_DIR, DB_PATH)

    print("Done!")
