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

## 🎯 Current Project — TQ Project (TQQQ 200일선 매매 코치)

QQQ 200일선 기반 TQQQ 리스크 관리 코치. 로컬 실행: api **7000** / web **4173**.

**핵심 흐름**: 개인연구(ComparePage, 백테스트 랩) → 전략 채택(`POST /managed-strategies/adopt-research`, 규칙이 `research_config`로 저장) → 전략 관리 "오늘의 판단" 탭(`GET /managed-strategies/{id}/today`)에서 일일 실행·기록.

**핵심 파일**:
- `apps/api/app/services/market_data.py` — 전체 히스토리·수정종가·디스크 스냅샷·합성 TQQQ/QLD(1999~)
- `apps/api/app/services/backtest_engine.py` — 백테스트 엔진(감속·방어모드·이월/급락 실험 노브 포함)
- `apps/api/app/services/today_engine.py` — 오늘 판단 (백테스트와 **같은 규칙 함수** 공유 — 절대 분리 금지)
- `apps/api/app/services/compare_engine.py` — 벤치마크 상대·기간 불변 점수 + 실행 점수(17%) + 규칙 강건성
- 연구 결론: [`docs/01_strategy_philosophy/research_daily_accumulation_findings_2026-07-10.md`](docs/01_strategy_philosophy/research_daily_accumulation_findings_2026-07-10.md) (운용 헌장 포함)
- 엔진 개편 기록: [`docs/07_development_plan/backtest_engine_overhaul_2026-07-10.md`](docs/07_development_plan/backtest_engine_overhaul_2026-07-10.md)

**채택 전략 (2026-07-10)**: 매일적립 80:20 · 조기방어 밴드 +2% · 이탈 2일 확인 시 현금 100% 방어 · 회복 후 21일 재투입 · 월 100만 적립. 검증된 원칙: **"대기 현금으로 뭔가 더 하려는 변형(감속 해제·조기 재투입·급락일 추가매수)은 전부 기준 규칙에 진다"** — 규칙 변경 제안은 반드시 백테스트+강건성 검증 후 반영.
