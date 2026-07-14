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
BUSH_UPDATE_FIELDS = {
    "plot_id", "planted_date", "fruiting_start_month", "fruiting_end_month", "status", "notes",
}
EXPENSE_CATEGORIES = {"fees", "tools", "compost", "seeds", "other"}

# Column order matches schema.sql's `plants` table (minus id) - same list
# seed_data.py's dicts use, so a user-submitted catalog entry is built the
# same way a seeded one is.
PLANT_COLUMNS = [
    "name", "variety", "category", "germination_days_min", "germination_days_max",
    "germination_method", "germination_temp_c", "sow_indoor_start_month", "sow_indoor_end_month",
    "sow_outdoor_start_month", "sow_outdoor_end_month", "transplant_weeks_after_sow",
    "transplant_start_month", "transplant_end_month", "maturity_from", "days_to_harvest_min",
    "days_to_harvest_max", "harvest_start_month", "harvest_end_month", "spacing_cm", "yield_unit",
    "typical_yield_g", "ref_price_gbp_per_kg", "succession_interval_days", "frost_tender", "is_bush",
    "water_frequency_days", "feed_frequency_days", "notes",
]
PLANT_INT_FIELDS = {
    "germination_days_min", "germination_days_max", "germination_temp_c",
    "sow_indoor_start_month", "sow_indoor_end_month", "sow_outdoor_start_month", "sow_outdoor_end_month",
    "transplant_weeks_after_sow", "transplant_start_month", "transplant_end_month",
    "days_to_harvest_min", "days_to_harvest_max", "harvest_start_month", "harvest_end_month",
    "spacing_cm", "succession_interval_days", "water_frequency_days", "feed_frequency_days",
}
PLANT_FLOAT_FIELDS = {"typical_yield_g", "ref_price_gbp_per_kg"}
PLANT_BOOL_FIELDS = {"frost_tender", "is_bush"}
PLANT_REQUIRED_FIELDS = (
    "name", "category", "germination_method", "maturity_from",
    "days_to_harvest_min", "days_to_harvest_max", "yield_unit",
)
PLANT_CATEGORIES = {"veg", "fruit", "herb"}
GERMINATION_METHODS = {"indoor_heat", "indoor", "outdoor", "either"}
MATURITY_FROM_OPTIONS = {"sow", "transplant"}
YIELD_UNITS = {"per_plant", "per_metre_row"}


def _coerce_plant_row(data):
    row = {}
    for col in PLANT_COLUMNS:
        v = data.get(col)
        try:
            if col in PLANT_BOOL_FIELDS:
                row[col] = 1 if v else 0
            elif col in PLANT_INT_FIELDS:
                row[col] = int(v) if v not in (None, "") else None
            elif col in PLANT_FLOAT_FIELDS:
                row[col] = float(v) if v not in (None, "") else None
            else:
                row[col] = v.strip() if isinstance(v, str) and v.strip() != "" else None
        except (TypeError, ValueError):
            raise ValueError(f"Invalid value for {col}: {v!r}")
    return row


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
    d["is_bush"] = bool(d["is_bush"])
    return d


def planting_to_dict(row, plant_row):
    d = dict(row)
    task = growth.next_task(row, plant_row)
    d["plant"] = plant_to_dict(plant_row)
    d["progress_percent"] = growth.progress_percent(row, plant_row)
    d["progress_color"] = growth.progress_color(d["progress_percent"])
    d["next_task"] = task
    return d


def bush_to_dict(row, plant_row, harvest_totals=None):
    d = dict(row)
    d["plant"] = plant_to_dict(plant_row)
    d["fruiting_now"] = growth.bush_fruiting_now(row)
    anchor = row["planted_date"] or row["created_at"][:10]
    d["care_tasks"] = growth.care_tasks(anchor, plant_row)
    totals = harvest_totals or {"quantity_g": 0, "value_gbp": 0, "count": 0}
    d["total_quantity_g"] = totals["quantity_g"]
    d["total_value_gbp"] = round(totals["value_gbp"], 2)
    d["harvest_count"] = totals["count"]
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
    bush = request.args.get("bush")
    conn = get_connection()
    rows = conn.execute("SELECT * FROM plants ORDER BY name").fetchall()
    conn.close()

    plants = [plant_to_dict(r) for r in rows]
    # Bushes (perennial soft fruit) are tracked separately from the one-shot
    # annual sow/plant flow this catalog otherwise serves - exclude them
    # unless the caller explicitly asks for the bush catalog (Fruit Bushes'
    # "add a bush" picker passes bush=true).
    want_bush = (bush or "").lower() in ("1", "true", "yes")
    plants = [p for p in plants if p["is_bush"] == want_bush]
    if category:
        plants = [p for p in plants if p["category"] == category]
    if month:
        plants = [p for p in plants if growth.sowable_now(p, month)]
    return jsonify(plants)


@app.post("/api/catalog")
@login_required
def create_plant():
    """Adds a user-defined catalog entry (custom crop or fruit bush)
    alongside the seeded/curated ones. The catalog is shared across the
    household (not per-user), same as the seeded rows - see schema.sql."""
    data = request.get_json(force=True)
    try:
        row = _coerce_plant_row(data)
    except ValueError as e:
        return jsonify(error=str(e)), 400

    missing = [f for f in PLANT_REQUIRED_FIELDS if row.get(f) is None]
    if missing:
        return jsonify(error=f"Missing required fields: {', '.join(missing)}"), 400
    if row["category"] not in PLANT_CATEGORIES:
        return jsonify(error=f"category must be one of {sorted(PLANT_CATEGORIES)}"), 400
    if row["germination_method"] not in GERMINATION_METHODS:
        return jsonify(error=f"germination_method must be one of {sorted(GERMINATION_METHODS)}"), 400
    if row["maturity_from"] not in MATURITY_FROM_OPTIONS:
        return jsonify(error=f"maturity_from must be one of {sorted(MATURITY_FROM_OPTIONS)}"), 400
    if row["yield_unit"] not in YIELD_UNITS:
        return jsonify(error=f"yield_unit must be one of {sorted(YIELD_UNITS)}"), 400

    conn = get_connection()
    existing = conn.execute(
        "SELECT id FROM plants WHERE name = ? AND variety IS ?", (row["name"], row["variety"])
    ).fetchone()
    if existing:
        conn.close()
        return jsonify(error="A plant with this name and variety already exists in the catalog"), 409

    cols = list(row.keys())
    placeholders = ", ".join("?" for _ in cols)
    cur = conn.execute(
        f"INSERT INTO plants ({', '.join(cols)}) VALUES ({placeholders})",
        tuple(row[c] for c in cols),
    )
    conn.commit()
    new_row = conn.execute("SELECT * FROM plants WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return jsonify(plant_to_dict(new_row)), 201


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


# ---- Fruit Bushes ----
# Perennial soft fruit (strawberries, currants, canes, rhubarb...): planted
# once, fruits again every year, so it doesn't fit the one-shot sow-to-
# harvest `plantings` lifecycle - see CLAUDE.md's "known gaps".

def _harvest_totals(conn, bush_id):
    row = conn.execute(
        """SELECT COALESCE(SUM(quantity_g), 0) AS quantity_g, COALESCE(SUM(value_gbp), 0) AS value_gbp,
                  COUNT(*) AS count
           FROM harvests WHERE bush_id = ?""",
        (bush_id,),
    ).fetchone()
    return dict(row)


@app.get("/api/bushes")
@login_required
def list_bushes():
    status = request.args.get("status")
    conn = get_connection()
    query = "SELECT * FROM bushes WHERE user_id = ?"
    params = [session["user_id"]]
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC"
    bushes = conn.execute(query, params).fetchall()

    result = []
    for b in bushes:
        plant_row = conn.execute("SELECT * FROM plants WHERE id = ?", (b["plant_id"],)).fetchone()
        result.append(bush_to_dict(b, plant_row, _harvest_totals(conn, b["id"])))
    conn.close()
    return jsonify(result)


@app.post("/api/bushes")
@login_required
def create_bush():
    data = request.get_json(force=True)
    conn = get_connection()
    plant_row = conn.execute("SELECT * FROM plants WHERE id = ?", (data.get("plant_id"),)).fetchone()
    if not plant_row:
        conn.close()
        return jsonify(error="Unknown plant"), 400

    fruiting_start = data.get("fruiting_start_month") or plant_row["harvest_start_month"]
    fruiting_end = data.get("fruiting_end_month") or plant_row["harvest_end_month"]
    if not fruiting_start or not fruiting_end:
        conn.close()
        return jsonify(error="fruiting_start_month and fruiting_end_month are required"), 400

    cur = conn.execute(
        """INSERT INTO bushes (user_id, plant_id, plot_id, planted_date, fruiting_start_month, fruiting_end_month, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            session["user_id"],
            data["plant_id"],
            data.get("plot_id"),
            data.get("planted_date"),
            fruiting_start,
            fruiting_end,
            data.get("notes"),
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM bushes WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return jsonify(bush_to_dict(row, plant_row)), 201


@app.patch("/api/bushes/<int:bush_id>")
@login_required
def update_bush(bush_id):
    data = request.get_json(force=True)
    updates = {k: v for k, v in data.items() if k in BUSH_UPDATE_FIELDS}
    if not updates:
        return jsonify(error="No valid fields to update"), 400

    conn = get_connection()
    owner = conn.execute("SELECT user_id FROM bushes WHERE id = ?", (bush_id,)).fetchone()
    if not owner or owner["user_id"] != session["user_id"]:
        conn.close()
        return jsonify(error="Not found"), 404

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(f"UPDATE bushes SET {set_clause} WHERE id = ?", (*updates.values(), bush_id))
    conn.commit()
    row = conn.execute("SELECT * FROM bushes WHERE id = ?", (bush_id,)).fetchone()
    plant_row = conn.execute("SELECT * FROM plants WHERE id = ?", (row["plant_id"],)).fetchone()
    result = bush_to_dict(row, plant_row, _harvest_totals(conn, bush_id))
    conn.close()
    return jsonify(result)


@app.delete("/api/bushes/<int:bush_id>")
@login_required
def delete_bush(bush_id):
    conn = get_connection()
    owner = conn.execute("SELECT user_id FROM bushes WHERE id = ?", (bush_id,)).fetchone()
    if not owner or owner["user_id"] != session["user_id"]:
        conn.close()
        return jsonify(error="Not found"), 404

    conn.execute("DELETE FROM harvests WHERE bush_id = ?", (bush_id,))
    conn.execute("DELETE FROM bushes WHERE id = ?", (bush_id,))
    conn.commit()
    conn.close()
    return "", 204


# ---- Harvests ----

@app.get("/api/harvests")
@login_required
def list_harvests():
    planting_id = request.args.get("planting_id", type=int)
    bush_id = request.args.get("bush_id", type=int)
    conn = get_connection()
    query = """
        SELECT h.*, COALESCE(p.name, bp.name) AS plant_name, COALESCE(p.variety, bp.variety) AS plant_variety
        FROM harvests h
        LEFT JOIN plantings pl ON h.planting_id = pl.id
        LEFT JOIN plants p ON pl.plant_id = p.id
        LEFT JOIN bushes bu ON h.bush_id = bu.id
        LEFT JOIN plants bp ON bu.plant_id = bp.id
        WHERE h.user_id = ?
    """
    params = [session["user_id"]]
    if planting_id:
        query += " AND h.planting_id = ?"
        params.append(planting_id)
    if bush_id:
        query += " AND h.bush_id = ?"
        params.append(bush_id)
    query += " ORDER BY h.harvest_date DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    result = []
    for r in rows:
        d = dict(r)
        d["source"] = "bush" if r["bush_id"] else "planting"
        result.append(d)
    return jsonify(result)


@app.post("/api/harvests")
@login_required
def create_harvest():
    data = request.get_json(force=True)
    planting_id = data.get("planting_id")
    bush_id = data.get("bush_id")
    if bool(planting_id) == bool(bush_id):
        return jsonify(error="Provide exactly one of planting_id or bush_id"), 400

    conn = get_connection()
    planting = None
    if planting_id:
        planting = conn.execute(
            "SELECT * FROM plantings WHERE id = ? AND user_id = ?", (planting_id, session["user_id"])
        ).fetchone()
        if not planting:
            conn.close()
            return jsonify(error="Planting not found"), 404
        plant_row = conn.execute("SELECT * FROM plants WHERE id = ?", (planting["plant_id"],)).fetchone()
    else:
        bush = conn.execute(
            "SELECT * FROM bushes WHERE id = ? AND user_id = ?", (bush_id, session["user_id"])
        ).fetchone()
        if not bush:
            conn.close()
            return jsonify(error="Bush not found"), 404
        plant_row = conn.execute("SELECT * FROM plants WHERE id = ?", (bush["plant_id"],)).fetchone()

    quantity_g = float(data["quantity_g"])
    ref_price = plant_row["ref_price_gbp_per_kg"] or 0
    value_gbp = round((quantity_g / 1000) * ref_price, 2)
    harvest_date = data.get("harvest_date") or date.today().isoformat()

    cur = conn.execute(
        """INSERT INTO harvests (planting_id, bush_id, user_id, harvest_date, quantity_g, value_gbp, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (planting_id, bush_id, session["user_id"], harvest_date, quantity_g, value_gbp, data.get("notes")),
    )
    if planting and not planting["first_harvest_date"]:
        conn.execute(
            "UPDATE plantings SET first_harvest_date = ? WHERE id = ?", (harvest_date, planting_id)
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


# ---- Care Schedule ----
# Watering/feeding reminders for every active planting and bush, derived
# from the catalog's guideline frequency (see growth.care_tasks) - a
# recurring guideline, not a to-do list with a "last done" history.

@app.get("/api/care-schedule")
@login_required
def care_schedule():
    conn = get_connection()
    user_id = session["user_id"]
    entries = []

    plantings = conn.execute(
        "SELECT * FROM plantings WHERE user_id = ? AND status = 'active'", (user_id,)
    ).fetchall()
    for p in plantings:
        plant_row = conn.execute("SELECT * FROM plants WHERE id = ?", (p["plant_id"],)).fetchone()
        anchor = p["transplanted_date"] or p["sow_date"]
        for task in growth.care_tasks(anchor, plant_row):
            entries.append({
                "source": "planting",
                "source_id": p["id"],
                "plant_name": plant_row["name"],
                "plant_variety": plant_row["variety"],
                **task,
            })

    bushes = conn.execute(
        "SELECT * FROM bushes WHERE user_id = ? AND status = 'active'", (user_id,)
    ).fetchall()
    for b in bushes:
        plant_row = conn.execute("SELECT * FROM plants WHERE id = ?", (b["plant_id"],)).fetchone()
        anchor = b["planted_date"] or b["created_at"][:10]
        for task in growth.care_tasks(anchor, plant_row):
            entries.append({
                "source": "bush",
                "source_id": b["id"],
                "plant_name": plant_row["name"],
                "plant_variety": plant_row["variety"],
                **task,
            })

    conn.close()
    entries.sort(key=lambda e: e["due_date"])
    return jsonify(entries)


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
    care_due_today = 0
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
        anchor = p["transplanted_date"] or p["sow_date"]
        care_due_today += sum(1 for t in growth.care_tasks(anchor, plant_row) if t["due_today"])
    tasks_due.sort(key=lambda t: t["due_date"])

    active_bushes = conn.execute(
        "SELECT * FROM bushes WHERE user_id = ? AND status = 'active'", (user_id,)
    ).fetchall()
    bushes_fruiting_now = []
    for b in active_bushes:
        plant_row = conn.execute("SELECT * FROM plants WHERE id = ?", (b["plant_id"],)).fetchone()
        if growth.bush_fruiting_now(b):
            bushes_fruiting_now.append({
                "bush_id": b["id"],
                "plant_name": plant_row["name"],
                "plant_variety": plant_row["variety"],
            })
        anchor = b["planted_date"] or b["created_at"][:10]
        care_due_today += sum(1 for t in growth.care_tasks(anchor, plant_row) if t["due_today"])

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
        bushes_fruiting_now=bushes_fruiting_now,
        care_tasks_due_today=care_due_today,
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
