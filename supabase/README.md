# supabase

Postgres(Supabase) 마이그레이션과 seed.

```
supabase/
  migrations/   # YYYYMMDDhhmm_description.sql (시간순)
  seed.sql      # 개발용 seed (운영 적용 금지)
```

## 규칙

- 스키마 변경은 **항상 migration 파일로** 남긴다. 기존 파일을 되돌리지 말고 새 파일로 보정한다.
- 새 테이블은 **RLS enable + policy** 필수. 테넌트 컬럼(`workspace_id`/`org_id` 등) 기준 접근 제어.
- 프론트=anon key, 백엔드=service_role key. service_role은 RLS를 우회하므로 API에서 소유권 검증 필수.
- 설계 근거(ERD·테이블 정의)는 `docs/04_data_architecture/`에 둔다.

## 적용 (예)

Supabase SQL Editor 또는 CLI로 `migrations/`를 시간순으로 적용한 뒤, 필요 시 `seed.sql`의 placeholder를 실제 값으로 바꿔 적용한다.
