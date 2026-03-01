"""Search builder: generates lunr.js-compatible JSON search index."""

import json
from pathlib import Path

from config import BuildConfig
from utils.helpers import get_topics, get_lessons
from utils.markdown_parser import extract_excerpt


class SearchBuilder:
    def __init__(self, config: BuildConfig):
        self.config = config

    def build(self):
        for lang in self.config.languages:
            self._build_index(lang)

    def _build_index(self, lang: str):
        documents = []
        topics = get_topics(self.config.content_dir, lang)

        for topic_info in topics:
            topic = topic_info["name"]
            lessons = get_lessons(self.config.content_dir, lang, topic)

            for lesson in lessons:
                md_path = self.config.content_dir / lang / topic / lesson["filename"]
                try:
                    content = md_path.read_text(encoding="utf-8")
                except Exception:
                    continue

                body = extract_excerpt(content, max_length=500)

                documents.append(
                    {
                        "id": f"{topic}/{lesson['stem']}",
                        "title": lesson["title"],
                        "topic": topic,
                        "topic_display": topic_info["display_name"],
                        "body": body,
                        "url": f"{self.config.base_url}/{lang}/{topic}/{lesson['stem']}.html",
                    }
                )

        output_dir = self.config.output_dir / "search-index"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{lang}.json"
        output_path.write_text(
            json.dumps({"documents": documents}, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"  Search index: {lang} ({len(documents)} documents)")
