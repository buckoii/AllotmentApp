import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.get("/dashboard").then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="form-error">{error}</p>;
  if (!data) return <p>Loading...</p>;

  return (
    <div className="page">
      <h1>Today</h1>

      <div className="stat-row">
        <div className="stat-card stat-positive">
          <span className="stat-label">Value saved (harvested)</span>
          <span className="stat-value">£{data.value_saved_total.toFixed(2)}</span>
        </div>
        <div className="stat-card stat-negative">
          <span className="stat-label">Spent</span>
          <span className="stat-value">£{data.expenses_total.toFixed(2)}</span>
        </div>
        <div className={`stat-card ${data.net_total >= 0 ? "stat-positive" : "stat-negative"}`}>
          <span className="stat-label">Net</span>
          <span className="stat-value">£{data.net_total.toFixed(2)}</span>
        </div>
      </div>

      <section>
        <h2>Tasks due</h2>
        {data.tasks_due.length === 0 && <p className="empty-hint">Nothing due - check back tomorrow.</p>}
        <ul className="task-list">
          {data.tasks_due.map((t) => (
            <li key={t.planting_id} className={t.overdue ? "task-row task-row-overdue" : "task-row"}>
              <span>{t.plant_name}{t.plant_variety ? ` (${t.plant_variety})` : ""} - {t.label}</span>
              <span className="task-due-date">{t.overdue ? "Overdue since " : "Due "}{t.due_date}</span>
            </li>
          ))}
        </ul>
        {data.tasks_due.length > 0 && <Link className="btn-link" to="/my-plot">View on My Plot &rarr;</Link>}
      </section>

      <section>
        <h2>Succession sowing reminders</h2>
        {data.succession_reminders.length === 0 && <p className="empty-hint">No successions due right now.</p>}
        <ul className="task-list">
          {data.succession_reminders.map((s) => (
            <li key={s.plant_id} className="task-row">
              <span>Time to sow more {s.plant_name}{s.plant_variety ? ` (${s.plant_variety})` : ""}</span>
              <span className="task-due-date">last sown {s.last_sown}</span>
            </li>
          ))}
        </ul>
        {data.succession_reminders.length > 0 && <Link className="btn-link" to="/planner">Go to Season Planner &rarr;</Link>}
      </section>

      <section>
        <h2>Fruit bushes in season</h2>
        {data.bushes_fruiting_now.length === 0 && <p className="empty-hint">Nothing fruiting right now.</p>}
        <ul className="task-list">
          {data.bushes_fruiting_now.map((b) => (
            <li key={b.bush_id} className="task-row">
              <span>{b.plant_name}{b.plant_variety ? ` (${b.plant_variety})` : ""} should be fruiting - go pick it</span>
            </li>
          ))}
        </ul>
        {data.bushes_fruiting_now.length > 0 && <Link className="btn-link" to="/bushes">View Fruit Bushes &rarr;</Link>}
      </section>

      <section>
        <h2>Watering &amp; feeding due today</h2>
        {data.care_tasks_due_today === 0 ? (
          <p className="empty-hint">Nothing due today.</p>
        ) : (
          <p>{data.care_tasks_due_today} task{data.care_tasks_due_today === 1 ? "" : "s"} due today.</p>
        )}
        <Link className="btn-link" to="/care">View full schedule &rarr;</Link>
      </section>
    </div>
  );
}
