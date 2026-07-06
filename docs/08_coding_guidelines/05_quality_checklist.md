# 05. 품질 체크리스트

상태: approved

## 1. 구현 전

- [ ] 관련 PRD/화면흐름/API/DB 문서를 확인했다.
- [ ] `docs/08_coding_guidelines` 규칙을 확인했다.
- [ ] 변경 범위가 MVP 목적과 맞는다.
- [ ] 새 기능이 기존 폴더 구조에 자연스럽게 들어간다.
- [ ] 민감한 키가 코드에 들어가지 않는다.

## 2. Python/FastAPI 변경 후

- [ ] Python 문법 검사 통과
- [ ] route는 얇게 유지됨
- [ ] 비즈니스 로직은 service로 분리됨
- [ ] request/response schema가 필요하면 Pydantic 모델을 추가함
- [ ] workspace 권한 검증이 빠지지 않음
- [ ] service role key가 프론트로 노출되지 않음
- [ ] 에러 응답이 사용자에게 이해 가능함

권장 확인:

```powershell
cd apps/api
.\.venv\Scripts\python.exe -m py_compile app\main.py
```

## 3. React/TypeScript 변경 후

- [ ] `npm.cmd run build` 통과
- [ ] 컴포넌트명은 PascalCase
- [ ] props 타입이 명시됨
- [ ] API 응답 타입이 명시됨
- [ ] loading/error/empty 상태가 있음
- [ ] icon-only 버튼은 aria-label이 있음
- [ ] 한글 텍스트가 깨지지 않음

권장 확인:

```powershell
cd apps/web
npm.cmd run build
```

## 4. DB/Supabase 변경 후

- [ ] migration 파일로 변경을 남김
- [ ] 새 테이블에 RLS가 켜져 있음
- [ ] 새 테이블에 policy가 있음
- [ ] workspace_id 기준 접근 제어가 있음
- [ ] 필요한 인덱스가 있음
- [ ] seed 데이터 영향 확인

## 5. AI 기능 변경 후

- [ ] AI 응답 JSON schema가 명확함
- [ ] 실패 시 원문 note가 보존됨
- [ ] AI 결과는 사용자가 수정 가능함
- [ ] prompt_version을 기록함
- [ ] 평가 샘플셋으로 최소 수동 검증함

## 6. 완료 전

- [ ] 서버 재시작 후 확인
- [ ] 프론트 화면 확인
- [ ] `/health` 확인
- [ ] 핵심 사용자 흐름(로그인 등) 수동 확인
- [ ] 빌드 산출물 `dist`, `*.tsbuildinfo`, `__pycache__` 정리
- [ ] 문서 업데이트가 필요한 경우 docs 반영

