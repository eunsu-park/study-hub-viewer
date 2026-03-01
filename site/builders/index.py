"""Index builder: generates home pages, topic pages, and root redirect."""

from jinja2 import Environment, FileSystemLoader

from config import BuildConfig
from utils.helpers import (
    get_topics, get_lessons, get_example_topics,
    load_topic_metadata, get_tier_groups, get_tier_for_topic,
)


class IndexBuilder:
    def __init__(self, config: BuildConfig):
        self.config = config
        self.env = Environment(
            loader=FileSystemLoader(str(config.template_dir)),
            autoescape=False,
        )
        self._example_topics = set(get_example_topics(config.examples_dir))

    def build(self):
        for lang in self.config.languages:
            self._build_home(lang)
            self._build_topic_pages(lang)
            self._build_search_page(lang)
        self._build_root_redirect()

    def _build_home(self, lang: str):
        template = self.env.get_template("index.html")
        topics = get_topics(self.config.content_dir, lang)

        meta = load_topic_metadata(self.config.content_dir)
        tiers = meta.get("tiers", [])
        tier_groups = get_tier_groups(self.config.content_dir, topics)

        html = template.render(
            topics=topics,
            lang=lang,
            languages=self.config.language_list,
            base_url=self.config.base_url,
            page_type="index",
            tiers=tiers,
            tier_groups=tier_groups,
        )
        html = "{% raw %}\n" + html + "\n{% endraw %}"

        output_path = self.config.output_dir / lang / "index.html"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")

    def _build_topic_pages(self, lang: str):
        template = self.env.get_template("topic.html")
        topics = get_topics(self.config.content_dir, lang)

        for topic_info in topics:
            topic = topic_info["name"]
            lessons = get_lessons(self.config.content_dir, lang, topic)
            has_examples = topic in self._example_topics

            tier = get_tier_for_topic(self.config.content_dir, topic)

            html = template.render(
                topic=topic,
                display_name=topic_info["display_name"],
                lessons=lessons,
                has_examples=has_examples,
                lang=lang,
                languages=self.config.language_list,
                base_url=self.config.base_url,
                page_type="topic",
                tier=tier,
            )
            html = "{% raw %}\n" + html + "\n{% endraw %}"

            output_path = self.config.output_dir / lang / topic / "index.html"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(html, encoding="utf-8")

    def _build_search_page(self, lang: str):
        template = self.env.get_template("search.html")

        html = template.render(
            lang=lang,
            languages=self.config.language_list,
            base_url=self.config.base_url,
            page_type="search",
        )
        html = "{% raw %}\n" + html + "\n{% endraw %}"

        output_path = self.config.output_dir / lang / "search.html"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")

    def _build_root_redirect(self):
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Study Materials</title>
    <script>
        var lang = navigator.language && navigator.language.startsWith('ko') ? 'ko' : 'en';
        window.location.href = '""" + self.config.base_url + """/' + lang + '/';
    </script>
    <noscript>
        <meta http-equiv="refresh" content="0; url=""" + self.config.base_url + """/en/">
    </noscript>
</head>
<body>
    <p>Redirecting... <a href=\"""" + self.config.base_url + """/en/">English</a> | <a href=\"""" + self.config.base_url + """/ko/">한국어</a></p>
</body>
</html>"""
        output_path = self.config.output_dir / "index.html"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")
