"""Example builder: generates syntax-highlighted code viewer pages."""

import shutil
from pathlib import Path

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, TextLexer
from jinja2 import Environment, FileSystemLoader

from config import BuildConfig
from utils.helpers import (
    get_example_topics,
    should_skip_file,
    format_file_size,
    get_lexer_name,
)


class ExampleBuilder:
    def __init__(self, config: BuildConfig):
        self.config = config
        self.env = Environment(
            loader=FileSystemLoader(str(config.template_dir)),
            autoescape=False,
        )
        self.formatter = HtmlFormatter(
            linenos="inline",
            cssclass="highlight",
            wrapcode=True,
        )

    def build(self):
        if not self.config.examples_dir.is_dir():
            return

        self._build_examples_index()
        topics = get_example_topics(self.config.examples_dir)

        for topic in topics:
            topic_dir = self.config.examples_dir / topic
            files = self._collect_files(topic_dir, topic)
            if files:
                self._build_topic_index(topic, files)
                for file_info in files:
                    self._build_example_page(file_info)
                    self._copy_raw_file(file_info)

    def _collect_files(self, topic_dir: Path, topic: str) -> list[dict]:
        """Collect all processable files in a topic's examples directory."""
        files = []
        for filepath in sorted(topic_dir.rglob("*")):
            if not filepath.is_file():
                continue
            if should_skip_file(filepath):
                continue

            rel_path = filepath.relative_to(self.config.examples_dir)
            sub_path = filepath.relative_to(topic_dir)
            lexer_name = get_lexer_name(filepath)

            files.append(
                {
                    "path": filepath,
                    "rel_path": str(rel_path),
                    "sub_path": str(sub_path),
                    "name": filepath.name,
                    "topic": topic,
                    "topic_display": topic.replace("_", " "),
                    "language": lexer_name,
                    "lexer_name": lexer_name,
                }
            )
        return files

    def _build_examples_index(self):
        """Build the main examples index page."""
        template = self.env.get_template("examples_index.html")
        topics = []

        for topic_name in get_example_topics(self.config.examples_dir):
            topic_dir = self.config.examples_dir / topic_name
            file_count = sum(
                1
                for f in topic_dir.rglob("*")
                if f.is_file() and not should_skip_file(f)
            )
            topics.append(
                {
                    "name": topic_name,
                    "display_name": topic_name.replace("_", " "),
                    "file_count": file_count,
                }
            )

        html = template.render(
            topics=topics,
            lang="en",
            languages=self.config.language_list,
            base_url=self.config.base_url,
            page_type="examples",
        )
        html = "{% raw %}\n" + html + "\n{% endraw %}"

        output_path = self.config.output_dir / "examples" / "index.html"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")

    def _build_topic_index(self, topic: str, files: list[dict]):
        """Build per-topic example index page."""
        template = self.env.get_template("examples_topic.html")

        html = template.render(
            topic=topic,
            topic_display=topic.replace("_", " "),
            files=files,
            lang="en",
            languages=self.config.language_list,
            base_url=self.config.base_url,
            page_type="examples",
        )
        html = "{% raw %}\n" + html + "\n{% endraw %}"

        output_path = self.config.output_dir / "examples" / topic / "index.html"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")

    def _build_example_page(self, file_info: dict):
        """Generate a syntax-highlighted viewer page for a single file."""
        template = self.env.get_template("example.html")

        try:
            content = file_info["path"].read_text(encoding="utf-8", errors="replace")
        except Exception:
            content = "# Unable to read file"

        try:
            lexer = get_lexer_by_name(file_info["lexer_name"])
        except Exception:
            lexer = TextLexer()

        highlighted = highlight(content, lexer, self.formatter)
        line_count = content.count("\n") + 1
        file_size = format_file_size(file_info["path"].stat().st_size)

        # Raw file URL (relative to the .html viewer page)
        raw_url = file_info["name"]

        html = template.render(
            filename=file_info["name"],
            topic=file_info["topic"],
            topic_display=file_info["topic_display"],
            highlighted_code=highlighted,
            raw_url=raw_url,
            language=file_info["language"],
            line_count=line_count,
            file_size=file_size,
            lang="en",
            languages=self.config.language_list,
            base_url=self.config.base_url,
            page_type="examples",
        )
        html = "{% raw %}\n" + html + "\n{% endraw %}"

        output_path = (
            self.config.output_dir / "examples" / file_info["rel_path"]
        ).with_suffix(
            file_info["path"].suffix + ".html"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")

    def _copy_raw_file(self, file_info: dict):
        """Copy the raw file for download."""
        output_path = self.config.output_dir / "examples" / file_info["rel_path"]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_info["path"], output_path)
