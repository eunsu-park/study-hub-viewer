"""Study Materials Web Viewer - Unified Flask Application.

Supports both single-user (AUTH_ENABLED=false) and multi-user (AUTH_ENABLED=true) modes.
"""
import os
import re
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from functools import lru_cache, wraps
from pathlib import Path
from types import SimpleNamespace

import yaml

from flask import Flask, render_template, request, jsonify, abort, redirect, url_for, make_response

# Add parent dir to path so shared/ package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import db, User, LessonRead, Bookmark
from config import Config
from progress import get_batch_progress, get_batch_read_status, get_batch_bookmark_status
from shared.utils.markdown_parser import parse_markdown, parse_markdown_cached, extract_excerpt, estimate_reading_time
from shared.utils.search import search, build_search_index, build_example_index, build_exercise_index, create_fts_table
from shared.utils.examples import get_example_topics, get_example_files, highlight_file
from shared.utils.exercises import get_exercise_topics, get_exercise_files, find_exercise_for_lesson

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db.init_app(app)

AUTH_ENABLED = app.config.get("AUTH_ENABLED", False)

# Conditional auth initialization
if AUTH_ENABLED:
    from flask_login import current_user, login_required
    from flask_wtf.csrf import CSRFProtect
    from auth import auth_bp, login_manager, register_cli

    login_manager.init_app(app)
    csrf = CSRFProtect(app)
    app.register_blueprint(auth_bp)
    register_cli(app)

    # Enable SQLite WAL mode for concurrent reads
    with app.app_context():
        from sqlalchemy import text
        with db.engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.commit()

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith("/api/"):
            return jsonify({"error": "Login required"}), 401
        return redirect(url_for("auth.login", next=request.url))

CONTENT_DIR = Config.CONTENT_DIR
EXAMPLES_DIR = Config.EXAMPLES_DIR
EXERCISES_DIR = Config.EXERCISES_DIR
SUPPORTED_LANGS = set(Config.SUPPORTED_LANGUAGES)
DEFAULT_LANG = Config.DEFAULT_LANGUAGE
LANGUAGE_NAMES = Config.LANGUAGE_NAMES


# Auth helpers
def _get_user_id():
    """Get current user ID. Returns None in single-user mode."""
    if AUTH_ENABLED:
        from flask_login import current_user as _cu
        return _cu.id if _cu.is_authenticated else None
    return None


def auth_required(f):
    """Require login only when AUTH_ENABLED=true. No-op otherwise."""
    if AUTH_ENABLED:
        from flask_login import login_required
        return login_required(f)
    return f


@app.context_processor
def inject_auth_state():
    """Make auth_enabled and current_user available in all templates."""
    ctx = {"auth_enabled": AUTH_ENABLED}
    if not AUTH_ENABLED:
        ctx["current_user"] = SimpleNamespace(is_authenticated=False)
    return ctx


# Template filters
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


# Content helpers
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
    """Get tier info for a single topic."""
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
    """Group topics by tier."""
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
        assignment = topic_assignments.get(topic_dir.name)
        if assignment:
            topic_info["tier"] = assignment.get("tier")
        topics.append(topic_info)
    return topics


@lru_cache(maxsize=128)
def _get_lessons_cached(lang: str, topic: str, dir_mtime: float) -> tuple:
    """Cached lesson list. Cache key includes dir mtime for invalidation."""
    topic_dir = get_content_dir(lang) / topic
    lessons = []
    for md_file in sorted(topic_dir.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        title = _extract_title(content) or md_file.stem
        lessons.append({
            "filename": md_file.name,
            "title": title,
            "display_name": md_file.stem.replace("_", " "),
            "reading_time": estimate_reading_time(content),
        })
    return tuple(lessons)


def get_lessons(lang: str, topic: str) -> list[dict]:
    """Get list of lessons for a topic with filesystem caching."""
    topic_dir = get_content_dir(lang) / topic
    if not topic_dir.exists():
        return []
    mtime = topic_dir.stat().st_mtime
    return [dict(l) for l in _get_lessons_cached(lang, topic, mtime)]


def _extract_title(content: str) -> str:
    """Extract first H1 from content."""
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    return match.group(1).strip() if match else ""


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
    user_id = _get_user_id()

    # Batch progress query (N+1 fix)
    progress_map = get_batch_progress(lang, user_id, topics)
    for topic in topics:
        topic["progress"] = progress_map[topic["name"]]

    # Overall progress
    total_lessons = sum(t["lesson_count"] for t in topics)
    total_read = sum(p["read"] for p in progress_map.values())
    overall = {
        "total": total_lessons,
        "read": total_read,
        "percentage": round(total_read / total_lessons * 100) if total_lessons > 0 else 0,
    }

    # Continue learning (1~99% progress topics, max 5)
    in_progress = [t for t in topics if 0 < t["progress"]["percentage"] < 100]
    in_progress.sort(key=lambda t: t["progress"]["read"], reverse=True)

    # Recently read lessons (latest 5) - batch by unique topic
    recent_items = []
    if AUTH_ENABLED:
        if user_id:
            recent_reads = LessonRead.query.filter_by(user_id=user_id, language=lang) \
                .order_by(LessonRead.read_at.desc()).limit(5).all()
        else:
            recent_reads = []
    else:
        recent_reads = LessonRead.query.filter_by(user_id=None, language=lang) \
            .order_by(LessonRead.read_at.desc()).limit(5).all()

    recent_topics = {r.topic for r in recent_reads}
    lessons_by_topic = {t: get_lessons(lang, t) for t in recent_topics}
    for r in recent_reads:
        lessons = lessons_by_topic.get(r.topic, [])
        info = next((l for l in lessons if l["filename"] == r.filename), None)
        if info:
            recent_items.append({
                "topic": r.topic, "filename": r.filename,
                "title": info["title"], "read_at": r.read_at,
            })

    # Recent bookmarks (latest 5) - batch by unique topic
    bookmark_items = []
    bookmark_count = 0
    if AUTH_ENABLED:
        if user_id:
            recent_bookmarks = Bookmark.query.filter_by(user_id=user_id, language=lang) \
                .order_by(Bookmark.created_at.desc()).limit(5).all()
            bookmark_count = Bookmark.query.filter_by(user_id=user_id, language=lang).count()
        else:
            recent_bookmarks = []
    else:
        recent_bookmarks = Bookmark.query.filter_by(user_id=None, language=lang) \
            .order_by(Bookmark.created_at.desc()).limit(5).all()
        bookmark_count = Bookmark.query.filter_by(user_id=None, language=lang).count()

    bm_topics = {b.topic for b in recent_bookmarks}
    bm_lessons_by_topic = {t: get_lessons(lang, t) for t in bm_topics if t not in lessons_by_topic}
    bm_lessons_by_topic.update(lessons_by_topic)
    for b in recent_bookmarks:
        lessons = bm_lessons_by_topic.get(b.topic, [])
        info = next((l for l in lessons if l["filename"] == b.filename), None)
        if info:
            bookmark_items.append({
                "topic": b.topic, "filename": b.filename,
                "title": info["title"],
            })

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
    user_id = _get_user_id()

    # Batch read/bookmark status (N+1 fix)
    filenames = [l["filename"] for l in lessons]
    read_status = get_batch_read_status(lang, name, user_id, filenames)
    bookmark_status = get_batch_bookmark_status(lang, name, user_id, filenames)
    for lesson_item in lessons:
        lesson_item["is_read"] = read_status[lesson_item["filename"]]
        lesson_item["is_bookmarked"] = bookmark_status[lesson_item["filename"]]

    total = len(lessons)
    read_count = sum(1 for v in read_status.values() if v)
    progress = {
        "total": total,
        "read": read_count,
        "percentage": round(read_count / total * 100) if total > 0 else 0,
    }

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
    user_id = _get_user_id()

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

    # Single-query read/bookmark check
    is_read = False
    is_bm = False
    if AUTH_ENABLED:
        if user_id:
            is_read = LessonRead.query.filter_by(
                user_id=user_id, language=lang, topic=name, filename=filename
            ).first() is not None
            is_bm = Bookmark.query.filter_by(
                user_id=user_id, language=lang, topic=name, filename=filename
            ).first() is not None
    else:
        is_read = LessonRead.query.filter_by(
            user_id=None, language=lang, topic=name, filename=filename
        ).first() is not None
        is_bm = Bookmark.query.filter_by(
            user_id=None, language=lang, topic=name, filename=filename
        ).first() is not None

    return render_template(
        "lesson.html",
        topic=name,
        filename=filename,
        title=parsed["title"] or filename,
        content=parsed["html"],
        toc=parsed["toc"],
        is_read=is_read,
        is_bookmarked=is_bm,
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
@auth_required
def dashboard(lang: str):
    """Dashboard page - overall progress."""
    topics = get_topics(lang)
    user_id = _get_user_id()

    # Batch progress query (N+1 fix)
    progress_map = get_batch_progress(lang, user_id, topics)
    for topic_item in topics:
        topic_item["progress"] = progress_map[topic_item["name"]]

    total_lessons = sum(t["lesson_count"] for t in topics)
    total_read = sum(p["read"] for p in progress_map.values())
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
@auth_required
def bookmarks(lang: str):
    """Bookmarks page."""
    user_id = _get_user_id()
    bookmarked = Bookmark.query.filter_by(user_id=user_id, language=lang) \
        .order_by(Bookmark.created_at.desc()).all()

    # Batch lesson lookup by unique topic
    unique_topics = {bm.topic for bm in bookmarked}
    lessons_by_topic = {t: get_lessons(lang, t) for t in unique_topics}

    items = []
    for bm in bookmarked:
        lessons = lessons_by_topic.get(bm.topic, [])
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
@auth_required
def api_mark_read():
    """Mark a lesson as read/unread."""
    data = request.get_json()
    lang = data.get("lang", DEFAULT_LANG)
    topic_name = data.get("topic")
    filename = data.get("filename")
    is_read = data.get("is_read", True)

    if lang not in SUPPORTED_LANGS:
        return jsonify({"error": "Unsupported language"}), 400
    if not topic_name or not filename:
        return jsonify({"error": "Missing topic or filename"}), 400

    user_id = _get_user_id()
    existing = LessonRead.query.filter_by(
        user_id=user_id, language=lang, topic=topic_name, filename=filename
    ).first()

    if is_read and not existing:
        lesson_read = LessonRead(user_id=user_id, language=lang, topic=topic_name, filename=filename)
        db.session.add(lesson_read)
        db.session.commit()
    elif not is_read and existing:
        db.session.delete(existing)
        db.session.commit()

    return jsonify({"success": True, "is_read": is_read})


@app.route("/api/bookmark", methods=["POST"])
@auth_required
def api_bookmark():
    """Add or remove a bookmark."""
    data = request.get_json()
    lang = data.get("lang", DEFAULT_LANG)
    topic_name = data.get("topic")
    filename = data.get("filename")

    if lang not in SUPPORTED_LANGS:
        return jsonify({"error": "Unsupported language"}), 400
    if not topic_name or not filename:
        return jsonify({"error": "Missing topic or filename"}), 400

    user_id = _get_user_id()
    existing = Bookmark.query.filter_by(
        user_id=user_id, language=lang, topic=topic_name, filename=filename
    ).first()

    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({"success": True, "bookmarked": False})
    else:
        bookmark = Bookmark(user_id=user_id, language=lang, topic=topic_name, filename=filename)
        db.session.add(bookmark)
        db.session.commit()
        return jsonify({"success": True, "bookmarked": True})


@app.route("/api/clear-user-data", methods=["POST"])
@auth_required
def api_clear_user_data():
    """Delete all reading history and bookmarks."""
    user_id = _get_user_id()
    deleted_reads = LessonRead.query.filter_by(user_id=user_id).delete()
    deleted_bookmarks = Bookmark.query.filter_by(user_id=user_id).delete()
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
    if EXAMPLES_DIR.exists():
        print("Building example code index...")
        build_example_index(EXAMPLES_DIR, db_path)
    if EXERCISES_DIR.exists():
        print("Building exercise index...")
        build_exercise_index(EXERCISES_DIR, db_path)
    print("Search index built for all languages, examples, and exercises.")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5050)
