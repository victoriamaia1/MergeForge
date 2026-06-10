import { Link, useLocation, useNavigate } from "react-router-dom";
import { LayoutDashboard, Cpu, Library, GitMerge, ListChecks, LogOut, Flame, Trophy } from "lucide-react";
import { tokenStore } from "../api";

const links = [
  { to: "/app",          icon: LayoutDashboard, label: "Dashboard" },
  { to: "/app/models",   icon: Library,         label: "Model Catalog" },
  { to: "/app/create",   icon: GitMerge,        label: "New Merge" },
  { to: "/app/jobs",     icon: ListChecks,      label: "Merge Jobs" },
  { to: "/app/leaderboard", icon: Trophy,       label: "Leaderboard" },
  { to: "/app/hardware", icon: Cpu,             label: "Hardware" },
];
export default function Sidebar() {
  const { pathname } = useLocation();
  const nav = useNavigate();
  const logout = () => { tokenStore.clear(); nav("/"); };
  return (
    <aside data-testid="sidebar" className="w-64 shrink-0 border-r border-line bg-panel/60 backdrop-blur-md hidden md:flex flex-col p-5 sticky top-0 h-screen">
      <Link to="/app" data-testid="sidebar-logo" className="flex items-center gap-2 mb-8">
        <div className="w-9 h-9 rounded-md bg-accent text-ink flex items-center justify-center"><Flame size={20} strokeWidth={2.5}/></div>
        <div className="font-display text-lg tracking-tight">MERGE<span className="text-accent">FORGE</span></div>
      </Link>
      <nav className="flex flex-col gap-1">
        {links.map(({to,icon:Icon,label}) => {
          const active = pathname === to || (to !== "/app" && pathname.startsWith(to));
          return (
            <Link
              key={to} to={to} data-testid={`nav-${label.toLowerCase().replace(/ /g,"-")}`}
              className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${active ? "bg-edge text-accent border border-line" : "text-zinc-300 hover:bg-edge/60"}`}>
              <Icon size={16}/> {label}
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto pt-6 border-t border-line">
        <button onClick={logout} data-testid="logout-btn" className="btn btn-ghost w-full justify-start text-zinc-400 hover:text-red-300">
          <LogOut size={14}/> Log out
        </button>
      </div>
    </aside>
  );
}
