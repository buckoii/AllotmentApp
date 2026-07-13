import React, { useEffect, useState } from "react";
import { api } from "../api";

export default function CareSchedule() {
  const [entries, setEntries] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.get("/care-schedule").then(setEntries).catch((e) => setError(e.message));
  }, []);

  return (
    <div className="page">
      <h1>Watering &amp; Feeding</h1>
      <p className="page-subtitle">
        Guideline reminders based on each plant/bush's typical needs from the catalog - not a log
        of what you've actually done, just how often it should roughly need doing.
      </p>
      {error && <p className="form-error">{error}</p>}
      {entries.length === 0 && <p className="empty-hint">Nothing active to water or feed yet.</p>}
      <ul className="task-list">
        {entries.map((e, i) => (
          <li key={i} className={e.due_today ? "task-row task-row-overdue" : "task-row"}>
            <span>
              {e.task === "water" ? "Water" : "Feed"} {e.plant_name}{e.plant_variety ? ` (${e.plant_variety})` : ""}
              {" "}
              <span className="empty-hint">
                ({e.source === "bush" ? "bush" : "plot"}, every {e.frequency_days} days)
              </span>
            </span>
            <span className="task-due-date">{e.due_today ? "Due today" : `Due ${e.due_date}`}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
