# CLAUDE.md — Project Template (FastAPI · React · Supabase)

> **이 파일은 인덱스/포인터다.** 본문 상세는 `.claude/rules/`·`docs/`에 두고, 여기에는 핵심 규칙과 링크만 둔다.
> 이 저장소는 **다양한 프로젝트의 베이스 템플릿**이다 — 멀티 CLI 오케스트레이션 + FastAPI/React/Supabase 모노레포 스캐폴딩.

## 🧱 스택 & 모노레포 구조

| 영역 | 스택 | 위치 |
|---|---|---|
| API | Python 3 · FastAPI · pydantic-settings · supabase-py · OpenAI | `apps/api/` |
| Web | React 19 · Vite 6 · TypeScript(strict) · supabase-js | `apps/web/` |
| DB | Supabase(Postgres) · RLS · migrations | `supabase/` |
| 설계문서 | 번호 폴더 체계 | `docs/` |

```
apps/api    FastAPI backend (app/{api,core,schemas,services,repositories,tests})
apps/web    React+Vite frontend (src/{app,components,features,lib,styles})
supabase    migrations/ + seed.sql
docs        00_overview … 08_coding_guidelines
```
로컬 실행: 루트 [`README.md`](README.md) 참조.

## 🤖 멀티 CLI 오케스트레이션

이 프로젝트는 Claude Code를 오케스트레이터로, Codex·Gemini CLI를 전문 위임 대상으로 쓴다.

| 에이전트 | 역할 | 호출 |
|---|---|---|
| **Claude Code** (main) | 오케스트레이터 + **단일 작성자**(파일 편집·통합) | 사용자 프롬프트 |
| **Codex CLI** (`gpt-5.5`) | 설계·디버깅·코드리뷰·로그/터미널 진단 (read-only 주력) | [`rules/codex-delegation.md`](.claude/rules/codex-delegation.md) · `/codex-system` |
| **Gemini CLI** (`gemini-3-flash-preview`) | 리서치·대규모 분석·멀티모달 | [`rules/gemini-delegation.md`](.claude/rules/gemini-delegation.md) · `/gemini-system` |

**원칙**: 무거운 작업(리서치·심층추론)은 서브에이전트로 위임해 메인 컨텍스트를 보존한다. 라이브 파일의 실제 편집은 항상 Claude가 한다(two-writer desync 방지 — 상세는 codex-delegation.md).

## 🪝 활성 훅 (advisory, `.claude/settings.json`)

| 훅 | 이벤트 | 역할 |
|---|---|---|
| `agent-router.py` | UserPromptSubmit | 키워드 감지 → Codex/Gemini 위임 힌트 주입 |
| `guard-bash.py` | PreToolUse(Bash) | **유일한 차단 훅** — 파괴적 명령·SQL·시크릿 누출 차단 |
| `check-codex-before-write.py` | PreToolUse(Edit/Write) | 고위험 영역(auth/payment 등) 편집 시 Codex 리뷰 권유 |
| `log-cli-tools.py` | PostToolUse(Bash) | Codex/Gemini 호출을 `.claude/logs/cli-tools.jsonl`에 기록 |
| `lint-on-save.py` | PostToolUse(Edit/Write) | `.py` 저장 시 ruff/ty (uv 또는 ruff 있을 때만) |

> opt-in 훅(미연결, 노이즈 우려로 기본 비활성): `check-codex-after-plan.py`, `suggest-gemini-research.py`, `post-implementation-review.py`. 필요하면 `settings.json`에 와이어링한다.

## 📐 규칙 (`.claude/rules/`)

- [`language.md`](.claude/rules/language.md) — 사고는 영어, 사용자 응답은 한국어, 코드는 영어
- [`coding-principles.md`](.claude/rules/coding-principles.md) — 단순성·단일책임·early return·타입힌트
- [`codex-delegation.md`](.claude/rules/codex-delegation.md) / [`gemini-delegation.md`](.claude/rules/gemini-delegation.md) — 위임 규칙
- **스택 규칙**: [`stack-python-fastapi.md`](.claude/rules/stack-python-fastapi.md) · [`stack-react-typescript.md`](.claude/rules/stack-react-typescript.md) · [`stack-supabase.md`](.claude/rules/stack-supabase.md)
- 상세 가이드라인: [`docs/08_coding_guidelines/`](docs/08_coding_guidelines/) · 품질 체크리스트 [`05_quality_checklist.md`](docs/08_coding_guidelines/05_quality_checklist.md)

## 🚀 스킬

- `/startproject` — 멀티에이전트 협업으로 신규 기능 착수(리서치→요구사항→설계리뷰→구현→리뷰)
- `/codex-system`, `/gemini-system` — 위임 호출 패턴 참조

## 📁 산출물 위치

| 위치 | 용도 |
|---|---|
| `.claude/docs/research/{topic}.md` | Gemini/Codex 리서치 결과 |
| `.claude/logs/cli-tools.jsonl` | Codex/Gemini 호출 로그 |

---

## 🎯 Current Project

> 이 저장소를 새 프로젝트의 베이스로 쓸 때, `/startproject`로 착수하면 이 섹션에 **해당 프로젝트의** 목표·핵심 파일·도메인 결정이 누적된다. (템플릿 상태 — 도메인 미정)
>
> 도메인 용어(예: `workspace`/`project`/...)와 실제 라우트·테이블은 프로젝트별로 채운다. 스택·구조·오케스트레이션은 그대로 유지.
