import React, { useEffect, useMemo, useState } from "react";
import { api } from "../api";

export default function HarvestLog() {
  const [harvests, setHarvests] = useState([]);
  const [error, setError] = useState(null);

  const load = () => {
    api.get("/harvests").then(setHarvests).catch((e) => setError(e.message));
  };

  useEffect(load, []);

  const deleteHarvest = async (h) => {
    if (!window.confirm(`Delete this picking of ${h.plant_name} (${h.harvest_date})? This can't be undone.`)) return;
    setError(null);
    try {
      await api.del(`/harvests/${h.id}`);
      load();
    } catch (e) {
      setError(e.message);
    }
  };

  const byCrop = useMemo(() => {
    const totals = {};
    for (const h of harvests) {
      const key = h.plant_variety ? `${h.plant_name} (${h.plant_variety})` : h.plant_name;
      if (!totals[key]) totals[key] = { grams: 0, value: 0 };
      totals[key].grams += h.quantity_g;
      totals[key].value += h.value_gbp;
    }
    return Object.entries(totals).sort((a, b) => b[1].value - a[1].value);
  }, [harvests]);

  const totalValue = harvests.reduce((sum, h) => sum + h.value_gbp, 0);

  return (
    <div className="page">
      <h1>Harvest Log</h1>
      {error && <p className="form-error">{error}</p>}

      <section>
        <h2>By crop</h2>
        {byCrop.length === 0 && <p className="empty-hint">Nothing picked yet.</p>}
        <table className="data-table">
          <thead><tr><th>Crop</th><th>Total weight</th><th>Value</th></tr></thead>
          <tbody>
            {byCrop.map(([name, t]) => (
              <tr key={name}>
                <td>{name}</td>
                <td>{(t.grams / 1000).toFixed(2)} kg</td>
                <td>£{t.value.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot><tr><td>Total</td><td></td><td>£{totalValue.toFixed(2)}</td></tr></tfoot>
        </table>
      </section>

      <section>
        <h2>All pickings</h2>
        <table className="data-table">
          <thead><tr><th>Date</th><th>Crop</th><th>Weight</th><th>Value</th><th></th></tr></thead>
          <tbody>
            {harvests.map((h) => (
              <tr key={h.id}>
                <td>{h.harvest_date}</td>
                <td>{h.plant_variety ? `${h.plant_name} (${h.plant_variety})` : h.plant_name}</td>
                <td>{h.quantity_g} g</td>
                <td>£{h.value_gbp.toFixed(2)}</td>
                <td>
                  <button type="button" className="btn-icon btn-icon-danger" title="Delete entry" onClick={() => deleteHarvest(h)}>
                    🗑
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
