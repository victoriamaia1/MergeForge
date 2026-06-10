import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, BACKEND_URL, tokenStore } from "../api";
import { ArrowLeft, Download, RefreshCw, Loader2, CheckCircle2, XCircle } from "lucide-react";

export default function JobDetail() {
  const { id } = useParams();
  const [job, setJob] = useState(null);
  const [err, setErr] = useState("");

  const load = async () => {
    try { const r = await api.get(`/api/merge/jobs/${id}`); setJob(r.data); }
    catch(e) { setErr(e.response?.data?.detail || "Not found"); }
  };
  useEffect(() => {
    load();
    const t = setInterval(()=>{ if (!job || ["queued","running"].includes(job.status)) load(); }, 1500);
    return ()=>clearInterval(t);
  }, [id]);

  if (err) return <div className="text-red-400" data-testid="job-error">{err}</div>;
  if (!job) return <div className="text-muted">Loading…</div>;
  const dlUrl = `${BACKEND_URL}/api/merge/jobs/${job.id}/download?token=${encodeURIComponent(tokenStore.get())}`;
  const ggufUrl = `${BACKEND_URL}/api/merge/jobs/${job.id}/download/gguf?token=${encodeURIComponent(tokenStore.get())}`;
  const score = job.quality_score;
  const scoreColor = score == null ? "text-muted" : score >= 80 ? "text-emerald-300" : score >= 60 ? "text-amber-300" : "text-red-300";
  const togglePublic = async () => {
    try {
      const r = await api.patch(`/api/merge/jobs/${job.id}/visibility`, { is_public: !job.is_public });
      setJob({ ...job, is_public: r.data.is_public });
    } catch (e) { alert("Could not toggle visibility: " + (e.response?.data?.detail || e.message)); }
  };

  const StatusIcon = job.status==="completed"?CheckCircle2:job.status==="failed"?XCircle:job.status==="running"?Loader2:RefreshCw;

  return (
    <div data-testid="job-detail-root" className="max-w-5xl">
      <Link to="/app/jobs" className="text-sm text-muted hover:text-accent inline-flex items-center gap-1 mb-4"><ArrowLeft size={14}/> Back to jobs</Link>
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="chip mb-2">{job.status.toUpperCase()}</div>
          <h1 className="font-display text-3xl md:text-4xl">{job.name}</h1>
          <div className="text-muted text-sm mt-1">{job.method} · ETA {job.estimated_minutes}m · stage: <span className="text-zinc-200">{job.stage}</span></div>
        </div>
        <StatusIcon size={28} className={job.status==="running"?"text-amber-300 animate-spin":job.status==="completed"?"text-accent":job.status==="failed"?"text-red-400":"text-muted"}/>
      </div>

      <div className="card p-5 mt-6">
        <div className="flex justify-between text-xs text-muted mb-1">
          <span>Progress</span>
          <span data-testid="job-progress-text">{job.progress}%</span>
        </div>
        <div className="h-2 bg-edge rounded-full overflow-hidden">
          <div data-testid="job-progress-bar" className="h-full bg-gradient-to-r from-accent to-accent2 transition-all" style={{width:`${job.progress}%`}}/>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-4 mt-4">
        <div className="card p-4"><div className="text-xs text-muted">Models</div><div className="font-display text-lg">{job.models.length}</div></div>
        <div className="card p-4"><div className="text-xs text-muted">Output size</div><div className="font-display text-lg">{job.output_size_gb}GB</div></div>
        <div className="card p-4"><div className="text-xs text-muted">ETA</div><div className="font-display text-lg">{job.estimated_minutes} min</div></div>
      </div>

      <div className="card p-5 mt-4">
        <div className="text-xs uppercase tracking-wider text-muted mb-2">Source models</div>
        <ul className="text-sm space-y-1">
          {job.models.map(m => <li key={m.id} className="font-display">· <span className="text-accent">{m.weight?.toFixed?.(2) ?? "—"}</span> {m.id}</li>)}
        </ul>
      </div>

      <div className="card p-5 mt-4">
        <div className="flex items-center justify-between mb-2">
          <div className="text-xs uppercase tracking-wider text-muted">Live log</div>
          <button onClick={load} className="text-xs text-accent hover:underline" data-testid="refresh-log-btn">refresh</button>
        </div>
        <pre data-testid="job-log" className="bg-ink border border-line rounded p-3 text-xs font-display max-h-96 overflow-auto whitespace-pre-wrap">{(job.logs||[]).join("\n") || "(no logs yet)"}</pre>
      </div>

      {job.status === "completed" && (
        <div className="card p-5 mt-4" data-testid="quality-card">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <div className="text-xs uppercase tracking-wider text-muted mb-1">Quality score</div>
              {score == null ? (
                <div className="text-sm text-muted" data-testid="quality-pending">Computing… (perplexity + inference tests)</div>
              ) : (
                <div className="flex items-baseline gap-3">
                  <div className={`font-display text-4xl ${scoreColor}`} data-testid="quality-score">{score.toFixed(1)}</div>
                  <div className="text-sm text-zinc-300" data-testid="quality-summary">{job.quality_summary}</div>
                </div>
              )}
            </div>
            <label className="flex items-center gap-2 text-sm cursor-pointer" data-testid="public-toggle-label">
              <input type="checkbox" checked={!!job.is_public} onChange={togglePublic} data-testid="public-toggle"/>
              <span>Public (eligible for leaderboard)</span>
            </label>
          </div>
        </div>
      )}

      {job.status === "completed" && (
        <div className="flex flex-wrap gap-3 mt-5" data-testid="downloads-row">
          <a href={dlUrl} data-testid="download-btn" className="btn btn-primary">
            <Download size={14}/> SafeTensors (.tar) · {(job.output_size_gb || 0).toFixed(2)}GB
          </a>
          {job.gguf_path ? (
            <a href={ggufUrl} data-testid="download-gguf-btn" className="btn btn-ghost">
              <Download size={14}/> GGUF Q4_K_M · {((job.gguf_size_mb||0)/1024).toFixed(2)}GB
            </a>
          ) : (
            <span className="text-xs text-muted self-center" data-testid="gguf-pending">GGUF Q4_K_M: converting in background…</span>
          )}
        </div>
      )}
      {job.error && <div className="mt-4 text-red-300 border border-red-900/50 bg-red-950/30 rounded p-3 text-sm" data-testid="job-error-detail">Error: {job.error}</div>}
    </div>
  );
}
