"""Database models for progress tracking and bookmarks with multi-language support."""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class LessonRead(db.Model):
    """Track which lessons have been read."""
    __tablename__ = "lessons_read"

    id = db.Column(db.Integer, primary_key=True)
    language = db.Column(db.String(10), nullable=False, default="ko")
    topic = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    read_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("language", "topic", "filename", name="unique_lesson"),
    )

    def __repr__(self):
        return f"<LessonRead {self.language}/{self.topic}/{self.filename}>"


class Bookmark(db.Model):
    """Bookmarked lessons."""
    __tablename__ = "bookmarks"

    id = db.Column(db.Integer, primary_key=True)
    language = db.Column(db.String(10), nullable=False, default="ko")
    topic = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("language", "topic", "filename", name="unique_bookmark"),
    )

    def __repr__(self):
        return f"<Bookmark {self.language}/{self.topic}/{self.filename}>"
