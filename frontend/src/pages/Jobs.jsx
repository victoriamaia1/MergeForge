import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Loader2, CheckCircle2, XCircle, Clock, Trash2, ArrowRight, GitMerge } from "lucide-react";

const ICONS = { running: Loader2, completed: CheckCircle2, failed: XCircle, queued: Clock };

export default function Jobs() {
  const [jobs, setJobs] = useState([]);
  const load = async () => { const r = await api.get("/api/merge/jobs"); setJobs(r.data); };
  useEffect(() => { load(); const t = setInterval(load, 2500); return ()=>clearInterval(t); }, []);
  const del = async (id) => { if (confirm("Delete this merge and its output?")) { await api.delete(`/api/merge/jobs/${id}`); load(); } };

  return (
    <div data-testid="jobs-root" className="max-w-5xl">
      <div className="flex items-end justify-between mb-6">
        <div>
          <div className="chip mb-2">Job queue</div>
          <h1 className="font-display text-3xl md:text-4xl">All merges</h1>
        </div>
        <Link to="/app/create" className="btn btn-primary" data-testid="new-merge-btn"><GitMerge size={14}/> New merge</Link>
      </div>

      {jobs.length===0 && <div className="card p-10 text-center text-muted">No jobs yet. Create your first merge.</div>}
      <div className="space-y-3 stagger">
        {jobs.map(j => {
          const Icon = ICONS[j.status] || Clock;
          return (
            <div key={j.id} data-testid={`job-row-${j.id}`} className="card p-4 flex items-center gap-4">
              <Icon size={20} className={j.status==="completed"?"text-accent":j.status==="failed"?"text-red-400":j.status==="running"?"text-amber-300 animate-spin":"text-muted"}/>
              <div className="flex-1 min-w-0">
                <div className="font-display truncate">{j.name}</div>
                <div className="text-xs text-muted truncate">{j.method} · {j.models.length} models · ETA {j.estimated_minutes}m · {j.stage}</div>
                <div className="h-1.5 mt-2 bg-edge rounded-full overflow-hidden">
                  <div className="h-full bg-accent transition-all" style={{width: `${j.progress}%`}}/>
                </div>
              </div>
              <Link to={`/app/jobs/${j.id}`} data-testid={`open-job-${j.id}`} className="btn btn-ghost text-sm">Open <ArrowRight size={14}/></Link>
              <button data-testid={`del-job-${j.id}`} onClick={()=>del(j.id)} className="btn btn-danger"><Trash2 size={14}/></button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
