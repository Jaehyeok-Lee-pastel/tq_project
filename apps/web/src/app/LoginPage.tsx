import { useState } from "react";
import { ArrowRight, Bot, CheckCircle2, LockKeyhole, Mail, ShieldCheck, UserPlus } from "lucide-react";
import { isSupabaseConfigured, supabase } from "../lib/supabase";

type AuthMode = "login" | "signup";

const authCopy = {
  login: {
    badge: "LOGIN",
    title: "내 전략 기록으로 로그인",
    description: "저장한 전략, 실행 기록, 코칭 내역을 내 계정 기준으로 안전하게 불러옵니다.",
    button: "로그인",
    switchText: "처음 오셨나요?",
    switchAction: "회원가입",
    success: "로그인되었습니다.",
  },
  signup: {
    badge: "JOIN",
    title: "전략 코치 계정 만들기",
    description: "친구에게 공유해도 내 전략 데이터는 계정별로 분리되어 저장됩니다.",
    button: "회원가입",
    switchText: "이미 계정이 있으신가요?",
    switchAction: "로그인",
    success: "회원가입 요청이 완료되었습니다. 이메일 확인 설정이 켜져 있다면 메일함을 확인해주세요.",
  },
} satisfies Record<AuthMode, Record<string, string>>;

export function LoginPage() {
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("로그인하면 개인 전략과 실행 기록이 계정별로 분리됩니다.");
  const [loading, setLoading] = useState(false);
  const copy = authCopy[mode];

  async function submit() {
    if (!isSupabaseConfigured) {
      setStatus("Supabase 환경변수 VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY를 먼저 설정해야 합니다.");
      return;
    }
    if (!email.trim() || !password) {
      setStatus("이메일과 비밀번호를 모두 입력해주세요.");
      return;
    }
    if (mode === "signup" && password.length < 8) {
      setStatus("회원가입 비밀번호는 8자 이상을 권장합니다.");
      return;
    }

    setLoading(true);
    try {
      const result =
        mode === "login"
          ? await supabase.auth.signInWithPassword({ email: email.trim(), password })
          : await supabase.auth.signUp({ email: email.trim(), password });
      if (result.error) throw result.error;
      setStatus(copy.success);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "인증 처리에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  function switchMode(nextMode: AuthMode) {
    setMode(nextMode);
    setStatus(
      nextMode === "login"
        ? "저장한 전략과 실행 기록을 다시 불러옵니다."
        : "새 계정을 만들면 전략 기록이 사용자별로 분리됩니다.",
    );
  }

  return (
    <main className="auth-shell">
      <section className="auth-layout" aria-label="TQ Coach account access">
        <div className="auth-intro">
          <span className="section-label">
            <Bot size={15} />
            TQ Coach
          </span>
          <h1>TQQQ 200일선 전략을 계정별로 관리하세요</h1>
          <p>
            로그인과 회원가입을 분리해 친구에게 공유해도 각자의 포트폴리오, 전략 버전,
            실행 기록이 독립적으로 저장됩니다.
          </p>
          <div className="auth-benefits">
            <span>
              <ShieldCheck size={16} />
              Supabase Auth 보호
            </span>
            <span>
              <CheckCircle2 size={16} />
              사용자별 전략 저장
            </span>
          </div>
        </div>

        <div className="auth-card">
          <div className="auth-mode-tabs" role="tablist" aria-label="인증 방식 선택">
            <button
              type="button"
              className={mode === "login" ? "active" : ""}
              onClick={() => switchMode("login")}
              aria-selected={mode === "login"}
              role="tab"
            >
              로그인
            </button>
            <button
              type="button"
              className={mode === "signup" ? "active" : ""}
              onClick={() => switchMode("signup")}
              aria-selected={mode === "signup"}
              role="tab"
            >
              회원가입
            </button>
          </div>

          <div className="auth-card-head">
            <span>{copy.badge}</span>
            <h2>{copy.title}</h2>
            <p>{copy.description}</p>
          </div>

          <div className="auth-form">
            {!isSupabaseConfigured ? (
              <div className="auth-warning">
                Supabase 연결 정보가 없습니다. 배포 환경에 VITE_SUPABASE_URL,
                VITE_SUPABASE_ANON_KEY를 설정하면 로그인 화면이 활성화됩니다.
              </div>
            ) : null}

            <label>
              이메일
              <div className="input-with-icon">
                <Mail size={16} />
                <input
                  autoComplete="email"
                  inputMode="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@example.com"
                />
              </div>
            </label>

            <label>
              비밀번호
              <div className="input-with-icon">
                <LockKeyhole size={16} />
                <input
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder={mode === "login" ? "비밀번호 입력" : "8자 이상 권장"}
                />
              </div>
            </label>

            <button className="primary auth-submit" onClick={submit} disabled={loading || !isSupabaseConfigured}>
              {mode === "login" ? <LockKeyhole size={17} /> : <UserPlus size={17} />}
              {loading ? "처리 중" : copy.button}
              <ArrowRight size={17} />
            </button>
          </div>

          <p className="auth-status" aria-live="polite">
            {status}
          </p>

          <div className="auth-switch">
            <span>{copy.switchText}</span>
            <button type="button" onClick={() => switchMode(mode === "login" ? "signup" : "login")}>
              {copy.switchAction}
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}
