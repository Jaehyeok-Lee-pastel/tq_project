# 02. Python/FastAPI 규칙

상태: approved

## 1. 기준

- Python 코드는 PEP 8을 기본으로 한다.
- 함수/변수/모듈은 `snake_case`.
- 클래스는 `PascalCase`.
- 상수는 `UPPER_SNAKE_CASE`.
- 타입힌트를 기본으로 작성한다.
- FastAPI는 공식 multi-file 구조를 따른다.

## 2. 폴더 구조

권장 구조:

```txt
apps/api/
  app/
    main.py
    api/
      deps.py
      routes/
        health.py
        me.py
        <domain>.py      # 도메인별 라우터를 추가
    core/
      config.py
      errors.py
    schemas/
      common.py
      me.py
      <domain>.py
    services/
      supabase.py
      <domain>_service.py
    repositories/
      profile_repository.py
      <domain>_repository.py
    tests/
```

## 3. 라우터 규칙

- 라우터는 HTTP 입출력과 dependency 처리만 담당한다.
- 비즈니스 로직은 `services/`로 옮긴다.
- request/response 구조는 `schemas/`에 둔다.
- 라우터 파일은 도메인 단위로 나눈다.

좋은 예:

```py
@router.get("", response_model=ItemListResponse)
async def list_items(current_user: CurrentUserDep):
    return item_service.list_items(current_user.user_id)
```

피할 예:

```py
@router.get("")
async def list_items(...):
    # 긴 DB 조회, 분류, AI 호출을 전부 여기서 처리
```

## 4. 서비스 규칙

- 서비스 함수명은 동사로 시작한다.
- DB 조회 함수는 `list_`, `get_`, `create_`, `update_`, `archive_`를 사용한다.
- AI 관련 함수는 `generate_`, `analyze_`, `extract_`를 사용한다.

예:

```py
def list_items(owner_id: str) -> list[dict]:
    ...

def get_item(item_id: str) -> Item:
    ...

def analyze_text(text: str) -> AiSuggestion:
    ...
```

## 5. 인증/권한

- `get_current_user`(`app/api/deps.py`)는 JWT 검증과 현재 사용자 확인을 담당한다.
- 테넌트/소유권이 필요한 API는 서비스 레이어에서 검증한다(예: `owner_id == current_user.user_id`).
- service role 사용 시 RLS 우회를 전제로 보수적으로 검증한다.

## 6. Supabase 사용

- Supabase client 생성은 `services/supabase.py`에서만 한다.
- 라우터에서 직접 `create_client`를 호출하지 않는다.
- SQL에 가까운 복잡한 조회는 서비스 함수로 감싼다.

## 7. Pydantic 스키마

- API request/response는 Pydantic 모델을 사용한다.
- DB 원본 row를 그대로 외부에 노출하지 않는다.
- 날짜/상태/우선순위 enum은 Literal 또는 Enum으로 제한한다.

예:

```py
from typing import Literal
from pydantic import BaseModel

Priority = Literal["high", "medium", "low"]

class ItemSummary(BaseModel):
    id: str
    title: str
    priority: Priority
```

## 8. 비동기

- FastAPI route는 `async def`를 기본으로 한다.
- 단, 사용하는 Supabase Python client가 sync 호출이면 service 내부에서 sync 호출을 허용한다.
- 장기적으로 DB client와 AI client의 비동기화 여부를 재검토한다.

## 9. 테스트

우선순위:

1. 권한 검증 (인증 없는 요청 → 401)
2. 핵심 도메인 로직
3. AI JSON validation (AI 기능이 있을 때)
4. API response schema

테스트 파일명:

```txt
test_health.py
test_me.py
test_<domain>.py
```

## 10. 포맷/린트 권장

초기 권장:

```txt
ruff check .
ruff format .
```

라인 길이는 100자를 권장한다. 긴 문자열/SQL/프롬프트는 가독성을 우선한다.

