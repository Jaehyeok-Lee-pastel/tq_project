import { NavLink, useLocation } from "react-router-dom";
import {
  ChartNoAxesCombined,
  ChevronRight,
  ClipboardList,
  FlaskConical,
  Info,
  LogOut,
  ShieldCheck,
  Sparkles
} from "lucide-react";
import { AppRoutes } from "./routes";
import { useAuth } from "./AuthContext";
import { LoginPage } from "./LoginPage";

export function App() {
  const { configured, loading, user, signOut } = useAuth();
  const location = useLocation();

  const pageMeta = {
    "/": ["전략 수립", "Portfolio design"],
    "/manage": ["오늘 판단", "Strategy operations"],
    "/lab": ["개인연구", "Research workspace"],
    "/info": ["추가정보", "Reference"],
    "/rules": ["규칙과 신뢰도", "Methodology"],
    "/universe": ["ETF 후보군", "Asset universe"]
  }[location.pathname] ?? ["TQ Coach", "Rule-based investing"];

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
    <main className="product-shell">
      <aside className="product-sidebar">
        <div className="product-brand">
          <span className="brand-mark" aria-hidden="true">
            TQ
          </span>
          <div>
            <strong>TQ Coach</strong>
            <small>Rule-based investing</small>
          </div>
        </div>

        <nav className="app-nav" aria-label="주요 메뉴">
          <NavLink to="/" end>
            <ChartNoAxesCombined size={18} />
            <span>
              전략 수립
              <small>목표 비중 설계</small>
            </span>
            <ChevronRight size={15} className="nav-chevron" />
          </NavLink>
          <NavLink to="/manage">
            <ClipboardList size={18} />
            <span>
              오늘 판단
              <small>실행과 기록</small>
            </span>
            <ChevronRight size={15} className="nav-chevron" />
          </NavLink>
          <NavLink to="/lab">
            <FlaskConical size={18} />
            <span>
              개인연구
              <small>비교와 검증</small>
            </span>
            <ChevronRight size={15} className="nav-chevron" />
          </NavLink>
          <NavLink to="/info">
            <Info size={18} />
            <span>
              추가정보
              <small>규칙과 후보군</small>
            </span>
            <ChevronRight size={15} className="nav-chevron" />
          </NavLink>
        </nav>

        <div className="sidebar-principle">
          <ShieldCheck size={17} />
          <div>
            <strong>QQQ 200일선</strong>
            <small>규칙 우선 · 예측 보조</small>
          </div>
        </div>

        <div className="account-chip">
          <span>{user?.email ?? "로컬 미리보기"}</span>
          {configured ? (
            <button type="button" onClick={signOut} title="로그아웃" aria-label="로그아웃">
              <LogOut size={16} />
            </button>
          ) : null}
        </div>
      </aside>

      <div className="app-workspace">
        <header className="workspace-topbar">
          <div>
            <span>{pageMeta[1]}</span>
            <h1>{pageMeta[0]}</h1>
          </div>
          <div className="workspace-state">
            <span className="live-dot" />
            규칙 엔진 준비
            <Sparkles size={15} />
          </div>
        </header>
        <div className="app-shell">
          <AppRoutes />
        </div>
      </div>
    </main>
  );
}
