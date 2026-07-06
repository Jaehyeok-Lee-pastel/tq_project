import { useState } from "react";
import { Bot, LockKeyhole, Mail, UserPlus } from "lucide-react";
import { isSupabaseConfigured, supabase } from "../lib/supabase";

export function LoginPage() {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("친구에게 공유하기 전, 간단히 로그인해서 내 전략과 기록을 분리합니다.");
  const [loading, setLoading] = useState(false);

  async function submit() {
    if (!isSupabaseConfigured) {
      setStatus("Supabase 환경변수 VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY를 먼저 설정해야 합니다.");
      return;
    }
    if (!email || !password) {
      setStatus("이메일과 비밀번호를 입력해주세요.");
      return;
    }

    setLoading(true);
    try {
      const result =
        mode === "login"
          ? await supabase.auth.signInWithPassword({ email, password })
          : await supabase.auth.signUp({ email, password });
      if (result.error) throw result.error;
      setStatus(mode === "login" ? "로그인되었습니다." : "가입 요청이 완료되었습니다. 이메일 확인 설정이 켜져 있으면 메일을 확인해주세요.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "로그인 처리에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-card">
        <div>
          <span className="section-label">
            <Bot size={15} />
            TQ Coach
          </span>
          <h1>개인 전략과 기록을 로그인으로 분리합니다</h1>
          <p>{status}</p>
        </div>

        <div className="auth-form">
          {!isSupabaseConfigured ? (
            <div className="auth-warning">
              Supabase 연결 정보가 없습니다. 배포 환경에 `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`를 설정하면 로그인 화면이 활성화됩니다.
            </div>
          ) : null}
          <label>
            이메일
            <div className="input-with-icon">
              <Mail size={16} />
              <input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="friend@example.com" />
            </div>
          </label>
          <label>
            비밀번호
            <div className="input-with-icon">
              <LockKeyhole size={16} />
              <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="8자 이상 권장" />
            </div>
          </label>
          <button className="primary" onClick={submit} disabled={loading || !isSupabaseConfigured}>
            {mode === "login" ? <LockKeyhole size={16} /> : <UserPlus size={16} />}
            {loading ? "처리 중" : mode === "login" ? "로그인" : "회원가입"}
          </button>
          <button type="button" onClick={() => setMode((current) => (current === "login" ? "signup" : "login"))}>
            {mode === "login" ? "처음이면 회원가입" : "이미 계정이 있으면 로그인"}
          </button>
        </div>
      </section>
    </main>
  );
}
