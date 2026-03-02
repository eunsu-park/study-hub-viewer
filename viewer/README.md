# Study Viewer (Web Viewer / 웹 뷰어)

A unified Flask-based Markdown study material viewer with optional multi-user authentication.

Flask 기반 Markdown 학습 자료 뷰어. 선택적 다중 사용자 인증을 지원합니다.

## Features / 기능

- Markdown rendering with Pygments syntax highlighting / Markdown 렌더링 (Pygments 코드 하이라이팅)
- Full-text search (SQLite FTS5) / 전체 텍스트 검색 (SQLite FTS5)
- Learning progress tracking / 학습 진행률 추적
- Bookmarks / 북마크
- Dark/Light mode / 다크/라이트 모드
- Multilingual support (Korean/English) / 다국어 지원 (한국어/영어)
- Unified top/bottom lesson toolbar (navigation + action buttons) / 레슨 상/하단 통합 툴바 (네비게이션 + 액션 버튼)
- Keyboard shortcuts (←/→ lesson navigation) / 키보드 단축키 (←/→ 레슨 이동)
- Scroll-to-top floating button / 맨 위로 스크롤 플로팅 버튼
- Optional multi-user auth (Flask-Login + bcrypt) / 선택적 다중 사용자 인증

## Auth Modes / 인증 모드

Controlled by `AUTH_ENABLED` environment variable (.env or shell).

`AUTH_ENABLED` 환경변수로 전환합니다.

| Mode | AUTH_ENABLED | Login UI | Progress/Bookmarks |
|------|-------------|----------|-------------------|
| Single-user (default) | `false` | Hidden | Always available (user_id=NULL) |
| Multi-user | `true` | Shown | Login required (per-user data) |

## Installation & Running / 설치 및 실행

### Single-user mode (default) / 단일 사용자 모드

```bash
cd viewer
pip install -r requirements.txt

flask init-db          # Initialize database
flask build-index      # Build search index
flask run --port 5050  # http://127.0.0.1:5050
```

### Multi-user mode / 다중 사용자 모드

```bash
cd viewer
pip install -r requirements.txt
cp .env.example .env
# Edit .env: AUTH_ENABLED=true, set SECRET_KEY

AUTH_ENABLED=true flask init-db
AUTH_ENABLED=true flask build-index
AUTH_ENABLED=true flask create-user --username admin
AUTH_ENABLED=true flask run --port 5050
```

### Production (Gunicorn) / 프로덕션

```bash
cp .env.example .env
# Edit .env: AUTH_ENABLED=true, SECRET_KEY=<random>, FLASK_ENV=production

gunicorn -c gunicorn.conf.py app:app
```

### DB Migration / DB 마이그레이션

Existing single-user databases can be migrated to the unified schema:

기존 단일 사용자 DB를 통합 스키마로 마이그레이션:

```bash
python migrate_db.py
```

## Project Structure / 프로젝트 구조

```
viewer/
├── app.py              # Flask main app (AUTH_ENABLED toggle)
├── auth.py             # Auth Blueprint (login/logout, CLI commands)
├── config.py           # Configuration + security settings
├── models.py           # User, LessonRead, Bookmark (user_id nullable)
├── forms.py            # WTForms (LoginForm)
├── progress.py         # Batch query helpers (N+1 optimized)
├── build_index.py      # Search index builder
├── migrate_db.py       # DB migration script
├── gunicorn.conf.py    # Gunicorn production config
├── requirements.txt    # Dependencies
├── .env.example        # Environment variable template
├── data.db             # SQLite DB (auto-generated)
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── topic.html
│   ├── lesson.html
│   ├── search.html
│   ├── dashboard.html
│   ├── bookmarks.html
│   └── auth/login.html
└── static/
    ├── css/
    └── js/
```

Shared utilities are in `../shared/utils/` (markdown_parser, search, examples, exercises).

## API Endpoints / API 엔드포인트

| Method / 메서드 | Path / 경로 | Description / 설명 |
|-----------------|-------------|-------------------|
| GET | `/<lang>/` | Topic list / 토픽 목록 |
| GET | `/<lang>/topic/<name>` | Lesson list / 레슨 목록 |
| GET | `/<lang>/topic/<name>/lesson/<file>` | Lesson content / 레슨 내용 |
| GET | `/<lang>/search?q=<query>` | Search / 검색 |
| GET | `/<lang>/dashboard` | Progress dashboard / 진행률 대시보드 |
| GET | `/<lang>/bookmarks` | Bookmark list / 북마크 목록 |
| POST | `/api/mark-read` | Mark as read / 읽음 표시 |
| POST | `/api/bookmark` | Toggle bookmark / 북마크 토글 |

> When `AUTH_ENABLED=true`, POST endpoints require authentication and `X-CSRFToken` header.

## Dependencies / 의존성

- Flask 3.x
- Flask-SQLAlchemy
- Flask-Login (multi-user mode)
- Flask-WTF (multi-user mode)
- bcrypt (multi-user mode)
- Markdown + Pygments
- PyYAML
- Gunicorn (production)
