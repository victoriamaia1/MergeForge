import { useEffect, useState } from "react";
import { api } from "../api";
import { Cpu, HardDrive, Database, Activity } from "lucide-react";

export default function Hardware() {
  const [hw, setHw] = useState(null);
  const [live, setLive] = useState(null);
  useEffect(() => {
    api.get("/api/hardware/profile").then(r=>setHw(r.data));
    const load = ()=> api.get("/api/hardware/live").then(r=>setLive(r.data));
    load(); const t = setInterval(load, 2000); return ()=>clearInterval(t);
  }, []);
  if (!hw || !live) return <div className="text-muted">Loading…</div>;

  const Bar = ({label, pct, sub}) => (
    <div>
      <div className="flex justify-between text-xs text-muted mb-1"><span>{label}</span><span>{sub}</span></div>
      <div className="h-2 bg-edge rounded-full overflow-hidden"><div className="h-full bg-accent transition-all" style={{width:`${pct}%`}}/></div>
    </div>
  );

  return (
    <div data-testid="hardware-root" className="max-w-5xl">
      <div className="chip mb-2">System profile</div>
      <h1 className="font-display text-3xl md:text-4xl">{hw.tier_label} · <span className="text-accent">{hw.tier}</span></h1>

      <div className="grid md:grid-cols-2 gap-4 mt-6 stagger">
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-3"><Cpu className="text-accent" size={18}/><div className="font-display">CPU</div></div>
          <div className="text-sm text-zinc-200">{hw.cpu.brand}</div>
          <div className="text-xs text-muted mt-1">{hw.cpu.cores_physical} physical · {hw.cpu.cores_logical} logical · {hw.cpu.freq_mhz} MHz</div>
          <div className="mt-2 flex gap-1.5"><span className="chip">{hw.cpu.has_avx?"AVX":"no-AVX"}</span><span className="chip">{hw.cpu.has_avx512?"AVX-512":"no-AVX512"}</span></div>
          <div className="mt-4"><Bar label="CPU usage" pct={live.cpu_pct} sub={`${live.cpu_pct.toFixed(0)}%`}/></div>
        </div>

        <div className="card p-5">
          <div className="flex items-center gap-2 mb-3"><Activity className="text-accent" size={18}/><div className="font-display">GPU</div></div>
          {hw.gpu.available ? (
            <>
              <div className="text-sm text-zinc-200">{hw.gpu.type} × {hw.gpu.count}</div>
              <ul className="text-xs text-muted mt-1">{hw.gpu.gpus.map((g,i)=> <li key={i}>{g.name} — {(g.vram_mb/1024).toFixed(1)}GB VRAM</li>)}</ul>
            </>
          ) : (
            <div className="text-sm text-amber-300">No GPU detected — running in CPU-only mode.</div>
          )}
        </div>

        <div className="card p-5">
          <div className="flex items-center gap-2 mb-3"><Database className="text-accent" size={18}/><div className="font-display">RAM</div></div>
          <div className="text-sm">{(hw.ram.total_mb/1024).toFixed(1)} GB total · {(live.ram_available_mb/1024).toFixed(1)} GB available</div>
          <div className="mt-3"><Bar label="RAM used" pct={live.ram_used_pct} sub={`${live.ram_used_pct.toFixed(0)}%`}/></div>
        </div>

        <div className="card p-5">
          <div className="flex items-center gap-2 mb-3"><HardDrive className="text-accent" size={18}/><div className="font-display">Storage</div></div>
          <div className="text-sm">{(hw.storage.total_mb/1024).toFixed(0)} GB total · {(live.disk_free_mb/1024).toFixed(0)} GB free</div>
          <div className="mt-3"><Bar label="Disk used" pct={100 - 100*live.disk_free_mb/hw.storage.total_mb} sub={`${(100 - 100*live.disk_free_mb/hw.storage.total_mb).toFixed(0)}%`}/></div>
        </div>
      </div>

      <div className="card p-5 mt-6">
        <div className="text-xs uppercase tracking-wider text-muted mb-2">Capabilities for this tier</div>
        <ul className="text-sm space-y-1">
          <li>Max model size: <span className="font-display text-accent">{hw.capabilities.max_params_b}B</span></li>
          <li>Max models per merge: <span className="font-display text-accent">{hw.capabilities.max_concurrent_models}</span></li>
          <li>Compression required: <span className="font-display">{hw.capabilities.compression_required?"Yes":"No"}</span></li>
          <li>Merge time multiplier: <span className="font-display">×{hw.capabilities.merge_time_multiplier}</span></li>
          <li>Supports batch merging: <span className="font-display">{hw.capabilities.supports_batch?"Yes":"No"}</span></li>
          <li>Supports MoE-merge: <span className="font-display">{hw.capabilities.supports_moe_merge?"Yes":"No"}</span></li>
        </ul>
      </div>
    </div>
  );
}
