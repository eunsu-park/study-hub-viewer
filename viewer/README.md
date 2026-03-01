# Study Viewer (Web Viewer / 웹 뷰어)

A Flask-based Markdown study material viewer.

Flask 기반 Markdown 학습 자료 뷰어입니다.

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

## Installation & Running / 설치 및 실행

```bash
cd viewer

# Install dependencies / 의존성 설치
pip install -r requirements.txt

# Initialize database / 데이터베이스 초기화
flask --app app init-db

# Build search index / 검색 인덱스 빌드
python build_index.py

# Run server (default port: 5000) / 서버 실행 (기본 포트: 5000)
flask run

# Change port / 포트 변경
flask run --port 5050

# Debug mode / 디버그 모드
flask run --debug --port 5050
```

Access http://127.0.0.1:5050 in your browser

브라우저에서 http://127.0.0.1:5050 접속

## Port Configuration / 포트 설정

### Method 1: Command Line Option / 방법 1: 명령줄 옵션
```bash
flask run --port 5050
```

### Method 2: Environment Variable / 방법 2: 환경 변수
```bash
export FLASK_RUN_PORT=5050
flask run
```

### Method 3: .flaskenv File / 방법 3: .flaskenv 파일
```bash
# Create viewer/.flaskenv / viewer/.flaskenv 생성
echo "FLASK_RUN_PORT=5050" > .flaskenv
flask run
```

## Project Structure / 프로젝트 구조

```
viewer/
├── app.py              # Flask main app / Flask 메인 앱
├── config.py           # Configuration / 설정
├── models.py           # SQLAlchemy models / SQLAlchemy 모델
├── build_index.py      # Search index builder / 검색 인덱스 빌드
├── requirements.txt    # Dependencies / 의존성
├── data.db             # SQLite DB (auto-generated / 자동 생성)
├── templates/          # Jinja2 templates / Jinja2 템플릿
│   ├── base.html
│   ├── index.html
│   ├── topic.html
│   ├── lesson.html
│   ├── search.html
│   ├── dashboard.html
│   └── bookmarks.html
├── static/             # Static files / 정적 파일
│   ├── css/
│   └── js/
└── utils/              # Utilities / 유틸리티
    ├── markdown_parser.py
    └── search.py
```

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

## Dependencies / 의존성

- Flask 3.x
- Flask-SQLAlchemy
- Markdown + Pygments
- python-frontmatter
