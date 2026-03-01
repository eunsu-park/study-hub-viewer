# Study Hub Viewer

A collection of viewer and site generation tools for [Study Hub](https://github.com/eunsu-park/study-hub): a personal Flask viewer with progress tracking and search, a multi-user Flask viewer with authentication, and a static site generator for GitHub Pages.

[Study Hub](https://github.com/eunsu-park/study-hub) 학습 자료를 위한 뷰어/사이트 생성 도구 모음. 개인용 Flask 뷰어(진행률 추적, 검색), 다중 사용자 Flask 뷰어(인증), 정적 사이트 생성기(GitHub Pages)를 포함합니다.

## Tools / 도구

| Tool | Description | Port |
|------|-------------|------|
| **viewer/** | Personal Flask web viewer / 개인용 Flask 웹 뷰어 | 5050 |
| **multi_viewer/** | Multi-user Flask viewer (auth, per-user data) / 다중 사용자 Flask 뷰어 | 5051 |
| **site/** | Static site generator (GitHub Pages) / 정적 사이트 생성기 | — |

## Prerequisites / 사전 요구사항

This repo references content from the study-hub repository. Clone it first.

이 레포는 study-hub 레포의 콘텐츠를 참조합니다. 먼저 study-hub를 clone하세요.

```bash
git clone https://github.com/eunsu-park/study-hub.git ~/repos/study-hub
git clone https://github.com/eunsu-park/study-hub_viewer.git ~/repos/study_hub_viewer
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

## Viewer (Personal / 개인용)

Single-user local study viewer. No authentication.

단일 사용자 로컬 학습 뷰어. 인증 없음.

```bash
cd viewer
pip install -r requirements.txt
flask init-db && flask build-index
flask run --port 5050
# http://127.0.0.1:5050
```

> Details: [viewer/README.md](viewer/README.md)

---

## Multi Viewer (Multi-user / 다중 사용자)

Multi-user viewer for server deployment. Flask-Login + bcrypt auth, per-user data isolation.

서버 배포용 다중 사용자 뷰어. Flask-Login + bcrypt 인증, 유저별 데이터 격리.

```bash
cd multi_viewer
pip install -r requirements.txt
flask init-db && flask build-index
flask create-user --username admin
flask run --port 5051
# http://127.0.0.1:5051
```

### Production / 프로덕션 배포

```bash
# Set environment variables / 환경변수 설정
cp multi_viewer/.env.example multi_viewer/.env
# Generate SECRET_KEY: python -c "import secrets; print(secrets.token_hex(32))"

# Run with Gunicorn / Gunicorn으로 실행
cd multi_viewer
gunicorn -c gunicorn.conf.py app:app
```

Nginx config: [multi_viewer/nginx.conf.example](multi_viewer/nginx.conf.example)

> Details: [multi_viewer/README.md](multi_viewer/README.md)

---

## Site Generator (Static Site / 정적 사이트)

Static HTML site generation for GitHub Pages hosting.

GitHub Pages용 정적 HTML 사이트 생성.

```bash
cd site
pip install -r requirements.txt
python build.py --clean
# Or specify content directory:
python build.py --content-dir ~/repos/study-hub --clean
```

Options: `--output <dir>`, `--base-url <path>`, `--content-dir <path>`, `--clean`

---

## Project Structure / 프로젝트 구조

```
study_hub_viewer/
├── viewer/              # Personal Flask viewer (port 5050)
│   ├── app.py
│   ├── config.py        # STUDY_HUB_PATH env var support
│   ├── models.py
│   ├── build_index.py
│   ├── templates/
│   ├── static/
│   └── utils/
│
├── multi_viewer/        # Multi-user Flask viewer (port 5051)
│   ├── app.py
│   ├── auth.py          # Auth Blueprint (login/logout, CLI)
│   ├── config.py        # STUDY_HUB_PATH + security settings
│   ├── models.py        # User, LessonRead, Bookmark (with user_id)
│   ├── forms.py
│   ├── gunicorn.conf.py
│   ├── nginx.conf.example
│   ├── .env.example
│   ├── templates/
│   ├── static/
│   └── utils/
│
├── site/                # Static site generator
│   ├── build.py         # --content-dir option
│   ├── config.py
│   ├── builders/
│   ├── templates/
│   └── utils/
│
├── .gitignore
├── LICENSE
├── CLAUDE.md
└── README.md
```

## License / 라이센스

[MIT License](./LICENSE)

## Author

**Eunsu Park**
- [ORCID: 0000-0003-0969-286X](https://orcid.org/0000-0003-0969-286X)
