# 04. 프로젝트 구조 규칙

상태: approved (template)

## 1. 루트 구조

```txt
<project>/
  .claude/        # Claude Code 오케스트레이션 (hooks, rules, skills)
  .codex/         # Codex CLI 설정·스킬
  .gemini/        # Gemini CLI 설정·스킬
  apps/
    web/          # React + Vite frontend
    api/          # FastAPI backend
  docs/           # 설계·규약 문서 (번호 폴더)
  supabase/
    migrations/
    seed.sql
  CLAUDE.md  AGENTS.md  README.md  .env.example  .gitignore
```

## 2. apps/api (FastAPI)

```txt
apps/api/
  app/
    main.py          # create_app(): CORS + router includes
    api/
      deps.py        # get_current_user 등 FastAPI dependency
      routes/        # 얇은 HTTP endpoint (도메인 단위 파일)
    core/
      config.py      # pydantic-settings
    schemas/         # Pydantic request/response
    services/        # 업무 로직 + supabase.py(유일한 backend Supabase client)
    repositories/    # DB 접근 (services에서 분리할 때)
    tests/
  requirements.txt
  .env.example
```

규칙:
- `.env`, `.venv`는 커밋하지 않는다.
- 새 REST API: `routes → services → repositories → schemas` 순으로 위치를 정한다.
- route 함수 안에 Supabase query·긴 업무 로직을 직접 두지 않는다.
- 외부 반환 응답에는 가능하면 Pydantic `response_model`을 붙인다.
- Supabase `service_role` key는 백엔드에서만.

## 3. apps/web (React + Vite)

```txt
apps/web/
  src/
    app/           # App.tsx, routes (커지면 분리)
    components/     # 공통/layout UI
    features/       # 도메인 기능 features/{domain} (커지면 pages→features 이동)
    lib/            # api.ts(=API 호출 단일 통로), supabase.ts(anon key 전용)
    styles/
  package.json
  .env.example
```

규칙:
- `.env.local`, `node_modules`, `dist`, `*.tsbuildinfo`는 커밋하지 않는다.
- API 응답 타입은 컴포넌트에 흩지 말고 `features/*/types` 또는 `lib`에 둔다.
- API 호출 함수는 `lib/api.ts`에 둔다. Supabase anon key만 프론트에서 사용.

## 4. docs

```txt
docs/
  00_overview/        01_product_strategy/   02_requirements/
  03_ux_flows/        04_data_architecture/  05_api_design/
  06_ai_design/       07_development_plan/   08_coding_guidelines/
  90_references/      99_archive/
```

규칙:
- 기준 문서는 docs에 둔다. 이전 버전은 `99_archive`로 옮긴다.
- 코드 규약 변경 시 `08_coding_guidelines`를 먼저 업데이트한다.

## 5. supabase

```txt
supabase/
  migrations/   # YYYYMMDDhhmm_description.sql
  seed.sql
```

규칙:
- migration은 되돌리기보다 **새 파일로 보정**한다.
- 운영 DB에 seed를 그대로 적용하지 않는다.
- RLS policy 변경은 migration으로 남긴다.

## 6. 파일 이동 기준

처음에는 단순하게 두고, 아래 조건에서 이동/분리한다.

- 파일이 150~200줄을 넘는다.
- 한 파일에 서로 다른 책임이 2개 이상 섞인다.
- 같은 코드가 3번 이상 반복된다.
- 테스트하기 어려워진다.
