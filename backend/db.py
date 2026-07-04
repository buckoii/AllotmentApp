import os
import sqlite3

DB_PATH = os.environ.get("DB_PATH", "/data/allotment.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    conn = get_connection()
    with open(schema_path) as f:
        conn.executescript(f.read())
    conn.commit()

    row = conn.execute("SELECT COUNT(*) AS n FROM plants").fetchone()
    if row["n"] == 0:
        from seed_data import PLANTS
        cols = list(PLANTS[0].keys())
        placeholders = ", ".join("?" for _ in cols)
        sql = f"INSERT INTO plants ({', '.join(cols)}) VALUES ({placeholders})"
        conn.executemany(sql, [tuple(p[c] for c in cols) for p in PLANTS])
        conn.commit()

    conn.close()
