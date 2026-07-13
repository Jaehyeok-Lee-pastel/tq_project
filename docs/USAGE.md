# 사용 가이드 (Template Usage)

이 템플릿을 새 프로젝트의 베이스로 쓰는 전체 흐름을 한곳에 정리한다.
(스택·구조 개요는 [`../README.md`](../README.md), 오케스트레이션 상세는 [`../CLAUDE.md`](../CLAUDE.md).)

---

## 1. 새 프로젝트 만들기

```powershell
# 1) 템플릿 복사
Copy-Item D:\이재혁\project-template D:\이재혁\<새프로젝트> -Recurse

# 2) 이름 일괄 변경 (APP_NAME · web package name · index.html title)
cd D:\이재혁\<새프로젝트>
pwsh ./scripts/init-project.ps1 -Name <새프로젝트>

# 3) (선택) 새 git 저장소로 시작
git init
```

그다음 환경값을 채운다:
- `apps/api/.env`  ← `Copy-Item apps/api/.env.example apps/api/.env` 후 Supabase 키 입력
- `apps/web/.env.local` ← `Copy-Item apps/web/.env.example apps/web/.env.local` 후 API base + Supabase anon key

---

## 2. 로컬 개발 루프

### Backend (apps/api)

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000     # http://localhost:8000/health, /docs
```

### Frontend (apps/web)

```powershell
cd apps/web
npm install
npm run dev                                     # http://localhost:5173
```

첫 화면은 `전략 수립`이며, 상단 메뉴에서 `오늘 판단`, `개인연구`, `추가정보`로 이동한다.
백엔드 상태는 `/health`의 `ready`와 `checks`로 운영 설정까지 함께 확인한다.

### DB (Supabase)

`supabase/migrations/*.sql`를 시간순으로 적용한다. 새 테이블은 **RLS enable + policy** 필수. 스타터 마이그레이션(`profiles`)이 패턴 예시다. 상세: [`../supabase/README.md`](../supabase/README.md).

### 품질 게이트 (커밋/PR 전)

```powershell
# api
cd apps/api;  ruff check . ;  pytest
# web
cd apps/web;  npm run lint ;  npm run format ;  npm run build
```

동일 게이트가 CI(`.github/workflows/ci.yml`)에서도 돈다.

### Docker (선택)

```powershell
docker compose up --build      # api(:8000) + web(:5173)
```

---

## 3. AI 오케스트레이션 활용

Claude Code 안에서 동작한다. 핵심: **Claude가 오케스트레이터 겸 유일한 파일 작성자**, 무거운 분석/리서치는 Codex·Gemini에 위임한다.

| 도구 | 언제 | 호출 방법 |
|---|---|---|
| **Codex** (`gpt-5.5`) | 설계·디버깅·코드리뷰·로그 진단 | `/codex-system` 스킬 또는 키워드("아키텍처","디버깅","리뷰") |
| **Gemini** (`gemini-3-flash-preview`) | 리서치·대규모 분석·멀티모달 | `/gemini-system` 스킬 또는 키워드("리서치","조사","최신 문서") |
| **`/startproject`** | 새 기능 착수 (리서치→요구사항→설계리뷰→작업→구현→리뷰) | Claude Code에서 `/startproject` |

자동으로 일어나는 일 (훅, `.claude/settings.json`):
- 프롬프트 키워드 감지 → Codex/Gemini 위임 힌트 주입 (`agent-router`)
- auth/payment/migration 등 **고위험 파일 편집 시** Codex 리뷰 권유 (`check-codex-before-write`)
- **위험 명령 차단** — `rm -rf`, WHERE 없는 DELETE/UPDATE, 시크릿을 외부 CLI로 파이프 (`guard-bash`, 유일한 차단 훅)
- `.py` 저장 시 ruff (`uv`/`ruff` 있을 때), Codex/Gemini 호출은 `.claude/logs/`에 기록

> 위임이 동작하려면 `codex`·`gemini` CLI가 PATH에 있어야 한다. 훅은 `python3`로 실행된다(없으면 훅만 조용히 스킵).

---

## 4. 자주 하는 작업 (cheatsheet)

**새 API 엔드포인트** — `routes → services → repositories → schemas` 순서:
1. `app/schemas/<domain>.py` — Pydantic request/response
2. `app/repositories/<domain>_repository.py` — Supabase 조회 (`get_supabase()` 사용)
3. `app/services/<domain>_service.py` — 업무 로직 + **소유권/테넌트 검증**
4. `app/api/routes/<domain>.py` — 얇은 라우터(`CurrentUserDep`로 인증)
5. `app/main.py`의 `create_app()`에 `include_router` 추가
6. `app/tests/test_<domain>.py`
   - 예시 경로: `routes/me.py` → `repositories/profile_repository.py` → `schemas/me.py`

**새 화면(web)**:
1. `src/pages/<Name>Page.tsx` (또는 `src/features/<domain>/`)
2. `src/app/routes.tsx`에 `<Route>` 추가
3. API 호출은 `src/lib/api.ts`의 `apiGet/Post/Patch/Delete`만 사용

**새 테이블(DB)**:
1. `supabase/migrations/<timestamp>_<desc>.sql` 새 파일
2. RLS enable + 테넌트/소유 정책 + 필요한 인덱스
3. 설계 근거는 `docs/04_data_architecture/`에

---

## 5. 규칙 · 문서 위치 (SSOT)

| 무엇 | 어디 |
|---|---|
| 프로젝트 인덱스(에이전트가 읽음) | `CLAUDE.md`, `AGENTS.md` |
| 코드 규약(상세) | `docs/08_coding_guidelines/` |
| Claude 요약 규칙 카드 | `.claude/rules/stack-*.md`, `coding-principles.md`, `language.md` |
| 위임 규칙 | `.claude/rules/codex-delegation.md`, `gemini-delegation.md` |
| 설계 문서 | `docs/00_overview … 07_development_plan` (프로젝트별로 채움) |
| 리서치 결과 | `.claude/docs/research/{topic}.md` |

> 새 프로젝트에서 가장 먼저 할 일: `docs/00_overview`에 **목표 + 도메인 용어 사전**을 적고, `CLAUDE.md`의 "Current Project" 섹션을 채운다(또는 `/startproject`가 채우게 한다).
