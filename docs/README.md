# docs

설계·규약 문서. 번호 폴더 체계로 관리한다.

> 📖 **[`USAGE.md`](USAGE.md)** — 이 템플릿 사용법 전체 가이드(시작·개발 루프·오케스트레이션·cheatsheet).

| 폴더 | 내용 |
|---|---|
| `00_overview/` | 프로젝트 개요·문서 목차·도메인 용어 |
| `01_product_strategy/` | 제품 전략·MVP 범위 |
| `02_requirements/` | 요구사항·PRD |
| `03_ux_flows/` | 화면 흐름·UX |
| `04_data_architecture/` | DB 스키마·데이터 모델 (Supabase migration의 설계 근거) |
| `05_api_design/` | API 명세 |
| `06_ai_design/` | AI 응답 스키마·프롬프트 설계·평가셋 (AI 기능이 있을 때) |
| `07_development_plan/` | 개발 계획·체크리스트·로컬 개발 가이드 |
| `08_coding_guidelines/` | **코드 규약 SSOT** — 항상 참조 |
| `90_references/` | 외부 참고자료 |
| `99_archive/` | 이전 버전 |

규칙:
- 기준 문서는 docs에 둔다. 이전 버전은 `99_archive`로 옮긴다.
- 코드 규약 변경 시 `08_coding_guidelines`를 먼저 업데이트한다.
- 새 프로젝트로 쓸 때 `00~07`은 비어 있다 — 해당 프로젝트 설계로 채운다.
