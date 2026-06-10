import { Link } from "react-router-dom";
import { Cpu, Database, GitMerge, Gauge, Shield, ArrowRight, Flame, Zap, HardDrive } from "lucide-react";
export default function Landing() {
  return (
    <div className="grain min-h-screen">
      <header className="max-w-7xl mx-auto px-6 md:px-10 py-6 flex items-center justify-between relative z-10">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-md bg-accent text-ink flex items-center justify-center"><Flame size={20} strokeWidth={2.5}/></div>
          <div className="font-display text-lg tracking-tight">MERGE<span className="text-accent">FORGE</span></div>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/auth" data-testid="nav-signin" className="btn btn-ghost text-sm">Sign in</Link>
          <Link to="/auth?mode=signup" data-testid="nav-signup" className="btn btn-primary text-sm">Get started <ArrowRight size={14}/></Link>
        </div>
      </header>

      <section className="max-w-7xl mx-auto px-6 md:px-10 pt-12 pb-24 relative z-10">
        <div className="chip mb-6">Hardware-aware LLM fusion · Enterprise edition</div>
        <h1 className="font-display text-5xl md:text-7xl leading-[0.95] tracking-tight max-w-4xl">
          Forge merged language models <span className="gradient-text">without surprises.</span>
        </h1>
        <p className="text-muted text-lg md:text-xl max-w-2xl mt-6">
          MergeForge profiles your host, hides anything impossible, and gives honest time estimates. CPU-only? Limited to safe small merges. GPU-loaded? Everything opens up.
        </p>
        <div className="flex flex-wrap gap-3 mt-8">
          <Link to="/auth?mode=signup" data-testid="get-started-btn" className="btn btn-primary text-base">Generate signup token <ArrowRight size={16}/></Link>
          <Link to="/auth" className="btn btn-ghost text-base" data-testid="signin-token-btn">Log in with token</Link>
        </div>

        <div className="mt-20 grid md:grid-cols-3 gap-4 stagger">
          {[
            {icon:Cpu, t:"Auto hardware detection", d:"nvidia-smi, CPU flags, RAM, disk — profiled at boot."},
            {icon:GitMerge, t:"Smart model filter", d:"Only shows what your tier can actually merge."},
            {icon:Gauge, t:"Honest ETAs", d:"Time multiplier tuned per tier. No false 5-minute promises."},
            {icon:Database, t:"Lazy weight fetch", d:"Models download only when used; cache cleaned after."},
            {icon:Shield, t:"Token-based access", d:"30-word memorable tokens. No passwords to forget."},
            {icon:HardDrive, t:"Live resource guard", d:"Throttles before OOM. Rejects impossible merges."},
          ].map(({icon:I,t,d})=>(
            <div key={t} className="card p-5 dot-grid">
              <I className="text-accent" size={20}/>
              <div className="font-display text-base mt-3">{t}</div>
              <div className="text-sm text-muted mt-1">{d}</div>
            </div>
          ))}
        </div>

        <div className="mt-24 card p-8 md:p-10 relative overflow-hidden">
          <div className="absolute -right-10 -top-10 w-64 h-64 bg-accent/10 blur-3xl rounded-full"/>
          <div className="flex items-center gap-2 mb-3"><Zap className="text-accent2" size={18}/><span className="chip">Tier-aware</span></div>
          <h2 className="font-display text-3xl md:text-4xl">Four tiers. One promise.</h2>
          <div className="grid md:grid-cols-4 gap-4 mt-6">
            {[
              ["TIER 1","CPU-only","≤13B · 2 models · slower"],
              ["TIER 2","Modest GPU","≤30B · 3 models · ~hr"],
              ["TIER 3","High-end GPU","≤70B · 4 models · 25 min"],
              ["TIER 4","Ultra-scale","405B+ · MoE · 5 min"],
            ].map(([k,n,d])=>(
              <div key={k} className="border border-line rounded-md p-4 bg-ink/60">
                <div className="font-display text-accent">{k}</div>
                <div className="font-display text-lg">{n}</div>
                <div className="text-xs text-muted mt-1">{d}</div>
              </div>
            ))}
          </div>
        </div>
      </section>
      <footer className="border-t border-line py-6 text-center text-xs text-muted">MergeForge · Built for honest LLM merging.</footer>
    </div>
  );
}
