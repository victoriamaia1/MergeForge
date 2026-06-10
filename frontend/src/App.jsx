import React, { useEffect, useState } from "react";
import { Routes, Route, Navigate, useNavigate, Link, useLocation } from "react-router-dom";
import { api, tokenStore } from "./api";
import Landing from "./pages/Landing.jsx";
import Auth from "./pages/Auth.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Models from "./pages/Models.jsx";
import CreateMerge from "./pages/CreateMerge.jsx";
import Jobs from "./pages/Jobs.jsx";
import JobDetail from "./pages/JobDetail.jsx";
import Hardware from "./pages/Hardware.jsx";
import Leaderboard from "./pages/Leaderboard.jsx";
import Sidebar from "./components/Sidebar.jsx";

function Protected({ children }) {
  const t = tokenStore.get();
  if (!t) return <Navigate to="/auth" replace />;
  return children;
}

function Shell({ children }) {
  return (
    <div className="grain min-h-screen flex">
      <Sidebar />
      <main className="flex-1 min-w-0 p-6 md:p-10 relative z-10">{children}</main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/auth" element={<Auth />} />
      <Route path="/leaderboard" element={<Leaderboard />} />
      <Route path="/app" element={<Protected><Shell><Dashboard/></Shell></Protected>} />
      <Route path="/app/models" element={<Protected><Shell><Models/></Shell></Protected>} />
      <Route path="/app/create" element={<Protected><Shell><CreateMerge/></Shell></Protected>} />
      <Route path="/app/jobs" element={<Protected><Shell><Jobs/></Shell></Protected>} />
      <Route path="/app/jobs/:id" element={<Protected><Shell><JobDetail/></Shell></Protected>} />
      <Route path="/app/hardware" element={<Protected><Shell><Hardware/></Shell></Protected>} />
      <Route path="/app/leaderboard" element={<Protected><Shell><Leaderboard embedded/></Shell></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
