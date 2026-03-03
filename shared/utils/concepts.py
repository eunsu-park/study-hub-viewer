"""Concept extraction and indexing utilities.

Extracts concept terms from H2/H3 headings in lesson markdown files and builds
a reverse index mapping concept -> [topic, lesson] occurrences.

Shared by both viewer/ and site/.
"""

import re
from pathlib import Path

# Structural headings that are navigation scaffolding, not concept terms.
SKIP_HEADINGS: frozenset[str] = frozenset({
    # Lesson structure
    "learning objectives", "summary", "practice problems", "practice",
    "next steps", "prerequisites", "introduction", "conclusion",
    "references", "further reading", "review questions", "overview",
    "getting started", "setup", "installation", "exercises", "exercise",
    "review", "key takeaways", "additional resources", "key terms",
    "key concepts", "what we covered", "what you will learn",
    "hands-on exercises", "quiz", "self-check", "recap", "resources",
    # Overview file sections
    "table of contents", "file list", "learning roadmap", "learning path",
    "recommended learning path", "online resources", "related resources",
    "related topics", "practice exercises", "practice environment",
    # Generic pedagogical
    "definition", "implementation", "concept", "comparison", "basic usage",
    "the problem", "key points", "example", "examples", "best practices",
    "common patterns", "advanced topics", "advanced usage", "basic operations",
    "common operations", "configuration", "architecture", "advantages",
    "disadvantages", "pros and cons", "use cases", "features", "syntax",
    "core concepts", "fundamentals", "basics", "practical examples",
    "when to use", "troubleshooting", "debugging", "testing", "performance",
    "security", "monitoring", "deployment", "extensions", "plugins",
    "how it works", "why it matters", "real-world applications",
    "python implementation", "c implementation", "code example",
    "step-by-step implementation", "project overview", "key features",
    "main options", "quick reference", "cheat sheet", "common mistakes",
    "strengths", "weaknesses", "structure", "schema", "principles",
    "core idea", "principle", "characteristics", "example code",
    "basic structure", "comparison table", "common pitfalls", "motivation",
    "navigation", "properties", "project structure", "visual explanation",
    "mathematical formulation", "common errors", "mathematical foundation",
    "quick start", "advanced features", "integration", "workflow",
    "visualization", "optimization", "evaluation", "limitations",
    "preparation", "tools and resources", "environment setup",
    "key differences", "performance optimization", "practical considerations",
    "core principles", "error handling", "formal definition",
    "practical applications", "when to use each", "putting it all together",
    "basic commands", "practical patterns", "the idea",
    "performance comparison", "comparison summary", "basic concepts",
    "version management", "basic setup", "statement",
    "when to use which", "basic syntax", "performance considerations",
    "summary table", "key properties", "security best practices",
    "installation and setup", "model comparison", "derivation",
    "mitigation strategies", "algorithm comparison", "selection criteria",
    "basic principle", "proof sketch", "physical interpretation",
})

# Regex to strip numeric prefixes: "3.", "4.1", "3.2.1" from headings
_NUMERIC_PREFIX_RE = re.compile(r"^\d+(?:\.\d+)*\.?\s+")


def extract_concepts(content: str, skip: frozenset[str] = SKIP_HEADINGS) -> list[dict]:
    """Extract concept terms from H2/H3 headings in markdown content.

    Returns a list of dicts: [{"term": "Gradient Descent", "term_lower": "gradient descent"}, ...]
    """
    results: list[dict] = []
    seen: set[str] = set()

    for line in content.splitlines():
        m = re.match(r"^(#{2,3})\s+(.+)$", line)
        if not m:
            continue

        raw = m.group(2).strip()
        # Strip trailing anchor links {#id}
        raw = re.sub(r"\s*\{[^}]+\}$", "", raw).strip()
        # Strip numeric prefix
        term = _NUMERIC_PREFIX_RE.sub("", raw).strip()
        if not term or len(term) < 4:
            continue

        term_lower = term.lower()
        if term_lower in skip or term_lower in seen:
            continue

        seen.add(term_lower)
        results.append({"term": term, "term_lower": term_lower})

    return results


def build_concept_index(content_dir: Path, lang: str) -> dict[str, dict]:
    """Scan all lesson files and build a reverse concept index.

    Args:
        content_dir: Root content directory (contains en/, ko/ subdirs).
        lang: Language code ('en' or 'ko').

    Returns:
        Alphabetically sorted dict:
        {
            "gradient descent": {
                "term": "Gradient Descent",
                "occurrences": [
                    {"topic": "Machine_Learning", "topic_display": "Machine Learning",
                     "filename": "02_LR.md", "lesson_title": "Linear Regression"},
                    ...
                ],
            },
            ...
        }
    """
    from .markdown_parser import extract_title

    lang_dir = content_dir / lang
    if not lang_dir.is_dir():
        return {}

    index: dict[str, dict] = {}

    for topic_dir in sorted(lang_dir.iterdir()):
        if not topic_dir.is_dir() or topic_dir.name.startswith("."):
            continue
        topic = topic_dir.name
        topic_display = topic.replace("_", " ")

        for md_file in sorted(topic_dir.glob("*.md")):
            # Skip overview files (structural, not concept-rich)
            if md_file.name.startswith("00_"):
                continue

            try:
                content = md_file.read_text(encoding="utf-8")
            except Exception:
                continue

            lesson_title = extract_title(content) or md_file.stem.replace("_", " ")
            concepts = extract_concepts(content)

            for concept in concepts:
                key = concept["term_lower"]
                if key not in index:
                    index[key] = {
                        "term": concept["term"],
                        "occurrences": [],
                    }
                index[key]["occurrences"].append({
                    "topic": topic,
                    "topic_display": topic_display,
                    "filename": md_file.name,
                    "lesson_title": lesson_title,
                })

    return dict(sorted(index.items()))
