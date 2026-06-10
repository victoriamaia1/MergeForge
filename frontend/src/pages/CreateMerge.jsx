import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useNavigate } from "react-router-dom";
import { Plus, Trash2, GitMerge, AlertTriangle, CheckCircle2, ArrowRight } from "lucide-react";

const METHODS = [
  {id:"linear", label:"Linear (weighted average)"},
  {id:"ties", label:"TIES (trim/elect/dare)"},
  {id:"dare_ties", label:"DARE-TIES"},
  {id:"slerp", label:"SLERP (2-model only)"},
  {id:"passthrough", label:"Passthrough"},
];

export default function CreateMerge() {
  const [allModels, setAllModels] = useState([]);
  const [hw, setHw] = useState(null);
  const [name, setName] = useState("");
  const [method, setMethod] = useState("linear");
  const [picks, setPicks] = useState([]); // {id, weight}
  const [compression, setCompression] = useState("auto");
  const [notes, setNotes] = useState("");
  const [validation, setValidation] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const nav = useNavigate();

  useEffect(() => {
    api.get("/api/models?include_incompatible=false").then(r=> setAllModels(r.data.items));
    api.get("/api/hardware/profile").then(r=>setHw(r.data));
  }, []);

  // Auto-validate as user configures the merge (debounced)
  useEffect(() => {
    if (picks.length < 2 || !name.trim()) { setValidation(null); return; }
    const t = setTimeout(async () => {
      try {
        const r = await api.post("/api/merge/validate", { name, method, models: picks, compression });
        setValidation(r.data);
      } catch(e) { /* keep silent, validation is hint */ }
    }, 400);
    return () => clearTimeout(t);
  }, [picks, name, method, compression]);

  const maxModels = hw?.capabilities?.max_concurrent_models || 2;

  const addPick = (id) => {
    if (picks.find(p=>p.id===id)) return;
    if (picks.length >= maxModels) return;
    const w = 1 / (picks.length+1);
    setPicks([...picks.map(p=>({...p, weight:w})), { id, weight:w }]);
  };
  const removePick = (id) => setPicks(picks.filter(p=>p.id!==id).map((p,_,arr)=>({ ...p, weight: 1/arr.length })));
  const setWeight = (id, w) => setPicks(picks.map(p=>p.id===id?{...p,weight:Number(w)}:p));

  const validate = async () => {
    setErr(""); setValidation(null);
    if (picks.length < 2) { setErr("Pick at least 2 models"); return; }
    if (!name) { setErr("Give the merge a name"); return; }
    try {
      const r = await api.post("/api/merge/validate", { name, method, models: picks, compression });
      setValidation(r.data);
    } catch(e) { setErr(e.response?.data?.detail || "Validation failed"); }
  };
  const submit = async () => {
    setErr("");
    if (picks.length < 2) { setErr("Pick at least 2 models"); return; }
    if (!name.trim()) { setErr("Give the merge a name"); return; }
    setBusy(true);
    try {
      // Always validate fresh before submitting
      let v = validation;
      if (!v || v.status !== "OK") {
        const vr = await api.post("/api/merge/validate", { name, method, models: picks, compression });
        v = vr.data;
        setValidation(v);
        if (v.status !== "OK") {
          setErr("Cannot merge: " + (v.blockers?.join("; ") || "see details below"));
          setBusy(false);
          return;
        }
      }
      const r = await api.post("/api/merge/create", { name, method, models: picks, compression, notes });
      nav(`/app/jobs/${r.data.job_id}`);
    } catch(e) {
      console.error("Merge create failed", e);
      setErr(e.response?.data?.detail || e.message || "Failed to start merge");
    }
    finally { setBusy(false); }
  };

  return (
    <div data-testid="create-merge-root" className="max-w-5xl">
      <div className="chip mb-2">New merge</div>
      <h1 className="font-display text-3xl md:text-4xl">Configure your fusion</h1>
      <p className="text-muted mt-2 text-sm">Hardware tier: <span className="text-accent">{hw?.tier_label||"…"}</span> · max {maxModels} models per merge</p>

      <div className="grid lg:grid-cols-3 gap-6 mt-8">
        <div className="lg:col-span-2 space-y-5">
          <div className="card p-5">
            <div className="text-xs uppercase tracking-wider text-muted mb-2">Merge name</div>
            <input data-testid="merge-name-input" value={name} onChange={e=>setName(e.target.value)} className="input" placeholder="my-mistral-zephyr-blend"/>
          </div>

          <div className="card p-5">
            <div className="text-xs uppercase tracking-wider text-muted mb-2">Method</div>
            <div className="grid sm:grid-cols-2 gap-2">
              {METHODS.map(m => (
                <button key={m.id} data-testid={`method-${m.id}`} onClick={()=>setMethod(m.id)}
                  className={`border rounded-md p-3 text-left text-sm transition-colors ${method===m.id?"border-accent bg-edge text-accent":"border-line text-zinc-300 hover:bg-edge/40"}`}>
                  <div className="font-display">{m.label}</div>
                  <div className="text-xs text-muted mt-0.5">{m.id}</div>
                </button>
              ))}
            </div>
          </div>

          <div className="card p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="text-xs uppercase tracking-wider text-muted">Selected models ({picks.length}/{maxModels})</div>
            </div>
            {picks.length === 0 && <div className="text-sm text-muted">Pick from the list on the right.</div>}
            <div className="space-y-2">
              {picks.map(p => {
                const m = allModels.find(x=>x.id===p.id);
                return (
                  <div key={p.id} data-testid={`picked-${p.id}`} className="border border-line rounded-md p-3 flex items-center gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="font-display truncate">{m?.name || p.id}</div>
                      <div className="text-xs text-muted truncate">{p.id}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <label className="text-xs text-muted">w</label>
                      <input data-testid={`weight-${p.id}`} type="number" step="0.05" min="0" max="2" value={p.weight.toFixed(2)} onChange={e=>setWeight(p.id, e.target.value)} className="input w-20 text-sm"/>
                      <button data-testid={`remove-${p.id}`} onClick={()=>removePick(p.id)} className="btn btn-danger"><Trash2 size={14}/></button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="card p-5">
            <div className="text-xs uppercase tracking-wider text-muted mb-2">Compression</div>
            <div className="flex gap-2 flex-wrap">
              {["auto","fp16","int8","int4"].map(c => (
                <button key={c} data-testid={`compress-${c}`} onClick={()=>setCompression(c)}
                  className={`btn ${compression===c?"btn-primary":"btn-ghost"} text-sm`}>{c.toUpperCase()}</button>
              ))}
            </div>
            <div className="text-xs text-muted mt-2">{hw?.capabilities?.compression_required ? "CPU-only tier: INT4 forced for safety." : "FP16 fine on GPU. INT4 if you want smaller output."}</div>
          </div>

          <div className="card p-5">
            <div className="text-xs uppercase tracking-wider text-muted mb-2">Notes (optional)</div>
            <textarea data-testid="merge-notes" value={notes} onChange={e=>setNotes(e.target.value)} className="input h-20" placeholder="What is this merge for?"/>
          </div>

          <div className="flex gap-3">
            <button data-testid="validate-btn" onClick={validate} className="btn btn-ghost">Validate</button>
            <button data-testid="start-merge-btn" disabled={busy || picks.length < 2 || !name.trim()} onClick={submit} className="btn btn-primary">
              {busy ? "Queueing…" : "Start merge"} <ArrowRight size={14}/>
            </button>
          </div>
          {err && <div data-testid="merge-error" className="text-sm text-red-400 border border-red-900/60 bg-red-950/30 rounded p-2">{err}</div>}
          {validation && (
            <div data-testid="merge-validation" className={`card p-4 border-l-2 ${validation.status==="OK"?"border-accent":"border-red-500"}`}>
              <div className="flex items-center gap-2 font-display">
                {validation.status==="OK"? <CheckCircle2 className="text-accent" size={18}/> : <AlertTriangle className="text-red-400" size={18}/>}
                {validation.status==="OK" ? "Ready to merge" : "Cannot merge"}
              </div>
              <div className="text-sm mt-2 text-muted">
                Peak RAM ≈ <span className="text-zinc-200">{validation.resource_estimate.peak_ram_gb}GB</span> ·
                ETA ≈ <span className="text-zinc-200">{validation.resource_estimate.merge_time_min} min</span> ·
                Download ≈ <span className="text-zinc-200">{validation.resource_estimate.download_size_gb}GB</span> ·
                Output ≈ <span className="text-zinc-200">{validation.resource_estimate.output_size_gb}GB</span>
              </div>
              {validation.warnings.length>0 && <ul className="text-xs text-amber-300 mt-2 list-disc ml-5">{validation.warnings.map((w,i)=><li key={i}>{w}</li>)}</ul>}
              {validation.blockers.length>0 && <ul className="text-xs text-red-300 mt-2 list-disc ml-5">{validation.blockers.map((b,i)=><li key={i}>{b}</li>)}</ul>}
            </div>
          )}
        </div>

        <div className="card p-5 h-fit sticky top-6">
          <div className="text-xs uppercase tracking-wider text-muted mb-3">Compatible catalog</div>
          <div className="space-y-1 max-h-[70vh] overflow-y-auto pr-1">
            {allModels.map(m => (
              <button key={m.id} data-testid={`pick-${m.id}`} disabled={picks.find(p=>p.id===m.id)||picks.length>=maxModels}
                onClick={()=>addPick(m.id)}
                className="w-full text-left border border-line rounded-md p-2 text-sm hover:bg-edge/60 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
                <div className="font-display truncate">{m.name}</div>
                <div className="text-[10px] text-muted truncate">{m.id} · {m.params_b}B</div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
