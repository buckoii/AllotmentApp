import os
import sqlite3

DB_PATH = os.environ.get("DB_PATH", "/data/allotment.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _table_exists(conn, table):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone() is not None


def _column_names(conn, table):
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def _migrate_plants_columns(conn):
    """Adds columns introduced after the initial schema for bushes/watering.
    `CREATE TABLE IF NOT EXISTS` in schema.sql is a no-op on an already-
    deployed `plants` table, so new nullable/defaulted columns have to be
    added explicitly here to reach existing databases. Runs before
    schema.sql's executescript, so a brand-new database (no `plants` table
    yet) is a no-op here - schema.sql creates the table with these columns
    already included."""
    if not _table_exists(conn, "plants"):
        return
    existing = _column_names(conn, "plants")
    if "is_bush" not in existing:
        conn.execute("ALTER TABLE plants ADD COLUMN is_bush INTEGER NOT NULL DEFAULT 0")
    if "water_frequency_days" not in existing:
        conn.execute("ALTER TABLE plants ADD COLUMN water_frequency_days INTEGER")
    if "feed_frequency_days" not in existing:
        conn.execute("ALTER TABLE plants ADD COLUMN feed_frequency_days INTEGER")
    conn.commit()


def _migrate_harvests_table(conn):
    """`harvests.planting_id` was NOT NULL in the original schema; harvests
    can now belong to a bush instead, so `planting_id` needs to become
    nullable and a new `bush_id` column needs to exist. SQLite can't alter a
    NOT NULL constraint in place, so on an existing database the table has
    to be rebuilt rather than just ALTERed. Runs before schema.sql's
    executescript (which would otherwise fail trying to index the not-yet-
    existent `bush_id` column on an old-shape table), and is a no-op for a
    brand-new database, which gets the final shape straight from schema.sql."""
    if not _table_exists(conn, "harvests"):
        return
    existing = _column_names(conn, "harvests")
    if "bush_id" in existing:
        return

    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("ALTER TABLE harvests RENAME TO harvests_old")
    conn.execute(
        """CREATE TABLE harvests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            planting_id INTEGER REFERENCES plantings(id),
            bush_id INTEGER REFERENCES bushes(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            harvest_date TEXT NOT NULL,
            quantity_g REAL NOT NULL,
            value_gbp REAL NOT NULL,
            notes TEXT,
            CHECK ((planting_id IS NOT NULL AND bush_id IS NULL) OR (planting_id IS NULL AND bush_id IS NOT NULL))
        )"""
    )
    conn.execute(
        """INSERT INTO harvests (id, planting_id, bush_id, user_id, harvest_date, quantity_g, value_gbp, notes)
           SELECT id, planting_id, NULL, user_id, harvest_date, quantity_g, value_gbp, notes FROM harvests_old"""
    )
    conn.execute("DROP TABLE harvests_old")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_harvests_planting ON harvests(planting_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_harvests_bush ON harvests(bush_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_harvests_user ON harvests(user_id, harvest_date)")
    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")


def _seed_or_update_plants(conn):
    """Upserts the curated catalog by (name, variety) instead of only
    seeding an empty table, so catalog edits/additions in seed_data.py
    (e.g. new bush entries) reach an already-deployed database on the next
    restart instead of being silently ignored."""
    from seed_data import PLANTS

    cols = list(PLANTS[0].keys())
    for p in PLANTS:
        existing = conn.execute(
            "SELECT id FROM plants WHERE name = ? AND variety IS ?", (p["name"], p["variety"])
        ).fetchone()
        if existing:
            set_clause = ", ".join(f"{c} = ?" for c in cols)
            conn.execute(
                f"UPDATE plants SET {set_clause} WHERE id = ?",
                (*(p[c] for c in cols), existing["id"]),
            )
        else:
            placeholders = ", ".join("?" for _ in cols)
            conn.execute(
                f"INSERT INTO plants ({', '.join(cols)}) VALUES ({placeholders})",
                tuple(p[c] for c in cols),
            )
    conn.commit()


def init_db():
    conn = get_connection()

    # Migrations run first: they bring an already-deployed database's
    # existing tables up to the current column/table shape so that
    # schema.sql's CREATE TABLE/INDEX statements below - which assume that
    # shape - are true no-ops on it. On a brand-new database these are all
    # no-ops (nothing to migrate yet) and schema.sql creates the final shape
    # directly.
    _migrate_plants_columns(conn)
    _migrate_harvests_table(conn)

    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path) as f:
        conn.executescript(f.read())
    conn.commit()

    _seed_or_update_plants(conn)

    conn.close()
