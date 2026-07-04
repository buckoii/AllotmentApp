import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./AuthContext";
import NavBar from "./components/NavBar";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import SeasonPlanner from "./pages/SeasonPlanner";
import MyPlot from "./pages/MyPlot";
import HarvestLog from "./pages/HarvestLog";
import Expenses from "./pages/Expenses";

function Shell() {
  const { user } = useAuth();

  if (user === undefined) {
    return <div className="loading-screen">Loading...</div>;
  }
  if (user === null) {
    return <Login />;
  }

  return (
    <div className="app-shell">
      <NavBar />
      <main className="app-main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/planner" element={<SeasonPlanner />} />
          <Route path="/my-plot" element={<MyPlot />} />
          <Route path="/harvest" element={<HarvestLog />} />
          <Route path="/expenses" element={<Expenses />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Shell />
    </AuthProvider>
  );
}
