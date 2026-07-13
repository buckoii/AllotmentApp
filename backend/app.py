import os
from datetime import date
from functools import wraps

from flask import Flask, jsonify, request, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash

from db import get_connection, init_db
import growth

FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "static_frontend")

app = Flask(__name__, static_folder=FRONTEND_DIST, static_url_path="")
app.secret_key = os.environ["FLASK_SECRET_KEY"]

PLANTING_UPDATE_FIELDS = {
    "sow_date", "pricked_out_date", "hardened_off_date", "transplanted_date",
    "first_harvest_date", "last_harvest_date", "status", "notes",
}
EXPENSE_CATEGORIES = {"fees", "tools", "compost", "seeds", "other"}


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify(error="Not logged in"), 401
        return fn(*args, **kwargs)
    return wrapper


def plant_to_dict(row):
    d = dict(row)
    d["sowable_now"] = growth.sowable_now(row)
    d["value_per_sqm_per_week"] = growth.value_per_sqm_per_week(row)
    d["total_lifecycle_weeks"] = round(growth.total_lifecycle_days(row) / 7, 1)
    d["frost_tender"] = bool(d["frost_tender"])
    return d


def planting_to_dict(row, plant_row):
    d = dict(row)
    task = growth.next_task(row, plant_row)
    d["plant"] = plant_to_dict(plant_row)
    d["progress_percent"] = growth.progress_percent(row, plant_row)
    d["progress_color"] = growth.progress_color(d["progress_percent"])
    d["next_task"] = task
    return d


# ---- Auth ----

@app.post("/api/auth/register")
def register():
    data = request.get_json(force=True)
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip() or None
    password = data.get("password") or ""
    if not username or len(password) < 8:
        return jsonify(error="Username required, password must be 8+ characters"), 400

    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, generate_password_hash(password)),
        )
        conn.commit()
        session["user_id"] = cur.lastrowid
        session["username"] = username
        return jsonify(id=cur.lastrowid, username=username), 201
    except Exception:
        return jsonify(error="Username or email already taken"), 409
    finally:
        conn.close()


@app.post("/api/auth/login")
def login():
    data = request.get_json(force=True)
    conn = get_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (data.get("username"),)
    ).fetchone()
    conn.close()
    if not user or not check_password_hash(user["password_hash"], data.get("password") or ""):
        return jsonify(error="Invalid username or password"), 401
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    return jsonify(id=user["id"], username=user["username"])


@app.post("/api/auth/logout")
def logout():
    session.clear()
    return "", 204


@app.get("/api/auth/me")
def me():
    if "user_id" not in session:
        return jsonify(error="Not logged in"), 401
    return jsonify(id=session["user_id"], username=session["username"])


# ---- Catalog ----

@app.get("/api/catalog")
def catalog():
    month = request.args.get("month", type=int)
    category = request.args.get("category")
    conn = get_connection()
    rows = conn.execute("SELECT * FROM plants ORDER BY name").fetchall()
    conn.close()

    plants = [plant_to_dict(r) for r in rows]
    if category:
        plants = [p for p in plants if p["category"] == category]
    if month:
        plants = [p for p in plants if growth.sowable_now(p, month)]
    return jsonify(plants)


# ---- Plots ----

@app.get("/api/plots")
@login_required
def list_plots():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM plots WHERE user_id = ? ORDER BY name", (session["user_id"],)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.post("/api/plots")
@login_required
def create_plot():
    data = request.get_json(force=True)
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO plots (user_id, name, length_cm, width_cm, notes) VALUES (?, ?, ?, ?, ?)",
        (session["user_id"], data.get("name"), data.get("length_cm"), data.get("width_cm"), data.get("notes")),
    )
    conn.commit()
    conn.close()
    return jsonify(id=cur.lastrowid), 201


# ---- Plantings ----

@app.get("/api/plantings")
@login_required
def list_plantings():
    status = request.args.get("status")
    conn = get_connection()
    query = "SELECT * FROM plantings WHERE user_id = ?"
    params = [session["user_id"]]
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY sow_date DESC"
    plantings = conn.execute(query, params).fetchall()

    result = []
    for p in plantings:
        plant_row = conn.execute("SELECT * FROM plants WHERE id = ?", (p["plant_id"],)).fetchone()
        result.append(planting_to_dict(p, plant_row))
    conn.close()
    return jsonify(result)


@app.post("/api/plantings")
@login_required
def create_planting():
    data = request.get_json(force=True)
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO plantings
           (user_id, plant_id, plot_id, sow_date, sow_method, quantity, row_length_cm, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            session["user_id"],
            data["plant_id"],
            data.get("plot_id"),
            data.get("sow_date") or date.today().isoformat(),
            data.get("sow_method", "outdoor"),
            data.get("quantity"),
            data.get("row_length_cm"),
            data.get("notes"),
        ),
    )
    conn.commit()
    new_id = cur.lastrowid
    row = conn.execute("SELECT * FROM plantings WHERE id = ?", (new_id,)).fetchone()
    plant_row = conn.execute("SELECT * FROM plants WHERE id = ?", (row["plant_id"],)).fetchone()
    conn.close()
    return jsonify(planting_to_dict(row, plant_row)), 201


@app.patch("/api/plantings/<int:planting_id>")
@login_required
def update_planting(planting_id):
    data = request.get_json(force=True)
    updates = {k: v for k, v in data.items() if k in PLANTING_UPDATE_FIELDS}
    if not updates:
        return jsonify(error="No valid fields to update"), 400

    conn = get_connection()
    owner = conn.execute(
        "SELECT user_id FROM plantings WHERE id = ?", (planting_id,)
    ).fetchone()
    if not owner or owner["user_id"] != session["user_id"]:
        conn.close()
        return jsonify(error="Not found"), 404

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(
        f"UPDATE plantings SET {set_clause} WHERE id = ?",
        (*updates.values(), planting_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM plantings WHERE id = ?", (planting_id,)).fetchone()
    plant_row = conn.execute("SELECT * FROM plants WHERE id = ?", (row["plant_id"],)).fetchone()
    conn.close()
    return jsonify(planting_to_dict(row, plant_row))


@app.delete("/api/plantings/<int:planting_id>")
@login_required
def delete_planting(planting_id):
    conn = get_connection()
    owner = conn.execute(
        "SELECT user_id FROM plantings WHERE id = ?", (planting_id,)
    ).fetchone()
    if not owner or owner["user_id"] != session["user_id"]:
        conn.close()
        return jsonify(error="Not found"), 404

    conn.execute("DELETE FROM harvests WHERE planting_id = ?", (planting_id,))
    conn.execute("DELETE FROM plantings WHERE id = ?", (planting_id,))
    conn.commit()
    conn.close()
    return "", 204


@app.get("/api/plantings/<int:planting_id>/bed-sharing")
@login_required
def bed_sharing(planting_id):
    conn = get_connection()
    planting = conn.execute(
        "SELECT * FROM plantings WHERE id = ? AND user_id = ?", (planting_id, session["user_id"])
    ).fetchone()
    if not planting:
        conn.close()
        return jsonify(error="Not found"), 404
    plant_row = conn.execute("SELECT * FROM plants WHERE id = ?", (planting["plant_id"],)).fetchone()
    catalog_rows = conn.execute("SELECT * FROM plants").fetchall()
    conn.close()

    candidates = growth.bed_sharing_candidates(planting, plant_row, catalog_rows)
    return jsonify([plant_to_dict(c) for c in candidates])


# ---- Harvests ----

@app.get("/api/harvests")
@login_required
def list_harvests():
    conn = get_connection()
    rows = conn.execute(
        """SELECT h.*, p.name AS plant_name, p.variety AS plant_variety
           FROM harvests h JOIN plantings pl ON h.planting_id = pl.id
           JOIN plants p ON pl.plant_id = p.id
           WHERE h.user_id = ? ORDER BY h.harvest_date DESC""",
        (session["user_id"],),
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.post("/api/harvests")
@login_required
def create_harvest():
    data = request.get_json(force=True)
    conn = get_connection()
    planting = conn.execute(
        "SELECT * FROM plantings WHERE id = ? AND user_id = ?",
        (data["planting_id"], session["user_id"]),
    ).fetchone()
    if not planting:
        conn.close()
        return jsonify(error="Planting not found"), 404
    plant_row = conn.execute("SELECT * FROM plants WHERE id = ?", (planting["plant_id"],)).fetchone()

    quantity_g = float(data["quantity_g"])
    ref_price = plant_row["ref_price_gbp_per_kg"] or 0
    value_gbp = round((quantity_g / 1000) * ref_price, 2)
    harvest_date = data.get("harvest_date") or date.today().isoformat()

    cur = conn.execute(
        """INSERT INTO harvests (planting_id, user_id, harvest_date, quantity_g, value_gbp, notes)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (planting["id"], session["user_id"], harvest_date, quantity_g, value_gbp, data.get("notes")),
    )
    if not planting["first_harvest_date"]:
        conn.execute(
            "UPDATE plantings SET first_harvest_date = ? WHERE id = ?", (harvest_date, planting["id"])
        )
    conn.commit()
    conn.close()
    return jsonify(id=cur.lastrowid, value_gbp=value_gbp), 201


@app.delete("/api/harvests/<int:harvest_id>")
@login_required
def delete_harvest(harvest_id):
    conn = get_connection()
    owner = conn.execute(
        "SELECT user_id FROM harvests WHERE id = ?", (harvest_id,)
    ).fetchone()
    if not owner or owner["user_id"] != session["user_id"]:
        conn.close()
        return jsonify(error="Not found"), 404

    conn.execute("DELETE FROM harvests WHERE id = ?", (harvest_id,))
    conn.commit()
    conn.close()
    return "", 204


# ---- Expenses ----

@app.get("/api/expenses")
@login_required
def list_expenses():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY expense_date DESC", (session["user_id"],)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.post("/api/expenses")
@login_required
def create_expense():
    data = request.get_json(force=True)
    category = data.get("category")
    if category not in EXPENSE_CATEGORIES:
        return jsonify(error=f"category must be one of {sorted(EXPENSE_CATEGORIES)}"), 400
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO expenses (user_id, expense_date, category, description, amount_gbp)
           VALUES (?, ?, ?, ?, ?)""",
        (
            session["user_id"],
            data.get("expense_date") or date.today().isoformat(),
            category,
            data.get("description"),
            float(data["amount_gbp"]),
        ),
    )
    conn.commit()
    conn.close()
    return jsonify(id=cur.lastrowid), 201


@app.delete("/api/expenses/<int:expense_id>")
@login_required
def delete_expense(expense_id):
    conn = get_connection()
    owner = conn.execute(
        "SELECT user_id FROM expenses WHERE id = ?", (expense_id,)
    ).fetchone()
    if not owner or owner["user_id"] != session["user_id"]:
        conn.close()
        return jsonify(error="Not found"), 404

    conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()
    return "", 204


# ---- Dashboard ----

@app.get("/api/dashboard")
@login_required
def dashboard():
    conn = get_connection()
    user_id = session["user_id"]

    active = conn.execute(
        "SELECT * FROM plantings WHERE user_id = ? AND status = 'active'", (user_id,)
    ).fetchall()

    tasks_due = []
    for p in active:
        plant_row = conn.execute("SELECT * FROM plants WHERE id = ?", (p["plant_id"],)).fetchone()
        task = growth.next_task(p, plant_row)
        if task:
            tasks_due.append({
                "planting_id": p["id"],
                "plant_name": plant_row["name"],
                "plant_variety": plant_row["variety"],
                **task,
            })
    tasks_due.sort(key=lambda t: t["due_date"])

    succession_reminders = []
    all_plants = conn.execute("SELECT * FROM plants WHERE succession_interval_days IS NOT NULL").fetchall()
    for plant_row in all_plants:
        last = conn.execute(
            """SELECT sow_date FROM plantings WHERE user_id = ? AND plant_id = ?
               ORDER BY sow_date DESC LIMIT 1""",
            (user_id, plant_row["id"]),
        ).fetchone()
        if last and growth.succession_due(plant_row, last["sow_date"]):
            succession_reminders.append({
                "plant_id": plant_row["id"],
                "plant_name": plant_row["name"],
                "plant_variety": plant_row["variety"],
                "last_sown": last["sow_date"],
            })

    harvest_total = conn.execute(
        "SELECT COALESCE(SUM(value_gbp), 0) AS total FROM harvests WHERE user_id = ?", (user_id,)
    ).fetchone()["total"]
    expense_total = conn.execute(
        "SELECT COALESCE(SUM(amount_gbp), 0) AS total FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchone()["total"]

    conn.close()
    return jsonify(
        tasks_due=tasks_due,
        succession_reminders=succession_reminders,
        value_saved_total=round(harvest_total, 2),
        expenses_total=round(expense_total, 2),
        net_total=round(harvest_total - expense_total, 2),
    )


# ---- Frontend (React build) ----

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    full_path = os.path.join(FRONTEND_DIST, path)
    if path and os.path.exists(full_path):
        return send_from_directory(FRONTEND_DIST, path)
    return send_from_directory(FRONTEND_DIST, "index.html")


init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
