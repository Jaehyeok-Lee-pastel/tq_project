# Project Template — FastAPI · React · Supabase + AI Orchestration

다양한 프로젝트의 **베이스 템플릿**이다. FastAPI/React/Supabase 모노레포 스캐폴딩과, Claude Code가 Codex·Gemini CLI를 위임 호출하는 멀티 CLI 오케스트레이션을 함께 담았다.

> 👉 **처음이라면 [`docs/USAGE.md`](docs/USAGE.md)** — 복사 → 개발 루프 → 오케스트레이션 활용 → 자주 하는 작업까지 한 번에.

## 구조

```txt
.claude/   Claude Code 오케스트레이션 (hooks, rules, skills, agents)
.codex/    Codex CLI 설정·스킬
.gemini/   Gemini CLI 설정·스킬
apps/
  api/     FastAPI backend
  web/     React + Vite frontend
supabase/  migrations + seed
docs/      설계·규약 문서 (08_coding_guidelines = 코드 규약 SSOT)
CLAUDE.md AGENTS.md  # 에이전트가 읽는 프로젝트 컨텍스트
```

## 로컬 실행

### Backend (apps/api)

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env       # Supabase 키 입력
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health: http://localhost:8000/health · Docs: http://localhost:8000/docs

### Frontend (apps/web)

```powershell
cd apps/web
npm install
Copy-Item .env.example .env.local  # API base + Supabase anon key 입력
npm run dev
```

http://localhost:5173 — 초기 화면이 백엔드 `/health`를 호출해 연결을 확인한다.

### Supabase

`supabase/migrations/*.sql`를 시간순 적용 후 필요 시 `supabase/seed.sql` 적용. 상세: [`supabase/README.md`](supabase/README.md).

### Docker (선택)

```powershell
docker compose up --build   # api(:8000) + web(:5173) 동시 기동
```
개별 빌드: `apps/api/Dockerfile`(uvicorn), `apps/web/Dockerfile`(vite build → nginx, SPA fallback). `apps/api/.env`가 있어야 compose가 키를 주입한다.

## AI 오케스트레이션 (개발 시)

Claude Code 안에서 동작한다. 무거운 작업은 위임한다:

- **Codex** (`gpt-5.5`) — 설계·디버깅·코드리뷰·로그 진단 (read-only)
- **Gemini** (`gemini-3-flash-preview`) — 리서치·대규모 분석·멀티모달

키워드를 감지하면 훅이 위임을 제안하고(`agent-router.py`), 위험한 명령은 차단된다(`guard-bash.py`). 스킬: `/startproject`(신규 기능 착수), `/codex-system`, `/gemini-system`. 상세: [`CLAUDE.md`](CLAUDE.md).

> Codex/Gemini CLI가 PATH에 있어야 위임이 동작한다. 훅은 `python3`로 실행된다(미설치 시 훅만 조용히 스킵).

## 새 프로젝트로 사용하기

1. 이 폴더를 새 위치로 복사한다. 예: `Copy-Item D:\이재혁\project-template D:\이재혁\my-app -Recurse`
2. 이름 일괄 변경: `pwsh ./scripts/init-project.ps1 -Name my-app` (APP_NAME·web package name·title 치환)
3. `apps/api/.env`, `apps/web/.env.local`을 채운다.
4. `supabase/migrations/`의 스타터 마이그레이션(`profiles`)을 적용하거나, 프로젝트 스키마로 교체한다.
5. `docs/00~07`을 해당 프로젝트 설계로 채우고, `docs/00_overview`에 도메인 용어를 정의한다.
6. Claude Code에서 `/startproject`로 첫 기능을 착수한다.

품질 게이트: `apps/api`에서 `ruff check . && pytest`, `apps/web`에서 `npm run lint && npm run build` (CI: `.github/workflows/ci.yml`).
코드 규약: [`docs/08_coding_guidelines/`](docs/08_coding_guidelines/README.md).
