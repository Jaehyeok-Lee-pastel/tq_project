import { NavLink } from "react-router-dom";
import { Bot, ChartNoAxesCombined, ClipboardList, FlaskConical, Info, LogOut, ShieldCheck } from "lucide-react";
import { AppRoutes } from "./routes";
import { useAuth } from "./AuthContext";
import { LoginPage } from "./LoginPage";

export function App() {
  const { configured, loading, user, signOut } = useAuth();

  if (loading) {
    return (
      <main className="auth-shell">
        <section className="auth-card">
          <span className="section-label">TQ Coach</span>
          <h1>세션을 확인하는 중입니다</h1>
        </section>
      </main>
    );
  }

  if (configured && !user) return <LoginPage />;

  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">
            <Bot size={16} />
            TQQQ 개인 투자전략 코치
          </p>
          <h1>TQ Coach</h1>
          <p className="muted">
            QQQ 200일선 기반 전략 수립, 일일 운용, 테스트와 신뢰도 검증을 분리해서 관리합니다.
          </p>
        </div>
        <nav className="app-nav" aria-label="주요 메뉴">
          <NavLink to="/" end>
            <ChartNoAxesCombined size={17} />
            전략 수립
          </NavLink>
          <NavLink to="/manage">
            <ClipboardList size={17} />
            오늘 판단
          </NavLink>
          <NavLink to="/lab">
            <FlaskConical size={17} />
            테스트
          </NavLink>
          <NavLink to="/info">
            <Info size={17} />
            추가정보
          </NavLink>
        </nav>
        <div className="account-chip">
          <span>{user?.email ?? "로컬 미리보기"}</span>
          {configured ? (
            <button type="button" onClick={signOut}>
              <LogOut size={15} />
              로그아웃
            </button>
          ) : null}
        </div>
      </header>
      <div className="status-band">
        <span>
          <ShieldCheck size={15} />
          기본형과 비교
        </span>
        <span>QQQ 200일선 생존 필터</span>
        <span>규칙 우선, 예측 보조</span>
      </div>
      <AppRoutes />
    </main>
  );
}
