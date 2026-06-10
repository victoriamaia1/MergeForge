import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { Search, Filter, Eye, EyeOff, Cpu, CheckCircle2, XCircle, Lock } from "lucide-react";

export default function Models() {
  const [data, setData] = useState(null);
  const [q, setQ] = useState("");
  const [fam, setFam] = useState("");
  const [showHidden, setShowHidden] = useState(true);
  const [families, setFamilies] = useState([]);

  useEffect(() => { api.get("/api/models/families").then(r=>setFamilies(r.data.families)); }, []);
  useEffect(() => {
    const params = new URLSearchParams();
    params.set("include_incompatible", String(showHidden));
    if (q) params.set("search", q);
    if (fam) params.set("family", fam);
    api.get("/api/models?" + params.toString()).then(r => setData(r.data));
  }, [q, fam, showHidden]);

  if (!data) return <div className="text-muted">Loading catalog…</div>;

  return (
    <div data-testid="models-root" className="max-w-6xl">
      <div className="chip mb-2">Catalog</div>
      <h1 className="font-display text-3xl md:text-4xl">Models filtered for <span className="text-accent">{data.tier_label}</span></h1>
      <p className="text-muted mt-2 text-sm">{data.available_count} compatible · {data.incompatible_count} hidden by hardware limits</p>

      <div className="mt-6 flex flex-wrap gap-3 items-center">
        <div className="flex items-center gap-2 bg-panel border border-line rounded-md px-3 py-2 flex-1 min-w-[260px]">
          <Search size={16} className="text-muted"/>
          <input data-testid="model-search-input" value={q} onChange={e=>setQ(e.target.value)} className="bg-transparent outline-none flex-1 text-sm" placeholder="search by name, family or id"/>
        </div>
        <select data-testid="model-family-select" value={fam} onChange={e=>setFam(e.target.value)} className="input max-w-[200px] text-sm">
          <option value="">All families</option>
          {families.map(f=> <option key={f} value={f}>{f}</option>)}
        </select>
        <button data-testid="toggle-hidden-btn" onClick={()=>setShowHidden(v=>!v)} className="btn btn-ghost text-sm">
          {showHidden ? <><EyeOff size={14}/> Hide incompatible</> : <><Eye size={14}/> Show incompatible</>}
        </button>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-6 stagger">
        {data.items.map(m => {
          const ok = m.compatibility.can_use;
          return (
            <div key={m.id} data-testid={`model-card-${m.id}`} className={`card p-5 transition-transform hover:-translate-y-0.5 ${ok?"":"opacity-60"}`}>
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-display text-lg leading-tight">{m.name}</div>
                  <div className="text-xs text-muted mt-0.5">{m.id}</div>
                </div>
                {ok ? <CheckCircle2 className="text-accent" size={18}/> : <Lock className="text-red-400" size={18}/>}
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5">
                <span className="chip">{m.params_b}B</span>
                <span className="chip">{m.family}</span>
                <span className="chip">{m.context_length.toLocaleString()} ctx</span>
                <span className="chip">{m.tier_min}</span>
              </div>
              <div className="mt-3 text-xs text-muted">
                FP16 ~{m.size_gb_fp16}GB · INT4 ~{m.quantized_size_gb}GB · merge≈{m.compatibility.merge_time_min_estimate}m
              </div>
              {m.compatibility.warnings.length>0 && (
                <div className="mt-2 text-[11px] text-amber-300 border border-amber-900/50 bg-amber-950/30 rounded p-2">
                  {m.compatibility.warnings.join(" · ")}
                </div>
              )}
              {m.compatibility.blockers.length>0 && (
                <div className="mt-2 text-[11px] text-red-300 border border-red-900/50 bg-red-950/30 rounded p-2" data-testid="model-blocker">
                  {m.compatibility.blockers.join(" · ")}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
