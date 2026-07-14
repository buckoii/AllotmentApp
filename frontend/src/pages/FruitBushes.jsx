import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function MonthSelect({ value, onChange }) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}>
      {MONTHS.map((m, i) => (
        <option key={m} value={i + 1}>{m}</option>
      ))}
    </select>
  );
}

function AddBushForm({ catalog, onAdd }) {
  const [plantId, setPlantId] = useState("");
  const [plantedDate, setPlantedDate] = useState("");
  const [fruitingStart, setFruitingStart] = useState(6);
  const [fruitingEnd, setFruitingEnd] = useState(8);

  useEffect(() => {
    if (catalog.length && !plantId) {
      setPlantId(String(catalog[0].id));
      setFruitingStart(catalog[0].harvest_start_month || 6);
      setFruitingEnd(catalog[0].harvest_end_month || 8);
    }
  }, [catalog]);

  const selectPlant = (id) => {
    setPlantId(id);
    const p = catalog.find((c) => String(c.id) === id);
    if (p) {
      setFruitingStart(p.harvest_start_month || 6);
      setFruitingEnd(p.harvest_end_month || 8);
    }
  };

  const submit = (e) => {
    e.preventDefault();
    if (!plantId) return;
    onAdd({
      plant_id: Number(plantId),
      planted_date: plantedDate || null,
      fruiting_start_month: Number(fruitingStart),
      fruiting_end_month: Number(fruitingEnd),
    });
    setPlantedDate("");
  };

  if (!catalog.length) return <p className="empty-hint">Loading bush catalog...</p>;

  return (
    <form className="expense-form bush-add-form" onSubmit={submit}>
      <label>
        Bush
        <select value={plantId} onChange={(e) => selectPlant(e.target.value)}>
          {catalog.map((p) => (
            <option key={p.id} value={p.id}>{p.name}{p.variety ? ` (${p.variety})` : ""}</option>
          ))}
        </select>
      </label>
      <label>
        Planted (leave blank if unknown)
        <input type="date" value={plantedDate} onChange={(e) => setPlantedDate(e.target.value)} />
      </label>
      <label>
        Fruiting from
        <MonthSelect value={fruitingStart} onChange={setFruitingStart} />
      </label>
      <label>
        Fruiting to
        <MonthSelect value={fruitingEnd} onChange={setFruitingEnd} />
      </label>
      <button type="submit" className="btn-primary">Add bush</button>
      <Link className="btn-link" to="/add-crop">Don't see it? Add a custom bush &rarr;</Link>
    </form>
  );
}

function CareTaskBadges({ tasks }) {
  if (!tasks || tasks.length === 0) return null;
  return (
    <div className="care-badges">
      {tasks.map((t) => (
        <span key={t.task} className={t.due_today ? "task-badge task-badge-overdue" : "task-badge task-badge-upcoming"}>
          {t.task === "water" ? "Water" : "Feed"} {t.due_today ? "today" : `by ${t.due_date}`} (every {t.frequency_days}d)
        </span>
      ))}
    </div>
  );
}

function BushCard({ bush, onRefresh }) {
  const [stageDate, setStageDate] = useState(todayIso());
  const [harvestGrams, setHarvestGrams] = useState("");
  const [showHarvestForm, setShowHarvestForm] = useState(false);
  const [editingDates, setEditingDates] = useState(false);
  const [plantedDate, setPlantedDate] = useState(bush.planted_date || "");
  const [fruitingStart, setFruitingStart] = useState(bush.fruiting_start_month);
  const [fruitingEnd, setFruitingEnd] = useState(bush.fruiting_end_month);
  const [error, setError] = useState(null);

  useEffect(() => {
    setPlantedDate(bush.planted_date || "");
    setFruitingStart(bush.fruiting_start_month);
    setFruitingEnd(bush.fruiting_end_month);
  }, [bush.planted_date, bush.fruiting_start_month, bush.fruiting_end_month]);

  const saveDates = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      await api.patch(`/bushes/${bush.id}`, {
        planted_date: plantedDate || null,
        fruiting_start_month: Number(fruitingStart),
        fruiting_end_month: Number(fruitingEnd),
      });
      setEditingDates(false);
      onRefresh();
    } catch (e) {
      setError(e.message);
    }
  };

  const deleteBush = async () => {
    if (!window.confirm(`Delete this ${bush.plant.name} bush and all its harvest history? This can't be undone.`)) return;
    setError(null);
    try {
      await api.del(`/bushes/${bush.id}`);
      onRefresh();
    } catch (e) {
      setError(e.message);
    }
  };

  const logHarvest = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/harvests", { bush_id: bush.id, harvest_date: stageDate, quantity_g: Number(harvestGrams) });
      setShowHarvestForm(false);
      setHarvestGrams("");
      onRefresh();
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="planting-card">
      <div className="planting-card-header">
        <h3>{bush.plant.name}{bush.plant.variety ? ` (${bush.plant.variety})` : ""}</h3>
        <div className="planting-header-actions">
          {bush.fruiting_now && <span className="value-badge">Fruiting now</span>}
          <button type="button" className="btn-icon" title="Edit dates" onClick={() => setEditingDates((v) => !v)}>
            ✎
          </button>
          <button type="button" className="btn-icon btn-icon-danger" title="Delete bush" onClick={deleteBush}>
            🗑
          </button>
        </div>
      </div>

      <p className="planting-sow-date">
        {bush.planted_date ? `Planted ${bush.planted_date}` : "Planted date unknown"}
        {" · "}Fruits {MONTHS[bush.fruiting_start_month - 1]}-{MONTHS[bush.fruiting_end_month - 1]}
      </p>

      <CareTaskBadges tasks={bush.care_tasks} />

      {editingDates && (
        <form className="edit-dates-form" onSubmit={saveDates}>
          <label>
            Planted date
            <input type="date" value={plantedDate} onChange={(e) => setPlantedDate(e.target.value)} />
          </label>
          <label>
            Fruiting from
            <MonthSelect value={fruitingStart} onChange={setFruitingStart} />
          </label>
          <label>
            Fruiting to
            <MonthSelect value={fruitingEnd} onChange={setFruitingEnd} />
          </label>
          <div className="plant-form-actions">
            <button type="submit" className="btn-primary">Save</button>
            <button type="button" className="btn-link" onClick={() => setEditingDates(false)}>Cancel</button>
          </div>
        </form>
      )}

      {error && <p className="form-error">{error}</p>}

      <div className="planting-meta-row">
        <span>{bush.harvest_count} picking{bush.harvest_count === 1 ? "" : "s"} this season - {(bush.total_quantity_g / 1000).toFixed(2)} kg total</span>
        <span>£{bush.total_value_gbp.toFixed(2)} saved</span>
      </div>

      <div className="planting-actions">
        {!showHarvestForm ? (
          <button className="btn-primary" onClick={() => setShowHarvestForm(true)}>Log a picking</button>
        ) : (
          <form className="inline-action" onSubmit={logHarvest}>
            <input type="date" value={stageDate} onChange={(e) => setStageDate(e.target.value)} />
            <input type="number" min="0" step="1" placeholder="grams" value={harvestGrams} onChange={(e) => setHarvestGrams(e.target.value)} required />
            <button type="submit" className="btn-primary">Save</button>
            <button type="button" className="btn-link" onClick={() => setShowHarvestForm(false)}>Cancel</button>
          </form>
        )}
      </div>
    </div>
  );
}

export default function FruitBushes() {
  const [bushes, setBushes] = useState([]);
  const [catalog, setCatalog] = useState([]);
  const [error, setError] = useState(null);

  const load = () => {
    api.get("/bushes?status=active").then(setBushes).catch((e) => setError(e.message));
  };

  useEffect(() => {
    load();
    api.get("/catalog?bush=true").then(setCatalog).catch((e) => setError(e.message));
  }, []);

  const addBush = async (payload) => {
    setError(null);
    try {
      await api.post("/bushes", payload);
      load();
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="page">
      <h1>Fruit Bushes</h1>
      <p className="page-subtitle">Perennial soft fruit - planted once, fruiting again every year.</p>
      {error && <p className="form-error">{error}</p>}

      <AddBushForm catalog={catalog} onAdd={addBush} />

      <div className="planting-grid">
        {bushes.map((b) => (
          <BushCard key={b.id} bush={b} onRefresh={load} />
        ))}
      </div>
      {bushes.length === 0 && <p className="empty-hint">No bushes tracked yet - add one above.</p>}
    </div>
  );
}
