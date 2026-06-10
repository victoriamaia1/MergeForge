import { useEffect, useState } from "react";
import { api } from "../api";
import { Link } from "react-router-dom";
import { Cpu, HardDrive, Database, Flame, GitMerge, CheckCircle2, XCircle, Loader2, Clock, ArrowRight } from "lucide-react";

const TIER_COPY = {
  TIER_1: { tag: "CPU-only mode", warn: "Merges will be slow (~hours). Limited to ≤13B and 2-model merges.", color: "text-amber-300" },
  TIER_2: { tag: "Modest GPU", warn: "Up to 30B and 3-way merges. ~hour scale.", color: "text-sky-300" },
  TIER_3: { tag: "High-end GPU", warn: "Fast 70B merges, 4-way batches enabled.", color: "text-accent" },
  TIER_4: { tag: "Ultra-scale", warn: "Everything unlocked, MoE-merge experimental.", color: "text-fuchsia-300" },
};

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [live, setLive] = useState(null);
  const [me, setMe] = useState(null);
  useEffect(() => {
    api.get("/api/auth/me").then(r=>setMe(r.data));
    const load = async () => {
      try {
        const [s,l] = await Promise.all([api.get("/api/dashboard/stats"), api.get("/api/hardware/live")]);
        setStats(s.data); setLive(l.data);
      } catch(e){}
    };
    load(); const t = setInterval(load, 4000); return ()=>clearInterval(t);
  }, []);

  if (!stats || !live) return <div className="text-muted">Loading…</div>;
  const hw = stats.hardware;
  const t = TIER_COPY[hw.tier] || TIER_COPY.TIER_1;

  const StatCard = ({label, value, icon:I, sub}) => (
    <div className="card p-5">
      <div className="flex items-center justify-between">
        <div className="text-xs uppercase tracking-wider text-muted">{label}</div>
        <I size={16} className="text-accent"/>
      </div>
      <div className="font-display text-3xl mt-2" data-testid={`stat-${label.toLowerCase().replace(/ /g,"-")}`}>{value}</div>
      {sub && <div className="text-xs text-muted mt-1">{sub}</div>}
    </div>
  );

  return (
    <div data-testid="dashboard-root" className="max-w-6xl">
      <div className="flex items-end justify-between gap-4 mb-8">
        <div>
          <div className="chip mb-2">Workstation overview</div>
          <h1 className="font-display text-3xl md:text-4xl">Hello, <span className="text-accent">{me?.username||"…"}</span></h1>
          <p className={`mt-2 text-sm ${t.color}`} data-testid="tier-banner">{t.tag} — {t.warn}</p>
        </div>
        <Link to="/app/create" className="btn btn-primary" data-testid="new-merge-cta"><GitMerge size={14}/> New merge</Link>
      </div>

      <div className="card p-4 mb-6 flex flex-wrap items-center gap-4 justify-between" data-testid="tier-card">
        <div>
          <div className="chip">Account tier</div>
          <div className="font-display text-xl mt-1 capitalize">
            <span className="text-accent" data-testid="tier-label">{stats.tier}</span> plan
          </div>
          <div className="text-xs text-muted mt-1">
            Daily merges used:&nbsp;
            <span className="font-display text-zinc-100" data-testid="daily-usage">
              {stats.used_today}{stats.daily_limit < 0 ? " (unlimited)" : ` / ${stats.daily_limit}`}
            </span>
          </div>
        </div>
        {stats.tier === "free" && (
          <div className="text-xs text-amber-300 max-w-md" data-testid="upgrade-prompt">
            On the free plan you can run {stats.daily_limit} merges per day. Upgrade to <b>pro</b> for {20}/day, or <b>enterprise</b> for unlimited capacity.
          </div>
        )}
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 stagger">
        <StatCard label="Total merges" value={stats.total_jobs} icon={Flame}/>
        <StatCard label="Completed" value={stats.completed} icon={CheckCircle2}/>
        <StatCard label="Running / Queued" value={`${stats.running} / ${stats.queued}`} icon={Loader2}/>
        <StatCard label="Output disk" value={`${(stats.output_disk_used_mb/1024).toFixed(2)} GB`} icon={HardDrive}/>
      </div>

      <div className="grid lg:grid-cols-2 gap-4 mt-6">
        <div className="card p-6 dot-grid">
          <div className="flex items-center justify-between">
            <div>
              <div className="chip">Hardware live</div>
              <div className="font-display text-xl mt-2">{hw.tier_label}</div>
            </div>
            <Cpu className="text-accent" size={22}/>
          </div>
          <div className="mt-4 grid grid-cols-3 gap-3 text-sm">
            <div><div className="text-muted text-xs">CPU</div><div className="font-display">{live.cpu_pct.toFixed(0)}%</div></div>
            <div><div className="text-muted text-xs">RAM used</div><div className="font-display">{live.ram_used_pct.toFixed(0)}%</div></div>
            <div><div className="text-muted text-xs">Free disk</div><div className="font-display">{(live.disk_free_mb/1024).toFixed(0)} GB</div></div>
          </div>
          <Link to="/app/hardware" className="btn btn-ghost mt-5 text-sm">Hardware detail <ArrowRight size={14}/></Link>
        </div>

        <div className="card p-6">
          <div className="chip">Capabilities</div>
          <div className="font-display text-xl mt-2">What this rig can merge</div>
          <ul className="mt-3 text-sm text-zinc-200 space-y-2">
            <li>Max model size: <span className="font-display text-accent">{hw.capabilities.max_params_b}B</span> parameters</li>
            <li>Max simultaneous models per merge: <span className="font-display text-accent">{hw.capabilities.max_concurrent_models}</span></li>
            <li>Compression required: <span className="font-display">{hw.capabilities.compression_required?"Yes (INT4 forced)":"No (FP16 OK)"}</span></li>
            <li>Time multiplier vs Tier 3: <span className="font-display">×{hw.capabilities.merge_time_multiplier}</span></li>
          </ul>
          <Link to="/app/models" className="btn btn-ghost mt-4 text-sm">Browse compatible models <ArrowRight size={14}/></Link>
        </div>
      </div>
    </div>
  );
}
