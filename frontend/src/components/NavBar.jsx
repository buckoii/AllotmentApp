import React from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../AuthContext";

const LINKS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/planner", label: "Season Planner" },
  { to: "/my-plot", label: "My Plot" },
  { to: "/harvest", label: "Harvest Log" },
  { to: "/expenses", label: "Expenses" },
];

export default function NavBar() {
  const { user, logout } = useAuth();
  return (
    <header className="nav-bar">
      <div className="nav-brand">Allotment</div>
      <nav>
        {LINKS.map((l) => (
          <NavLink key={l.to} to={l.to} end={l.end} className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
            {l.label}
          </NavLink>
        ))}
      </nav>
      <div className="nav-user">
        <span>{user?.username}</span>
        <button className="btn-link" onClick={logout}>Log out</button>
      </div>
    </header>
  );
}
