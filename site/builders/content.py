"""Content builder: renders markdown lessons to static HTML pages."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from config import BuildConfig
from utils.helpers import get_lessons
from utils.markdown_parser import parse_markdown


class ContentBuilder:
    def __init__(self, config: BuildConfig):
        self.config = config
        self.env = Environment(
            loader=FileSystemLoader(str(config.template_dir)),
            autoescape=False,
        )

    def build(self) -> dict:
        """Build all lesson pages. Returns mapping of (lang, topic, stem) -> metadata."""
        all_lessons = {}
        for lang in self.config.languages:
            lang_dir = self.config.content_dir / lang
            if not lang_dir.is_dir():
                continue
            for topic_dir in sorted(lang_dir.iterdir()):
                if not topic_dir.is_dir() or topic_dir.name.startswith("."):
                    continue
                topic = topic_dir.name
                lessons = get_lessons(self.config.content_dir, lang, topic)
                self._build_topic_lessons(lang, topic, lessons)
                for lesson in lessons:
                    all_lessons[(lang, topic, lesson["stem"])] = lesson
        return all_lessons

    def _build_topic_lessons(self, lang: str, topic: str, lessons: list[dict]):
        template = self.env.get_template("lesson.html")
        topic_display = topic.replace("_", " ")

        for i, lesson in enumerate(lessons):
            md_path = self.config.content_dir / lang / topic / lesson["filename"]
            content = md_path.read_text(encoding="utf-8")
            parsed = parse_markdown(content)

            prev_lesson = lessons[i - 1] if i > 0 else None
            next_lesson = lessons[i + 1] if i < len(lessons) - 1 else None

            html = template.render(
                title=parsed["title"] or lesson["display_name"],
                content=parsed["html"],
                toc=parsed["toc"],
                topic=topic,
                topic_display=topic_display,
                prev_lesson=prev_lesson,
                next_lesson=next_lesson,
                lang=lang,
                languages=self.config.language_list,
                base_url=self.config.base_url,
                page_type="lesson",
            )

            # Wrap in {% raw %} for Jekyll compatibility
            html = self._wrap_raw(html)

            output_path = (
                self.config.output_dir / lang / topic / f"{lesson['stem']}.html"
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(html, encoding="utf-8")

    def _wrap_raw(self, html: str) -> str:
        """Wrap HTML in Jekyll {% raw %} tags to prevent Liquid processing."""
        return "{% raw %}\n" + html + "\n{% endraw %}"
