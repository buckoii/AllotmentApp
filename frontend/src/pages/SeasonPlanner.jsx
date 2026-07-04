import React, { useEffect, useState } from "react";
import { api } from "../api";
import PlantCard from "../components/PlantCard";

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

export default function SeasonPlanner() {
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [category, setCategory] = useState("");
  const [sortBy, setSortBy] = useState("value");
  const [plants, setPlants] = useState([]);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  const load = () => {
    const params = new URLSearchParams({ month: String(month) });
    if (category) params.set("category", category);
    api.get(`/catalog?${params}`).then(setPlants).catch((e) => setError(e.message));
  };

  useEffect(load, [month, category]);

  const sorted = [...plants].sort((a, b) => {
    if (sortBy === "value") {
      return (b.value_per_sqm_per_week || 0) - (a.value_per_sqm_per_week || 0);
    }
    return a.name.localeCompare(b.name);
  });

  const handlePlant = async (payload) => {
    setMessage(null);
    setError(null);
    try {
      await api.post("/plantings", payload);
      setMessage("Logged - check My Plot to track it.");
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="page">
      <h1>Season Planner</h1>
      <p className="page-subtitle">What can go in the ground this month, ranked by value.</p>

      <div className="filter-row">
        <label>
          Month
          <select value={month} onChange={(e) => setMonth(Number(e.target.value))}>
            {MONTHS.map((m, i) => (
              <option key={m} value={i + 1}>{m}</option>
            ))}
          </select>
        </label>
        <label>
          Type
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">All</option>
            <option value="veg">Veg</option>
            <option value="fruit">Fruit</option>
            <option value="herb">Herb</option>
          </select>
        </label>
        <label>
          Sort by
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            <option value="value">Value (£/m²/week)</option>
            <option value="name">Name</option>
          </select>
        </label>
      </div>

      {message && <p className="form-success">{message}</p>}
      {error && <p className="form-error">{error}</p>}

      <div className="plant-grid">
        {sorted.map((p) => (
          <PlantCard key={p.id} plant={p} onPlant={handlePlant} />
        ))}
      </div>
      {sorted.length === 0 && <p className="empty-hint">Nothing sowable in {MONTHS[month - 1]} for this filter.</p>}
    </div>
  );
}
