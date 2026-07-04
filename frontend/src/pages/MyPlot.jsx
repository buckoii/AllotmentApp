import React, { useEffect, useState } from "react";
import { api } from "../api";
import ProgressBar from "../components/ProgressBar";
import TaskBadge from "../components/TaskBadge";

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function PlantingCard({ planting, onRefresh }) {
  const [stageDate, setStageDate] = useState(todayIso());
  const [harvestGrams, setHarvestGrams] = useState("");
  const [showHarvestForm, setShowHarvestForm] = useState(false);
  const [bedMates, setBedMates] = useState(null);
  const [error, setError] = useState(null);

  const task = planting.next_task;

  const markTransplanted = async () => {
    setError(null);
    try {
      await api.patch(`/plantings/${planting.id}`, { transplanted_date: stageDate });
      onRefresh();
    } catch (e) {
      setError(e.message);
    }
  };

  const logHarvest = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/harvests", {
        planting_id: planting.id,
        harvest_date: stageDate,
        quantity_g: Number(harvestGrams),
      });
      setShowHarvestForm(false);
      setHarvestGrams("");
      onRefresh();
    } catch (e) {
      setError(e.message);
    }
  };

  const closeOut = async () => {
    setError(null);
    try {
      await api.patch(`/plantings/${planting.id}`, { status: "harvested", last_harvest_date: stageDate });
      onRefresh();
    } catch (e) {
      setError(e.message);
    }
  };

  const loadBedMates = async () => {
    try {
      setBedMates(await api.get(`/plantings/${planting.id}/bed-sharing`));
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="planting-card">
      <div className="planting-card-header">
        <h3>{planting.plant.name}{planting.plant.variety ? ` (${planting.plant.variety})` : ""}</h3>
        <span className="planting-sow-date">Sown {planting.sow_date}</span>
      </div>

      <ProgressBar percent={planting.progress_percent} color={planting.progress_color} />
      <div className="planting-meta-row">
        <span>{planting.progress_percent}% to expected harvest</span>
        <TaskBadge task={task} />
      </div>

      {error && <p className="form-error">{error}</p>}

      <div className="planting-actions">
        {task?.label === "Transplant outdoors" && (
          <div className="inline-action">
            <input type="date" value={stageDate} onChange={(e) => setStageDate(e.target.value)} />
            <button className="btn-primary" onClick={markTransplanted}>Mark transplanted</button>
          </div>
        )}

        {(task?.label === "Check for harvest" || task?.label === "Finish harvesting / close out bed") && (
          <>
            {!showHarvestForm ? (
              <button className="btn-primary" onClick={() => setShowHarvestForm(true)}>Log a harvest</button>
            ) : (
              <form className="inline-action" onSubmit={logHarvest}>
                <input type="date" value={stageDate} onChange={(e) => setStageDate(e.target.value)} />
                <input type="number" min="0" step="1" placeholder="grams" value={harvestGrams} onChange={(e) => setHarvestGrams(e.target.value)} required />
                <button type="submit" className="btn-primary">Save</button>
                <button type="button" className="btn-link" onClick={() => setShowHarvestForm(false)}>Cancel</button>
              </form>
            )}
            {task?.label === "Finish harvesting / close out bed" && (
              <button className="btn-link" onClick={closeOut}>Mark bed cleared</button>
            )}
          </>
        )}

        <button className="btn-link" onClick={loadBedMates}>Suggest bed-mates</button>
      </div>

      {bedMates && (
        <div className="bed-mates">
          {bedMates.length === 0 ? (
            <p className="empty-hint">Nothing in the catalog fits the remaining time/month.</p>
          ) : (
            <p>Could fit alongside: {bedMates.map((m) => m.name).join(", ")}</p>
          )}
        </div>
      )}
    </div>
  );
}

export default function MyPlot() {
  const [plantings, setPlantings] = useState([]);
  const [error, setError] = useState(null);

  const load = () => {
    api.get("/plantings?status=active").then(setPlantings).catch((e) => setError(e.message));
  };

  useEffect(load, []);

  return (
    <div className="page">
      <h1>My Plot</h1>
      {error && <p className="form-error">{error}</p>}
      {plantings.length === 0 && <p className="empty-hint">Nothing active yet - plant something from the Season Planner.</p>}
      <div className="planting-grid">
        {plantings.map((p) => (
          <PlantingCard key={p.id} planting={p} onRefresh={load} />
        ))}
      </div>
    </div>
  );
}
