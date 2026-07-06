# 01. 공통 규칙

상태: approved

## 1. 인코딩

- 모든 소스 코드, SQL, Markdown, 설정 파일은 UTF-8로 저장한다.
- 한글 UI 문구와 문서는 UTF-8 한국어를 허용한다.
- 코드 식별자에는 한글을 쓰지 않는다.
- 깨진 한글이 발견되면 해당 파일을 UTF-8로 다시 저장하고 빌드/테스트를 돌린다.

## 2. 파일명

### Python

- 파일명: `snake_case.py`
- 패키지명: `snake_case`

예:

```txt
task_service.py
daily_review_service.py
```

### TypeScript/React

- React 컴포넌트 파일: `PascalCase.tsx`
- hook 파일: `useSomething.ts`
- 일반 util 파일: `camelCase.ts` 또는 도메인 이름 기반 `apiClient.ts`
- CSS 파일: 기존 구조에서는 `styles.css`, 컴포넌트별 CSS를 만들 때는 `ComponentName.css`

예:

```txt
TaskCard.tsx
QuickInput.tsx
useSession.ts
apiClient.ts
```

### 문서

- 한국어 문서명은 허용한다.
- 버전 문서는 `_v1`, `_v2`를 붙인다.

## 3. 네이밍

### 공통

- 축약어는 널리 쓰이는 경우만 허용한다.
- `data`, `info`, `temp`, `result` 같은 넓은 이름은 범위가 짧을 때만 사용한다.
- boolean은 `is`, `has`, `can`, `should`로 시작한다.

예:

```ts
const isLoading = true;
const hasDueDate = Boolean(task.dueDate);
const canSubmit = email.length > 0;
```

### 도메인 용어

각 프로젝트는 자신의 도메인 용어 사전을 **이 문서(또는 `docs/00_overview`)에 정의하고 통일**한다. 예시(멀티테넌트 SaaS):

- `workspace` / `org` (테넌트 경계)
- `project`, `member`, `role`

규칙:
- 용어는 프로젝트당 한 번 정하고 전체 코드에서 동일하게 쓴다.
- UI 표시 문구는 한국어를 사용해도, **코드 식별자는 영어 도메인 용어**를 쓴다.

## 4. 주석

- 코드가 하는 일을 그대로 반복하는 주석은 쓰지 않는다.
- 정책, 보안, 복잡한 판단 이유는 짧게 남긴다.
- TODO는 담당/조건이 있을 때만 쓴다.

좋은 예:

```py
# Service role bypasses RLS, so workspace membership must be checked here.
```

피할 예:

```py
# Set user_id to user_id.
```

## 5. 에러 처리

- 사용자에게 보여줄 에러와 내부 로그용 에러를 구분한다.
- API 에러 응답은 공통 형식을 유지한다.
- AI/외부 API 실패 시 원본 사용자 입력은 보존한다.
- 인증/권한 실패는 401/403을 명확히 구분한다.

## 6. 보안

- `service_role` key는 백엔드에서만 사용한다.
- 프론트에는 Supabase anon key만 둔다.
- `.env`, `.env.local`, `.venv`, `node_modules`는 커밋하지 않는다.
- FastAPI가 service role로 DB를 읽더라도 workspace 권한 검증을 반드시 수행한다.

## 7. 자동화 우선순위

권장 도구:

- Python: Ruff, Black 또는 Ruff formatter, mypy/pyright 후보
- React/TypeScript: ESLint flat config, typescript-eslint, Prettier
- 공통: EditorConfig

처음에는 빌드/타입체크를 우선하고, 린터는 안정화 단계에서 추가한다.

