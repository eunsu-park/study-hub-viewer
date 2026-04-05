# Study Hub Viewer

study-hub의 콘텐츠를 렌더링하는 Flask 기반 웹 뷰어. 이중언어 지원과 진도 추적을 제공한다.

A Flask-based web viewer that renders [study-hub](https://github.com/eunsu-park/study-hub) content with bilingual support and progress tracking.

## Prerequisites / 사전 요구사항

This repo references content from the study-hub repository. Clone it first.

이 레포는 study-hub 레포의 콘텐츠를 참조합니다. 먼저 study-hub를 clone하세요.

```bash
git clone https://github.com/eunsu-park/study-hub.git ~/repos/study-hub
git clone https://github.com/eunsu-park/study-hub-viewer.git ~/repos/study-hub-viewer
```

## Environment Setup / 환경 설정

Set the `STUDY_HUB_PATH` environment variable to point to your study-hub repo.

`STUDY_HUB_PATH` 환경변수로 study-hub 레포 경로를 지정합니다.

```bash
export STUDY_HUB_PATH=~/repos/study-hub

# Or add to .env file / 또는 .env 파일에 추가
echo 'STUDY_HUB_PATH=~/repos/study-hub' >> .env
```

> If not set, the parent directory (`../`) is used as fallback.
> 환경변수가 설정되지 않으면 상위 디렉토리(`../`)를 fallback으로 사용합니다.

---

## Running / 실행

### Single-user mode (default) / 단일 사용자 모드 (기본)

```bash
cd viewer
pip install -r requirements.txt
flask init-db && flask build-index
flask run --port 5050
# http://127.0.0.1:5050
```

### Multi-user mode / 다중 사용자 모드

```bash
cd viewer
cp .env.example .env
# Edit .env: AUTH_ENABLED=true, set SECRET_KEY

AUTH_ENABLED=true flask init-db
AUTH_ENABLED=true flask build-index
AUTH_ENABLED=true flask create-user --username admin
AUTH_ENABLED=true flask run --port 5050
```

### Production / 프로덕션 배포

```bash
cp viewer/.env.example viewer/.env
# Edit .env: AUTH_ENABLED=true, SECRET_KEY, FLASK_ENV=production

cd viewer
gunicorn -c gunicorn.conf.py app:app
```

> Details: [viewer/README.md](viewer/README.md)

---

## Project Structure / 프로젝트 구조

```
study-hub-viewer/
├── shared/                 # Shared utilities
│   └── utils/
│       ├── markdown_parser.py
│       ├── search.py
│       ├── examples.py
│       └── exercises.py
│
├── viewer/                 # Flask web viewer (port 5050)
│   ├── app.py              # Main app (AUTH_ENABLED toggle)
│   ├── auth.py             # Auth Blueprint (login/logout, CLI)
│   ├── config.py           # Configuration + security settings
│   ├── models.py           # User, LessonRead, Bookmark
│   ├── forms.py            # WTForms (LoginForm)
│   ├── progress.py         # Batch query helpers (N+1 optimized)
│   ├── build_index.py      # FTS index builder
│   ├── migrate_db.py       # DB migration script
│   ├── gunicorn.conf.py    # Production config
│   ├── .env.example
│   ├── templates/
│   └── static/
│
├── .gitignore
├── LICENSE
└── README.md
```

## License / 라이센스

[MIT License](./LICENSE)

## Author

**Eunsu Park**
- [ORCID: 0000-0003-0969-286X](https://orcid.org/0000-0003-0969-286X)
