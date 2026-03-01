"""Study Materials Web Viewer - Flask Application with Multi-language Support."""
import os
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from functools import wraps

import yaml

from flask import Flask, render_template, request, jsonify, abort, redirect, url_for, make_response
from models import db, LessonRead, Bookmark
from config import Config
from utils.markdown_parser import parse_markdown, parse_markdown_cached, extract_excerpt, estimate_reading_time
from utils.search import search, build_search_index, build_example_index, build_exercise_index, create_fts_table
from utils.examples import get_example_topics, get_example_files, highlight_file
from utils.exercises import get_exercise_topics, get_exercise_files, find_exercise_for_lesson

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db.init_app(app)

CONTENT_DIR = Config.CONTENT_DIR
EXAMPLES_DIR = Config.EXAMPLES_DIR
EXERCISES_DIR = Config.EXERCISES_DIR
SUPPORTED_LANGS = set(Config.SUPPORTED_LANGUAGES)
DEFAULT_LANG = Config.DEFAULT_LANGUAGE
LANGUAGE_NAMES = Config.LANGUAGE_NAMES


@app.template_filter("timeago")
def timeago_filter(dt):
    """Format a datetime as a relative time string."""
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m ago"
    elif seconds < 86400:
        return f"{int(seconds // 3600)}h ago"
    elif seconds < 604800:
        return f"{int(seconds // 86400)}d ago"
    else:
        return dt.strftime("%Y-%m-%d")


def get_content_dir(lang: str) -> Path:
    """Get content directory for a specific language."""
    return CONTENT_DIR / lang


def validate_lang(f):
    """Decorator to validate language parameter."""
    @wraps(f)
    def decorated_function(lang, *args, **kwargs):
        if lang not in SUPPORTED_LANGS:
            abort(404)
        return f(lang, *args, **kwargs)
    return decorated_function


_topic_metadata_cache = None


def load_topic_metadata() -> dict:
    """Load tier definitions and topic assignments from topic_metadata.yaml."""
    global _topic_metadata_cache
    if _topic_metadata_cache is not None:
        return _topic_metadata_cache

    yaml_path = CONTENT_DIR / "topic_metadata.yaml"
    if not yaml_path.exists():
        _topic_metadata_cache = {"tiers": [], "topics": {}}
        return _topic_metadata_cache

    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    _topic_metadata_cache = data or {"tiers": [], "topics": {}}
    return _topic_metadata_cache


def get_tier_for_topic(topic_name: str) -> dict | None:
    """Get tier info for a single topic. Returns None if not classified."""
    meta = load_topic_metadata()
    topic_meta = meta.get("topics", {}).get(topic_name)
    if not topic_meta:
        return None
    tier_id = topic_meta.get("tier")
    for tier in meta.get("tiers", []):
        if tier["id"] == tier_id:
            return tier
    return None


def get_tier_groups(topics: list[dict], lang: str) -> OrderedDict:
    """Group topics by tier. Returns OrderedDict keyed by tier id."""
    meta = load_topic_metadata()
    tiers = meta.get("tiers", [])
    topic_assignments = meta.get("topics", {})

    groups = OrderedDict()
    for tier in tiers:
        groups[tier["id"]] = []

    for topic in topics:
        assignment = topic_assignments.get(topic["name"])
        tier_id = assignment["tier"] if assignment else None
        if tier_id and tier_id in groups:
            groups[tier_id].append(topic)
        else:
            groups.setdefault("uncategorized", []).append(topic)

    return groups


def get_topics(lang: str) -> list[dict]:
    """Get list of all topics with lesson counts for a language."""
    content_dir = get_content_dir(lang)
    if not content_dir.exists():
        return []

    meta = load_topic_metadata()
    topic_assignments = meta.get("topics", {})

    topics = []
    for topic_dir in sorted(content_dir.iterdir()):
        if not topic_dir.is_dir() or topic_dir.name.startswith("."):
            continue
        lessons = list(topic_dir.glob("*.md"))
        topic_info = {
            "name": topic_dir.name,
            "lesson_count": len(lessons),
            "display_name": topic_dir.name.replace("_", " "),
        }
        # Inject tier info
        assignment = topic_assignments.get(topic_dir.name)
        if assignment:
            topic_info["tier"] = assignment.get("tier")
        topics.append(topic_info)
    return topics


def get_lessons(lang: str, topic: str) -> list[dict]:
    """Get list of lessons for a topic in a language."""
    topic_dir = get_content_dir(lang) / topic
    if not topic_dir.exists():
        return []

    lessons = []
    for md_file in sorted(topic_dir.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        title = extract_title_from_content(content) or md_file.stem
        lessons.append({
            "filename": md_file.name,
            "title": title,
            "display_name": md_file.stem.replace("_", " "),
            "reading_time": estimate_reading_time(content),
        })
    return lessons


def extract_title_from_content(content: str) -> str:
    """Extract first H1 from content."""
    import re
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    return match.group(1).strip() if match else ""


def get_progress(lang: str, topic: str) -> dict:
    """Get reading progress for a topic in a language."""
    lessons = get_lessons(lang, topic)
    total = len(lessons)
    read_count = LessonRead.query.filter_by(language=lang, topic=topic).count()
    return {
        "total": total,
        "read": read_count,
        "percentage": round(read_count / total * 100) if total > 0 else 0,
    }


def is_lesson_read(lang: str, topic: str, filename: str) -> bool:
    """Check if a lesson has been read."""
    return LessonRead.query.filter_by(language=lang, topic=topic, filename=filename).first() is not None


def is_bookmarked(lang: str, topic: str, filename: str) -> bool:
    """Check if a lesson is bookmarked."""
    return Bookmark.query.filter_by(language=lang, topic=topic, filename=filename).first() is not None


def get_available_languages() -> list[dict]:
    """Get list of available languages with their names."""
    return [{"code": lang, "name": LANGUAGE_NAMES.get(lang, lang)} for lang in SUPPORTED_LANGS]


# Routes
@app.route("/")
def root():
    """Root - redirect to default language."""
    lang = request.cookies.get("lang", DEFAULT_LANG)
    if lang not in SUPPORTED_LANGS:
        lang = DEFAULT_LANG
    return redirect(url_for("index", lang=lang))


@app.route("/<lang>/")
@validate_lang
def index(lang: str):
    """Home page - learning hub with stats, recent activity, and topics grid."""
    topics = get_topics(lang)
    for topic in topics:
        topic["progress"] = get_progress(lang, topic["name"])

    # Overall progress
    total_lessons = sum(t["lesson_count"] for t in topics)
    total_read = LessonRead.query.filter_by(language=lang).count()
    overall = {
        "total": total_lessons,
        "read": total_read,
        "percentage": round(total_read / total_lessons * 100) if total_lessons > 0 else 0,
    }

    # Continue learning (1~99% progress topics, max 5)
    in_progress = [t for t in topics if 0 < t["progress"]["percentage"] < 100]
    in_progress.sort(key=lambda t: t["progress"]["read"], reverse=True)

    # Recently read lessons (latest 5)
    recent_reads = LessonRead.query.filter_by(language=lang) \
        .order_by(LessonRead.read_at.desc()).limit(5).all()
    recent_items = []
    for r in recent_reads:
        lessons = get_lessons(lang, r.topic)
        info = next((l for l in lessons if l["filename"] == r.filename), None)
        if info:
            recent_items.append({
                "topic": r.topic, "filename": r.filename,
                "title": info["title"], "read_at": r.read_at,
            })

    # Recent bookmarks (latest 5)
    recent_bookmarks = Bookmark.query.filter_by(language=lang) \
        .order_by(Bookmark.created_at.desc()).limit(5).all()
    bookmark_items = []
    for b in recent_bookmarks:
        lessons = get_lessons(lang, b.topic)
        info = next((l for l in lessons if l["filename"] == b.filename), None)
        if info:
            bookmark_items.append({
                "topic": b.topic, "filename": b.filename,
                "title": info["title"],
            })

    bookmark_count = Bookmark.query.filter_by(language=lang).count()

    # Tier grouping
    meta = load_topic_metadata()
    tiers = meta.get("tiers", [])
    tier_groups = get_tier_groups(topics, lang)

    response = make_response(render_template(
        "index.html",
        topics=topics,
        lang=lang,
        languages=get_available_languages(),
        overall=overall,
        in_progress=in_progress[:5],
        recent_reads=recent_items,
        bookmarks=bookmark_items,
        bookmark_count=bookmark_count,
        tiers=tiers,
        tier_groups=tier_groups,
    ))
    response.set_cookie("lang", lang, max_age=60*60*24*365)
    return response


@app.route("/<lang>/topic/<name>")
@validate_lang
def topic(lang: str, name: str):
    """Topic page - list lessons."""
    topic_dir = get_content_dir(lang) / name
    if not topic_dir.exists():
        abort(404)

    lessons = get_lessons(lang, name)
    for lesson in lessons:
        lesson["is_read"] = is_lesson_read(lang, name, lesson["filename"])
        lesson["is_bookmarked"] = is_bookmarked(lang, name, lesson["filename"])

    progress = get_progress(lang, name)
    tier = get_tier_for_topic(name)
    has_examples = (EXAMPLES_DIR / name).is_dir()
    has_exercises = (EXERCISES_DIR / name).is_dir()
    return render_template(
        "topic.html",
        topic=name,
        display_name=name.replace("_", " "),
        lessons=lessons,
        progress=progress,
        lang=lang,
        languages=get_available_languages(),
        tier=tier,
        has_examples=has_examples,
        has_exercises=has_exercises,
    )


@app.route("/<lang>/topic/<name>/lesson/<filename>")
@validate_lang
def lesson(lang: str, name: str, filename: str):
    """Lesson page - render markdown content."""
    filepath = get_content_dir(lang) / name / filename
    if not filepath.exists():
        abort(404)

    parsed = parse_markdown_cached(str(filepath))

    # Get prev/next lessons for navigation
    lessons = get_lessons(lang, name)
    current_idx = next(
        (i for i, l in enumerate(lessons) if l["filename"] == filename), -1
    )
    if current_idx < 0:
        prev_lesson = next_lesson = None
    else:
        prev_lesson = lessons[current_idx - 1] if current_idx > 0 else None
        next_lesson = lessons[current_idx + 1] if current_idx < len(lessons) - 1 else None

    exercise = find_exercise_for_lesson(EXERCISES_DIR, name, filename)

    return render_template(
        "lesson.html",
        topic=name,
        filename=filename,
        title=parsed["title"] or filename,
        content=parsed["html"],
        toc=parsed["toc"],
        is_read=is_lesson_read(lang, name, filename),
        is_bookmarked=is_bookmarked(lang, name, filename),
        prev_lesson=prev_lesson,
        next_lesson=next_lesson,
        exercise=exercise,
        lang=lang,
        languages=get_available_languages(),
    )


@app.route("/<lang>/search")
@validate_lang
def search_page(lang: str):
    """Search page with topic and content type filters."""
    query = request.args.get("q", "")
    topic_filter = request.args.get("topic", "")
    type_filter = request.args.get("type", "")
    results = []
    if query:
        db_path = Path(app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", ""))
        results = search(db_path, query, lang=lang, topic=topic_filter, content_type=type_filter)
    topics = get_topics(lang)
    return render_template(
        "search.html",
        query=query,
        results=results,
        topics=topics,
        topic_filter=topic_filter,
        type_filter=type_filter,
        lang=lang,
        languages=get_available_languages(),
    )


@app.route("/<lang>/dashboard")
@validate_lang
def dashboard(lang: str):
    """Dashboard page - overall progress."""
    topics = get_topics(lang)
    for topic in topics:
        topic["progress"] = get_progress(lang, topic["name"])

    # Calculate overall progress
    total_lessons = sum(t["lesson_count"] for t in topics)
    total_read = LessonRead.query.filter_by(language=lang).count()
    overall = {
        "total": total_lessons,
        "read": total_read,
        "percentage": round(total_read / total_lessons * 100) if total_lessons > 0 else 0,
    }

    return render_template(
        "dashboard.html",
        topics=topics,
        overall=overall,
        lang=lang,
        languages=get_available_languages(),
    )


@app.route("/<lang>/bookmarks")
@validate_lang
def bookmarks(lang: str):
    """Bookmarks page."""
    bookmarked = Bookmark.query.filter_by(language=lang).order_by(Bookmark.created_at.desc()).all()
    items = []
    for bm in bookmarked:
        lessons = get_lessons(lang, bm.topic)
        lesson_info = next((l for l in lessons if l["filename"] == bm.filename), None)
        if lesson_info:
            items.append({
                "topic": bm.topic,
                "filename": bm.filename,
                "title": lesson_info["title"],
                "created_at": bm.created_at,
            })
    return render_template(
        "bookmarks.html",
        bookmarks=items,
        lang=lang,
        languages=get_available_languages(),
    )


# Example Routes
@app.route("/<lang>/examples")
@validate_lang
def examples_index(lang: str):
    """Examples index - list all example topics."""
    topics = get_example_topics(EXAMPLES_DIR)
    total_files = sum(t["file_count"] for t in topics)
    return render_template(
        "examples_index.html",
        topics=topics,
        total_files=total_files,
        lang=lang,
        languages=get_available_languages(),
    )


@app.route("/<lang>/examples/<topic_name>")
@validate_lang
def examples_topic(lang: str, topic_name: str):
    """Examples topic - list files in a topic."""
    topic_dir = EXAMPLES_DIR / topic_name
    if not topic_dir.exists():
        abort(404)
    files = get_example_files(topic_dir)
    return render_template(
        "examples_topic.html",
        topic=topic_name,
        display_name=topic_name.replace("_", " "),
        files=files,
        lang=lang,
        languages=get_available_languages(),
    )


@app.route("/<lang>/examples/<topic_name>/<path:filepath>")
@validate_lang
def example_view(lang: str, topic_name: str, filepath: str):
    """Example file viewer with syntax highlighting."""
    full_path = EXAMPLES_DIR / topic_name / filepath
    if not full_path.exists() or not full_path.is_file():
        abort(404)
    highlighted = highlight_file(full_path)
    return render_template(
        "example_file.html",
        topic=topic_name,
        display_name=topic_name.replace("_", " "),
        filepath=filepath,
        filename=full_path.name,
        highlighted=highlighted,
        lang=lang,
        languages=get_available_languages(),
    )


@app.route("/raw/examples/<topic_name>/<path:filepath>")
def example_raw(topic_name: str, filepath: str):
    """Serve raw example file for download."""
    from flask import send_from_directory
    topic_dir = EXAMPLES_DIR / topic_name
    if not (topic_dir / filepath).exists():
        abort(404)
    return send_from_directory(topic_dir, filepath, as_attachment=True)


# Exercise Routes
def _find_related_lesson(lang: str, topic_name: str, exercise_filepath: str) -> dict | None:
    """Find lesson matching exercise by numeric prefix."""
    import re
    prefix_match = re.match(r"^(\d+)_", Path(exercise_filepath).name)
    if not prefix_match:
        return None
    prefix = prefix_match.group(1)
    lessons = get_lessons(lang, topic_name)
    for lesson_item in lessons:
        if lesson_item["filename"].startswith(f"{prefix}_"):
            return lesson_item
    return None


@app.route("/<lang>/exercises")
@validate_lang
def exercises_index(lang: str):
    """Exercises index - list all exercise topics."""
    topics = get_exercise_topics(EXERCISES_DIR)
    total_files = sum(t["file_count"] for t in topics)
    return render_template(
        "exercises_index.html",
        topics=topics,
        total_files=total_files,
        lang=lang,
        languages=get_available_languages(),
    )


@app.route("/<lang>/exercises/<topic_name>")
@validate_lang
def exercises_topic(lang: str, topic_name: str):
    """Exercises topic - list files in a topic."""
    topic_dir = EXERCISES_DIR / topic_name
    if not topic_dir.exists():
        abort(404)
    files = get_exercise_files(topic_dir)
    return render_template(
        "exercises_topic.html",
        topic=topic_name,
        display_name=topic_name.replace("_", " "),
        files=files,
        lang=lang,
        languages=get_available_languages(),
    )


@app.route("/<lang>/exercises/<topic_name>/<path:filepath>")
@validate_lang
def exercise_file_view(lang: str, topic_name: str, filepath: str):
    """Exercise file viewer with syntax highlighting."""
    full_path = EXERCISES_DIR / topic_name / filepath
    if not full_path.exists() or not full_path.is_file():
        abort(404)
    highlighted = highlight_file(full_path)
    related_lesson = _find_related_lesson(lang, topic_name, filepath)
    return render_template(
        "exercise_file.html",
        topic=topic_name,
        display_name=topic_name.replace("_", " "),
        filepath=filepath,
        filename=full_path.name,
        highlighted=highlighted,
        related_lesson=related_lesson,
        lang=lang,
        languages=get_available_languages(),
    )


@app.route("/raw/exercises/<topic_name>/<path:filepath>")
def exercise_raw(topic_name: str, filepath: str):
    """Serve raw exercise file for download."""
    from flask import send_from_directory
    topic_dir = EXERCISES_DIR / topic_name
    if not (topic_dir / filepath).exists():
        abort(404)
    return send_from_directory(topic_dir, filepath, as_attachment=True)


# API Routes
@app.route("/api/mark-read", methods=["POST"])
def api_mark_read():
    """Mark a lesson as read/unread."""
    data = request.get_json()
    lang = data.get("lang", DEFAULT_LANG)
    topic = data.get("topic")
    filename = data.get("filename")
    is_read = data.get("is_read", True)

    if lang not in SUPPORTED_LANGS:
        return jsonify({"error": "Unsupported language"}), 400
    if not topic or not filename:
        return jsonify({"error": "Missing topic or filename"}), 400

    existing = LessonRead.query.filter_by(language=lang, topic=topic, filename=filename).first()

    if is_read and not existing:
        lesson_read = LessonRead(language=lang, topic=topic, filename=filename)
        db.session.add(lesson_read)
        db.session.commit()
    elif not is_read and existing:
        db.session.delete(existing)
        db.session.commit()

    return jsonify({"success": True, "is_read": is_read})


@app.route("/api/bookmark", methods=["POST"])
def api_bookmark():
    """Add or remove a bookmark."""
    data = request.get_json()
    lang = data.get("lang", DEFAULT_LANG)
    topic = data.get("topic")
    filename = data.get("filename")

    if lang not in SUPPORTED_LANGS:
        return jsonify({"error": "Unsupported language"}), 400
    if not topic or not filename:
        return jsonify({"error": "Missing topic or filename"}), 400

    existing = Bookmark.query.filter_by(language=lang, topic=topic, filename=filename).first()

    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({"success": True, "bookmarked": False})
    else:
        bookmark = Bookmark(language=lang, topic=topic, filename=filename)
        db.session.add(bookmark)
        db.session.commit()
        return jsonify({"success": True, "bookmarked": True})


@app.route("/api/clear-user-data", methods=["POST"])
def api_clear_user_data():
    """Delete all reading history and bookmarks."""
    deleted_reads = LessonRead.query.delete()
    deleted_bookmarks = Bookmark.query.delete()
    db.session.commit()
    return jsonify({
        "success": True,
        "deleted_reads": deleted_reads,
        "deleted_bookmarks": deleted_bookmarks,
    })


@app.route("/api/search")
def api_search():
    """Search API endpoint."""
    query = request.args.get("q", "")
    lang = request.args.get("lang", DEFAULT_LANG)
    topic_filter = request.args.get("topic", "")
    type_filter = request.args.get("type", "")
    if not query:
        return jsonify({"results": []})

    db_path = Path(app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", ""))
    results = search(db_path, query, lang=lang, topic=topic_filter, content_type=type_filter)
    return jsonify({"results": results})


@app.route("/api/set-language", methods=["POST"])
def api_set_language():
    """Set preferred language."""
    data = request.get_json()
    lang = data.get("lang", DEFAULT_LANG)

    if lang not in SUPPORTED_LANGS:
        return jsonify({"error": "Unsupported language"}), 400

    response = jsonify({"success": True, "lang": lang})
    response.set_cookie("lang", lang, max_age=60*60*24*365)
    return response


# CLI Commands
@app.cli.command("init-db")
def init_db():
    """Initialize the database."""
    with app.app_context():
        db.create_all()
        db_path = Path(app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", ""))
        create_fts_table(db_path)
        print("Database initialized.")


@app.cli.command("build-index")
def build_index():
    """Build the search index for all languages and examples."""
    db_path = Path(app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", ""))
    for lang in SUPPORTED_LANGS:
        lang_content_dir = get_content_dir(lang)
        if lang_content_dir.exists():
            print(f"Building index for {lang}...")
            build_search_index(lang_content_dir, db_path, lang=lang)
    # Index example code files
    if EXAMPLES_DIR.exists():
        print("Building example code index...")
        build_example_index(EXAMPLES_DIR, db_path)
    # Index exercise files
    if EXERCISES_DIR.exists():
        print("Building exercise index...")
        build_exercise_index(EXERCISES_DIR, db_path)
    print("Search index built for all languages, examples, and exercises.")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
