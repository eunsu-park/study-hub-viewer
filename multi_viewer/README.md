# Multi-User Study Viewer

Study Hub의 다중 사용자 웹 뷰어. 개인용 `viewer/`를 기반으로 사용자 인증과 유저별 데이터 격리를 추가한 서버 운영용 애플리케이션.

Multi-user web viewer for Study Hub. Based on the personal `viewer/`, with added user authentication and per-user data isolation for server deployment.

## Tech Stack

| Component | Choice | Notes |
|-----------|--------|-------|
| Framework | Flask 3.x | Server-rendered, Jinja2 templates |
| Database | SQLite + WAL mode | Sufficient for 10 users |
| Auth | Flask-Login + bcrypt | Session-based, cookie auth |
| CSRF | Flask-WTF CSRFProtect | Form + API protection |
| WSGI | Gunicorn | Multi-worker production server |
| Reverse Proxy | Nginx | Static file serving, HTTPS |

## Project Structure

```
multi_viewer/
├── app.py              # Flask app (auth integration, user-scoped queries)
├── auth.py             # Auth Blueprint (login/logout, CLI commands)
├── config.py           # Configuration (security settings)
├── forms.py            # WTForms (LoginForm)
├── models.py           # SQLAlchemy models (User, LessonRead, Bookmark)
├── requirements.txt    # Python dependencies
├── gunicorn.conf.py    # Gunicorn production config
├── nginx.conf.example  # Nginx reverse proxy example
├── .env.example        # Environment variable template
├── templates/
│   ├── base.html       # Base layout (CSRF meta, user UI)
│   ├── auth/
│   │   └── login.html  # Login page
│   ├── index.html      # Home (conditional progress display)
│   ├── topic.html      # Topic page (conditional progress bar)
│   ├── lesson.html     # Lesson page (conditional action buttons)
│   ├── dashboard.html  # Dashboard (login required)
│   ├── bookmarks.html  # Bookmarks (login required)
│   └── ...
├── static/
│   ├── css/style.css   # Styles (+ auth page styles)
│   └── js/
│       ├── app.js      # getCsrfToken() utility
│       ├── lesson.js   # CSRF headers on fetch
│       ├── bookmarks.js
│       └── dashboard.js
└── utils/              # Shared utilities (copied from viewer/)
    ├── markdown_parser.py
    ├── search.py
    ├── examples.py
    └── exercises.py
```

## Access Control

| Route | Anonymous | Logged In |
|-------|-----------|-----------|
| Content (index, topic, lesson) | Read only, no progress | Progress + bookmarks displayed |
| Search, examples, exercises | Full access | Full access |
| Dashboard, bookmarks page | Redirect to login | Per-user data |
| API (mark-read, bookmark) | 401 Unauthorized | User-scoped |

## Setup

### 1. Install Dependencies

```bash
cd multi_viewer
pip install -r requirements.txt
```

### 2. Initialize Database

```bash
export FLASK_APP=app.py
flask init-db        # Create tables
flask build-index    # Build FTS5 search index
```

### 3. Create User

No registration page — users are created via CLI only.

```bash
flask create-user --username alice --display-name "Alice"
# Password will be prompted interactively

flask list-users     # List all users
```

### 4. Run Development Server

```bash
flask run --port 5051
# http://127.0.0.1:5051
```

Port 5051 is used to avoid conflict with `viewer/` (port 5050).

## Production Deployment

### Environment Variables

```bash
cp .env.example .env
# Edit .env:
#   SECRET_KEY=<random 32+ byte hex string>
#   FLASK_ENV=production
```

Generate a secret key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Gunicorn

```bash
gunicorn -c gunicorn.conf.py app:app
# Binds to 127.0.0.1:5051, auto-detects worker count
```

### Nginx

```bash
sudo cp nginx.conf.example /etc/nginx/sites-available/study-viewer
sudo ln -s /etc/nginx/sites-available/study-viewer /etc/nginx/sites-enabled/
# Edit server_name and paths as needed
sudo nginx -t && sudo systemctl reload nginx
```

See `nginx.conf.example` for HTTPS configuration (Let's Encrypt).

## Differences from viewer/

| Feature | viewer/ (personal) | multi_viewer/ (multi-user) |
|---------|--------------------|-----------------------------|
| Auth | None | Flask-Login + bcrypt |
| Data scope | Global (single user) | Per-user (user_id FK) |
| CSRF | None | Flask-WTF CSRFProtect |
| Session | None | Signed cookie (HttpOnly, SameSite) |
| User creation | N/A | CLI only (`flask create-user`) |
| Port | 5050 | 5051 |
| Deployment | `flask run` | Gunicorn + Nginx |

## Security

- bcrypt password hashing (12 rounds)
- HttpOnly, SameSite=Lax session cookies
- CSRF protection on all forms and API endpoints
- Parameterized SQL queries (SQLAlchemy ORM)
- Production: `SECRET_KEY` required via env var, `SESSION_COOKIE_SECURE=True`
