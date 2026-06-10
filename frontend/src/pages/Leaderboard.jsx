import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Flame, Trophy, ArrowLeft } from "lucide-react";

export default function Leaderboard({ embedded=false }) {
  const [items, setItems] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    api.get("/api/leaderboard?limit=10")
      .then(r => setItems(r.data.items || []))
      .catch(e => setErr(e.message));
  }, []);

  const scoreColor = (s) => s >= 80 ? "text-emerald-300" : s >= 60 ? "text-amber-300" : "text-red-300";

  const body = (
    <div className="max-w-5xl mx-auto" data-testid="leaderboard-root">
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="chip mb-2">Community</div>
          <h1 className="font-display text-3xl md:text-4xl flex items-center gap-2">
            <Trophy className="text-accent" size={28}/> Top merges leaderboard
          </h1>
          <p className="text-muted mt-2 text-sm">Public merges ranked by automated quality score (perplexity + coherence).</p>
        </div>
        {!embedded && <Link to="/" className="btn btn-ghost text-sm"><ArrowLeft size={14}/> Home</Link>}
      </div>
      {err && <div className="text-red-300">Error: {err}</div>}
      {!items && !err && <div className="text-muted">Loading…</div>}
      {items && items.length === 0 && (
        <div className="card p-8 text-center text-muted" data-testid="leaderboard-empty">
          No public merges yet. Mark your completed merges public to be the first on the board.
        </div>
      )}
      {items && items.length > 0 && (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-edge/60 text-muted text-xs uppercase tracking-wider">
              <tr>
                <th className="text-left px-4 py-3">#</th>
                <th className="text-left px-4 py-3">Merge</th>
                <th className="text-left px-4 py-3">Sources</th>
                <th className="text-left px-4 py-3">Method</th>
                <th className="text-right px-4 py-3">Score</th>
                <th className="text-right px-4 py-3">Date</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it, i) => (
                <tr key={it.id} className="border-t border-line" data-testid={`lb-row-${i}`}>
                  <td className="px-4 py-3 font-display text-accent">{i+1}</td>
                  <td className="px-4 py-3">
                    <div className="font-display">{it.name}</div>
                    <div className="text-xs text-muted">by {it.username}</div>
                  </td>
                  <td className="px-4 py-3 text-zinc-300">
                    {(it.models||[]).slice(0,3).map(m=> <div key={m} className="text-xs">{m}</div>)}
                  </td>
                  <td className="px-4 py-3 uppercase text-xs text-zinc-300">{it.method}</td>
                  <td className={`px-4 py-3 text-right font-display text-lg ${scoreColor(it.quality_score||0)}`}>
                    {(it.quality_score ?? 0).toFixed(1)}
                  </td>
                  <td className="px-4 py-3 text-right text-xs text-muted">{(it.created_at||"").slice(0,10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );

  if (embedded) return body;
  return (
    <div className="grain min-h-screen p-6 md:p-10">
      <header className="max-w-5xl mx-auto mb-8 flex items-center gap-2">
        <div className="w-9 h-9 rounded-md bg-accent text-ink flex items-center justify-center"><Flame size={20} strokeWidth={2.5}/></div>
        <div className="font-display text-lg tracking-tight">MERGE<span className="text-accent">FORGE</span></div>
      </header>
      {body}
    </div>
  );
}
