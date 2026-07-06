# AGENTS.md — Project Template (read by Codex / Gemini)

이 저장소는 **FastAPI · React · Supabase** 모노레포 베이스 템플릿이며, Claude Code가 오케스트레이터로 Codex/Gemini CLI를 위임 호출한다. 당신(Codex/Gemini)은 분석·리서치·리뷰를 제공하고, **파일 편집은 Claude가 수행**한다.

## Stack & Layout

```
apps/api/   FastAPI (Python). app/{api/routes, api/deps.py, core/config.py, schemas, services, repositories, tests}
apps/web/   React 19 + Vite 6 + TS strict. src/{app, components, features, lib, styles}
supabase/   migrations/*.sql + seed.sql (RLS, tenant-scoped)
docs/       numbered design docs; 08_coding_guidelines is the SSOT for code rules
```

## Core Rules (요약 — 상세는 docs/08_coding_guidelines)

- **레이어 분리**: FastAPI 라우터는 얇게(HTTP만), 로직은 `services/`, DB는 `repositories/`/`services/`, 타입은 `schemas/`(Pydantic).
- **Supabase 클라이언트**: 백엔드는 `app/services/supabase.py`에서만, 프론트는 `src/lib/supabase.ts`에서만 생성. 프론트=anon key, 백엔드=service_role key.
- **보안**: service_role는 RLS 우회 → API에서 테넌트/소유권 검증 필수. 시크릿은 `.env`에서만, 코드/로그/프론트 노출 금지.
- **타입**: Python 타입힌트 필수, TS `strict`. 식별자는 영어, UI 문구는 한국어 허용.
- **DB 변경**: 항상 migration 파일로. 새 테이블은 RLS enable + policy.
- 파일이 150~200줄을 넘거나 책임이 2개 이상 섞이면 분리.

## How you're called

- 분석/리뷰: `codex exec --sandbox read-only --skip-git-repo-check "..." < /dev/null` (read-only 주력)
- 리서치: `gemini -m gemini-3-flash-preview -p "..."` → 결과는 `.claude/docs/research/`에 저장
- 출력 언어: 영어로 답하면 Claude가 사용자에게 한국어로 보고.

## Output Format

- **Codex**: Analysis / Recommendation / Rationale / Risks / Next Steps
- **Gemini**: Summary / Details / Recommendations / Sources
