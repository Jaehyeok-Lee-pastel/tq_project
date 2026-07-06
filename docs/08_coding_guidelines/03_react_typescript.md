# 03. React/TypeScript 규칙

상태: approved

## 1. 기준

- React는 함수형 컴포넌트를 사용한다.
- TypeScript는 `strict`를 유지한다.
- 컴포넌트명은 `PascalCase`.
- 일반 함수와 변수는 `camelCase`.
- 타입/인터페이스는 `PascalCase`.
- React Hooks는 `use`로 시작한다.

## 2. 폴더 구조

권장 구조:

```txt
apps/web/src/
  app/
    App.tsx
    routes.tsx
  components/
    common/
    layout/
  features/
    auth/
    <domain>/        # 도메인별 기능 폴더를 추가
  lib/
    api.ts
    supabase.ts
  styles/
```

현재 scaffold는 작게 시작했으므로, 파일이 늘어나면 위 구조로 이동한다.

## 3. 컴포넌트 규칙

- 한 파일에는 주 컴포넌트 하나를 둔다.
- 150줄을 넘기면 하위 컴포넌트 분리를 검토한다.
- props 타입은 컴포넌트 가까이에 둔다.
- UI 문구는 한국어를 허용한다.

예:

```tsx
type ItemCardProps = {
  title: string;
  subtitle: string;
  priority: "high" | "medium" | "low";
};

export function ItemCard({ title, subtitle, priority }: ItemCardProps) {
  ...
}
```

## 4. 상태 관리

초기 MVP:

- 서버 상태: API 호출 + local state
- 인증 상태: Supabase session
- 전역 상태 라이브러리는 도입하지 않는다.

도입 검토 시점:

- 여러 화면에서 같은 서버 데이터를 공유한다.
- 캐싱/재시도/무효화가 필요하다.
- 그때 TanStack Query를 우선 검토한다.

## 5. API 호출

- `fetch` 직접 호출은 `lib/api.ts`에 감싼다.
- 컴포넌트에서 URL 문자열을 흩뿌리지 않는다.
- response 타입을 명시한다.
- 에러 메시지는 사용자용 문구로 변환한다.

예:

```ts
apiGet<ItemListResponse>("/items", token);
```

## 6. Supabase

- Supabase client는 `lib/supabase.ts`에서만 생성한다.
- 프론트에서는 anon key만 사용한다.
- service role key를 프론트 환경변수에 넣지 않는다.

## 7. 스타일

- 현재 MVP는 CSS 파일 기반으로 간다.
- 페이지 전체 layout은 `AppShell`, `Sidebar`, `Topbar` 같은 구조 컴포넌트로 분리한다.
- 버튼/입력/카드 등 반복 UI는 공통 컴포넌트화한다.
- 텍스트가 좁은 버튼 안에서 깨지지 않도록 최소 너비와 줄바꿈을 고려한다.

## 8. 접근성

- 입력에는 label 또는 `aria-label`을 둔다.
- icon-only 버튼은 `aria-label`을 둔다.
- 색상만으로 상태를 구분하지 않는다.
- 버튼은 실제 `<button>`을 사용한다.

## 9. 네이밍

컴포넌트:

```txt
ItemCard
QuickInput
SummaryCards
AppSidebar
```

함수:

```txt
handleLogin
handleLogout
loadItems
formatDate
```

타입:

```txt
ApiItem
ItemListResponse
Priority
```

## 10. 빌드/품질

현재 필수:

```powershell
npm.cmd run build
```

추가 예정:

```powershell
npm.cmd run lint
npm.cmd run format
```

ESLint는 flat config 기반으로 구성한다. TypeScript lint는 `typescript-eslint` recommended config를 우선한다.

