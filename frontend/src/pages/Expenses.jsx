import React, { useEffect, useState } from "react";
import { api } from "../api";

const CATEGORIES = ["fees", "tools", "compost", "seeds", "other"];

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export default function Expenses() {
  const [expenses, setExpenses] = useState([]);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({ expense_date: todayIso(), category: "seeds", description: "", amount_gbp: "" });

  const load = () => {
    api.get("/expenses").then(setExpenses).catch((e) => setError(e.message));
  };

  useEffect(load, []);

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/expenses", { ...form, amount_gbp: Number(form.amount_gbp) });
      setForm({ ...form, description: "", amount_gbp: "" });
      load();
    } catch (err) {
      setError(err.message);
    }
  };

  const total = expenses.reduce((sum, e) => sum + e.amount_gbp, 0);

  return (
    <div className="page">
      <h1>Expenses</h1>
      {error && <p className="form-error">{error}</p>}

      <form className="expense-form" onSubmit={submit}>
        <input type="date" value={form.expense_date} onChange={(e) => setForm({ ...form, expense_date: e.target.value })} required />
        <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
          {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <input type="text" placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        <input type="number" min="0" step="0.01" placeholder="Amount (£)" value={form.amount_gbp} onChange={(e) => setForm({ ...form, amount_gbp: e.target.value })} required />
        <button type="submit" className="btn-primary">Add</button>
      </form>

      <table className="data-table">
        <thead><tr><th>Date</th><th>Category</th><th>Description</th><th>Amount</th></tr></thead>
        <tbody>
          {expenses.map((e) => (
            <tr key={e.id}>
              <td>{e.expense_date}</td>
              <td>{e.category}</td>
              <td>{e.description}</td>
              <td>£{e.amount_gbp.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot><tr><td colSpan={3}>Total</td><td>£{total.toFixed(2)}</td></tr></tfoot>
      </table>
    </div>
  );
}
