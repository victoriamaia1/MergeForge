import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, tokenStore } from "../api";
import { Flame, ArrowRight, Copy, Check, KeyRound } from "lucide-react";

export default function Auth() {
  const [params] = useSearchParams();
  const [mode, setMode] = useState(params.get("mode") === "signup" ? "signup" : "login");
  const [username, setUsername] = useState("");
  const [token, setToken] = useState("");
  const [issuedToken, setIssuedToken] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const nav = useNavigate();

  const signup = async () => {
    setErr(""); setBusy(true);
    try {
      const r = await api.post("/api/auth/signup", { username });
      setIssuedToken(r.data.token);
    } catch (e) { setErr(e.response?.data?.detail || "Signup failed"); }
    finally { setBusy(false); }
  };
  const login = async () => {
    setErr(""); setBusy(true);
    try {
      const r = await api.post("/api/auth/login", { token });
      tokenStore.set(r.data.token);
      nav("/app");
    } catch (e) { setErr(e.response?.data?.detail || "Invalid token"); }
    finally { setBusy(false); }
  };
  const proceedWithIssued = () => { tokenStore.set(issuedToken); nav("/app"); };
  const copy = () => {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(issuedToken);
      } else {
        const ta = document.createElement("textarea");
        ta.value = issuedToken; ta.style.position="fixed"; ta.style.opacity="0";
        document.body.appendChild(ta); ta.select();
        document.execCommand("copy"); document.body.removeChild(ta);
      }
      setCopied(true); setTimeout(()=>setCopied(false),1500);
    } catch(e) { alert("Copy failed — please select & copy manually."); }
  };

  return (
    <div className="grain min-h-screen flex items-center justify-center p-6">
      <div className="card w-full max-w-md p-8 relative z-10">
        <Link to="/" className="flex items-center gap-2 mb-6">
          <div className="w-9 h-9 rounded-md bg-accent text-ink flex items-center justify-center"><Flame size={20} strokeWidth={2.5}/></div>
          <div className="font-display text-lg">MERGE<span className="text-accent">FORGE</span></div>
        </Link>

        {!issuedToken && (
          <>
            <h1 className="font-display text-2xl mb-2">{mode === "signup" ? "Create access" : "Welcome back"}</h1>
            <p className="text-muted text-sm mb-6">{mode === "signup" ? "Pick a username, get a 30-word access token. No passwords." : "Paste your token to log in."}</p>

            <div className="flex border border-line rounded-md mb-6 overflow-hidden">
              <button data-testid="tab-signup" className={`flex-1 py-2 text-sm ${mode==="signup"?"bg-accent text-ink font-semibold":"text-zinc-300"}`} onClick={()=>setMode("signup")}>Sign up</button>
              <button data-testid="tab-login" className={`flex-1 py-2 text-sm ${mode==="login"?"bg-accent text-ink font-semibold":"text-zinc-300"}`} onClick={()=>setMode("login")}>Log in</button>
            </div>

            {mode === "signup" ? (
              <>
                <label className="text-xs uppercase tracking-wider text-muted">Username</label>
                <input data-testid="signup-username-input" value={username} onChange={e=>setUsername(e.target.value)} className="input mt-1" placeholder="e.g. mergeforge_user" />
                <button data-testid="signup-submit-btn" disabled={busy || username.length<2} onClick={signup} className="btn btn-primary w-full justify-center mt-4">Generate token <ArrowRight size={14}/></button>
              </>
            ) : (
              <>
                <label className="text-xs uppercase tracking-wider text-muted">Access token</label>
                <textarea data-testid="login-token-input" value={token} onChange={e=>setToken(e.target.value)} className="input mt-1 h-28 font-display text-xs" placeholder="alpha-river-..." />
                <button data-testid="login-submit-btn" disabled={busy || token.length<10} onClick={login} className="btn btn-primary w-full justify-center mt-4">Log in <KeyRound size={14}/></button>
              </>
            )}

            {err && <div data-testid="auth-error" className="mt-4 text-sm text-red-400 border border-red-900/60 bg-red-950/30 rounded p-2">{err}</div>}
          </>
        )}

        {issuedToken && (
          <>
            <h2 className="font-display text-2xl mb-1">Save this token</h2>
            <p className="text-muted text-sm mb-4">It is the only way to log back in. 30 words.</p>
            <div data-testid="issued-token-box" className="bg-ink border border-line rounded-md p-3 font-display text-xs break-words leading-relaxed whitespace-pre-wrap">{issuedToken}</div>
            <div className="flex gap-2 mt-4">
              <button data-testid="copy-token-btn" onClick={copy} className="btn btn-ghost flex-1 justify-center">{copied?<><Check size={14}/> Copied</>:<><Copy size={14}/> Copy</>}</button>
              <button data-testid="continue-btn" onClick={proceedWithIssued} className="btn btn-primary flex-1 justify-center">Enter app <ArrowRight size={14}/></button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
