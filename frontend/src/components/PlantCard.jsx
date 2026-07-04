import React, { useState } from "react";

const METHOD_LABELS = {
  indoor_heat: "Indoor (heated propagator)",
  indoor: "Indoor",
  outdoor: "Outdoor (direct sow)",
  either: "Indoor or outdoor",
};

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export default function PlantCard({ plant, onPlant }) {
  const [expanded, setExpanded] = useState(false);
  const [sowDate, setSowDate] = useState(todayIso());
  const [sowMethod, setSowMethod] = useState(plant.sowable_now[0] || "outdoor");
  const [quantity, setQuantity] = useState("");

  const submit = (e) => {
    e.preventDefault();
    onPlant({
      plant_id: plant.id,
      sow_date: sowDate,
      sow_method: sowMethod,
      quantity: quantity ? Number(quantity) : null,
    });
    setExpanded(false);
  };

  return (
    <div className="plant-card">
      <div className="plant-card-header">
        <div>
          <h3>{plant.name}</h3>
          {plant.variety && <p className="plant-variety">{plant.variety}</p>}
        </div>
        {plant.value_per_sqm_per_week != null && (
          <span className="value-badge" title="Estimated £ saved per m² of bed, per week occupied">
            £{plant.value_per_sqm_per_week.toFixed(2)}/m²/wk
          </span>
        )}
      </div>

      <dl className="plant-facts">
        <dt>Germination</dt>
        <dd>
          {plant.germination_days_min ? `${plant.germination_days_min}-${plant.germination_days_max} days, ` : ""}
          {METHOD_LABELS[plant.germination_method]}
          {plant.germination_temp_c ? ` (min ${plant.germination_temp_c}°C)` : ""}
        </dd>
        <dt>Days to harvest</dt>
        <dd>{plant.days_to_harvest_min}-{plant.days_to_harvest_max} days from {plant.maturity_from}</dd>
        <dt>Sowable now as</dt>
        <dd>{plant.sowable_now.length ? plant.sowable_now.join(" or ") : "Not this month"}</dd>
      </dl>

      {plant.notes && <p className="plant-notes">{plant.notes}</p>}

      {!expanded ? (
        <button className="btn-primary" disabled={!plant.sowable_now.length} onClick={() => setExpanded(true)}>
          Planted
        </button>
      ) : (
        <form className="plant-form" onSubmit={submit}>
          <label>
            Date
            <input type="date" value={sowDate} onChange={(e) => setSowDate(e.target.value)} required />
          </label>
          <label>
            Method
            <select value={sowMethod} onChange={(e) => setSowMethod(e.target.value)}>
              {plant.sowable_now.map((m) => (
                <option key={m} value={m}>{METHOD_LABELS[m] || m}</option>
              ))}
            </select>
          </label>
          <label>
            Quantity
            <input type="number" min="0" value={quantity} onChange={(e) => setQuantity(e.target.value)} placeholder="optional" />
          </label>
          <div className="plant-form-actions">
            <button type="submit" className="btn-primary">Confirm</button>
            <button type="button" className="btn-link" onClick={() => setExpanded(false)}>Cancel</button>
          </div>
        </form>
      )}
    </div>
  );
}
