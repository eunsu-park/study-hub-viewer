"""Build configuration for the static study site."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BuildConfig:
    content_dir: Path
    examples_dir: Path
    output_dir: Path
    base_url: str = "/study"
    languages: list[str] = field(default_factory=lambda: ["en", "ko"])
    language_names: dict[str, str] = field(
        default_factory=lambda: {"en": "English", "ko": "한국어"}
    )
    template_dir: Path = field(default=None)

    def __post_init__(self):
        if self.template_dir is None:
            self.template_dir = Path(__file__).parent / "templates"
        # Normalize base_url: strip trailing slash
        self.base_url = self.base_url.rstrip("/")

    @property
    def language_list(self) -> list[dict]:
        return [
            {"code": lang, "name": self.language_names[lang]}
            for lang in self.languages
        ]
