import React, { useState } from "react";
import { api } from "../api";

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

const GERMINATION_METHODS = [
  { value: "outdoor", label: "Outdoor (direct sow)" },
  { value: "indoor", label: "Indoor" },
  { value: "indoor_heat", label: "Indoor (heated propagator)" },
  { value: "either", label: "Indoor or outdoor" },
];

function MonthOptions() {
  return (
    <>
      <option value="">-</option>
      {MONTHS.map((m, i) => (
        <option key={m} value={i + 1}>{m}</option>
      ))}
    </>
  );
}

const EMPTY_FORM = {
  name: "", variety: "", category: "veg",
  germination_days_min: "", germination_days_max: "", germination_method: "outdoor", germination_temp_c: "",
  sow_indoor_start_month: "", sow_indoor_end_month: "", sow_outdoor_start_month: "", sow_outdoor_end_month: "",
  transplant_weeks_after_sow: "", transplant_start_month: "", transplant_end_month: "",
  maturity_from: "sow", days_to_harvest_min: "", days_to_harvest_max: "",
  harvest_start_month: "", harvest_end_month: "", spacing_cm: "", yield_unit: "per_plant",
  typical_yield_g: "", ref_price_gbp_per_kg: "", succession_interval_days: "",
  frost_tender: false, water_frequency_days: "", feed_frequency_days: "", notes: "",
};

export default function AddPlant() {
  const [plantType, setPlantType] = useState("crop"); // 'crop' | 'bush'
  const [form, setForm] = useState(EMPTY_FORM);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  const set = (field) => (e) => {
    const value = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    setForm((f) => ({ ...f, [field]: value }));
  };

  const changeType = (type) => {
    setPlantType(type);
    setForm((f) => ({ ...f, category: type === "bush" ? "fruit" : "veg" }));
  };

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    try {
      const payload = { ...form, is_bush: plantType === "bush" };
      const created = await api.post("/catalog", payload);
      setMessage(
        `Added "${created.name}${created.variety ? ` (${created.variety})` : ""}" to the catalog - ` +
        `it'll show up in ${plantType === "bush" ? "Fruit Bushes'" : "Season Planner's"} picker now.`
      );
      setForm({ ...EMPTY_FORM, category: plantType === "bush" ? "fruit" : "veg" });
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="page">
      <h1>Add a Crop or Bush</h1>
      <p className="page-subtitle">
        Not in the seeded catalog? Add your own vegetable/herb crop or perennial fruit bush - it's
        shared across the household, same as the built-in catalog.
      </p>

      {message && <p className="form-success">{message}</p>}
      {error && <p className="form-error">{error}</p>}

      <div className="filter-row">
        <label>
          Type
          <select value={plantType} onChange={(e) => changeType(e.target.value)}>
            <option value="crop">Vegetable / herb crop (one-shot, sown each year)</option>
            <option value="bush">Perennial fruit bush (planted once, fruits every year)</option>
          </select>
        </label>
      </div>

      <form className="catalog-form" onSubmit={submit}>
        <section>
          <h2>Basics</h2>
          <div className="form-grid">
            <label>
              Name
              <input type="text" value={form.name} onChange={set("name")} required />
            </label>
            <label>
              Variety (optional)
              <input type="text" value={form.variety} onChange={set("variety")} />
            </label>
            {plantType === "crop" && (
              <label>
                Category
                <select value={form.category} onChange={set("category")}>
                  <option value="veg">Vegetable</option>
                  <option value="herb">Herb</option>
                </select>
              </label>
            )}
          </div>
        </section>

        <section>
          <h2>{plantType === "bush" ? "Planting" : "Sowing & germination"}</h2>
          <div className="form-grid">
            <label>
              Germination days (optional)
              <div className="range-pair">
                <input type="number" min="0" value={form.germination_days_min} onChange={set("germination_days_min")} placeholder="min" />
                <input type="number" min="0" value={form.germination_days_max} onChange={set("germination_days_max")} placeholder="max" />
              </div>
            </label>
            <label>
              Germination method
              <select value={form.germination_method} onChange={set("germination_method")}>
                {GERMINATION_METHODS.map((m) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
            </label>
            <label>
              Min germination temp °C (optional)
              <input type="number" value={form.germination_temp_c} onChange={set("germination_temp_c")} />
            </label>
            <label>
              Indoor sow window (optional)
              <div className="range-pair">
                <select value={form.sow_indoor_start_month} onChange={set("sow_indoor_start_month")}><MonthOptions /></select>
                <select value={form.sow_indoor_end_month} onChange={set("sow_indoor_end_month")}><MonthOptions /></select>
              </div>
            </label>
            <label>
              {plantType === "bush" ? "Bare-root/crown planting window" : "Outdoor sow window"} (optional)
              <div className="range-pair">
                <select value={form.sow_outdoor_start_month} onChange={set("sow_outdoor_start_month")}><MonthOptions /></select>
                <select value={form.sow_outdoor_end_month} onChange={set("sow_outdoor_end_month")}><MonthOptions /></select>
              </div>
            </label>
            {plantType === "crop" && (
              <>
                <label>
                  Weeks from sow to transplant (optional)
                  <input type="number" min="0" value={form.transplant_weeks_after_sow} onChange={set("transplant_weeks_after_sow")} />
                </label>
                <label>
                  Transplant window (optional)
                  <div className="range-pair">
                    <select value={form.transplant_start_month} onChange={set("transplant_start_month")}><MonthOptions /></select>
                    <select value={form.transplant_end_month} onChange={set("transplant_end_month")}><MonthOptions /></select>
                  </div>
                </label>
              </>
            )}
            <label>
              Maturity measured from
              <select value={form.maturity_from} onChange={set("maturity_from")}>
                <option value="sow">Sow / planting date</option>
                <option value="transplant">Transplant date</option>
              </select>
            </label>
          </div>
        </section>

        <section>
          <h2>{plantType === "bush" ? "Fruiting" : "Harvest"}</h2>
          <div className="form-grid">
            <label>
              Days to {plantType === "bush" ? "first fruiting" : "harvest"}
              <div className="range-pair">
                <input type="number" min="0" value={form.days_to_harvest_min} onChange={set("days_to_harvest_min")} placeholder="min" required />
                <input type="number" min="0" value={form.days_to_harvest_max} onChange={set("days_to_harvest_max")} placeholder="max" required />
              </div>
            </label>
            <label>
              {plantType === "bush" ? "Typical fruiting window" : "Typical harvest window"} (optional
              {plantType === "bush" ? " - used as this bush's default fruiting dates" : ""})
              <div className="range-pair">
                <select value={form.harvest_start_month} onChange={set("harvest_start_month")}><MonthOptions /></select>
                <select value={form.harvest_end_month} onChange={set("harvest_end_month")}><MonthOptions /></select>
              </div>
            </label>
            <label>
              Spacing cm (optional)
              <input type="number" min="0" value={form.spacing_cm} onChange={set("spacing_cm")} />
            </label>
            <label>
              Yield measured
              <select value={form.yield_unit} onChange={set("yield_unit")}>
                <option value="per_plant">Per plant</option>
                <option value="per_metre_row">Per metre of row</option>
              </select>
            </label>
            <label>
              Typical yield, grams (optional)
              <input type="number" min="0" value={form.typical_yield_g} onChange={set("typical_yield_g")} />
            </label>
            <label>
              Shop reference price £/kg (optional - powers the value/savings estimate)
              <input type="number" min="0" step="0.01" value={form.ref_price_gbp_per_kg} onChange={set("ref_price_gbp_per_kg")} />
            </label>
          </div>
        </section>

        <section>
          <h2>Care</h2>
          <div className="form-grid">
            {plantType === "crop" && (
              <label>
                Succession-sow interval, days (optional)
                <input type="number" min="0" value={form.succession_interval_days} onChange={set("succession_interval_days")} />
              </label>
            )}
            <label className="checkbox-label">
              <input type="checkbox" checked={form.frost_tender} onChange={set("frost_tender")} />
              Frost tender
            </label>
            <label>
              Water roughly every (days, optional)
              <input type="number" min="0" value={form.water_frequency_days} onChange={set("water_frequency_days")} />
            </label>
            <label>
              Feed roughly every (days, optional)
              <input type="number" min="0" value={form.feed_frequency_days} onChange={set("feed_frequency_days")} />
            </label>
          </div>
          <label>
            Notes (optional)
            <textarea rows="3" value={form.notes} onChange={set("notes")} />
          </label>
        </section>

        <div className="plant-form-actions">
          <button type="submit" className="btn-primary">Add to catalog</button>
        </div>
      </form>
    </div>
  );
}
