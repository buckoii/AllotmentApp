-- Catalog data: shared reference table, not per-user.
-- One row per "thing you'd sow" (a plant, or a specific named variety of one).
CREATE TABLE IF NOT EXISTS plants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                    -- e.g. "Parsnip"
    variety TEXT,                          -- e.g. "Gladiator F1", nullable
    category TEXT NOT NULL,                -- 'veg' | 'fruit' | 'herb'

    germination_days_min INTEGER,
    germination_days_max INTEGER,
    germination_method TEXT NOT NULL,      -- 'indoor_heat' | 'indoor' | 'outdoor' | 'either'
    germination_temp_c INTEGER,            -- min soil/propagator temp, nullable

    sow_indoor_start_month INTEGER,        -- 1-12, nullable if not indoor-sowable
    sow_indoor_end_month INTEGER,
    sow_outdoor_start_month INTEGER,       -- 1-12, nullable if not direct-sowable
    sow_outdoor_end_month INTEGER,

    transplant_weeks_after_sow INTEGER,    -- nullable, weeks from indoor sow to planting out
    transplant_start_month INTEGER,
    transplant_end_month INTEGER,

    maturity_from TEXT NOT NULL,           -- 'sow' | 'transplant' - what days_to_harvest is measured from
    days_to_harvest_min INTEGER NOT NULL,
    days_to_harvest_max INTEGER NOT NULL,
    harvest_start_month INTEGER,           -- typical harvest window, for browsing by month
    harvest_end_month INTEGER,

    spacing_cm INTEGER,
    yield_unit TEXT NOT NULL DEFAULT 'per_plant',  -- 'per_plant' | 'per_metre_row'
    typical_yield_g REAL,                  -- yield per plant, or per metre of row
    ref_price_gbp_per_kg REAL,             -- supermarket reference price, for value scoring

    succession_interval_days INTEGER,      -- nullable; null = not typically succession-sown
    frost_tender INTEGER NOT NULL DEFAULT 0,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS plots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    length_cm INTEGER,
    width_cm INTEGER,
    notes TEXT
);

-- A single sowing event and its lifecycle. Milestone dates live directly on
-- this row (rather than a generic event log) since they're 1:1 per planting
-- and the progress bar / next-task math needs them without a join.
CREATE TABLE IF NOT EXISTS plantings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    plant_id INTEGER NOT NULL REFERENCES plants(id),
    plot_id INTEGER REFERENCES plots(id),

    sow_date TEXT NOT NULL,
    sow_method TEXT NOT NULL,              -- 'indoor_heat' | 'indoor' | 'outdoor'
    quantity INTEGER,                      -- number of plants/modules
    row_length_cm INTEGER,                 -- for per_metre_row crops

    pricked_out_date TEXT,
    hardened_off_date TEXT,
    transplanted_date TEXT,
    first_harvest_date TEXT,
    last_harvest_date TEXT,

    status TEXT NOT NULL DEFAULT 'active', -- 'active' | 'harvested' | 'failed'
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Individual pickings against a planting (a bean plant gets picked weekly,
-- a parsnip bed gets lifted once). value_gbp is snapshotted at insert time
-- against the plant's ref_price_gbp_per_kg so later catalog price edits
-- don't retroactively rewrite history.
CREATE TABLE IF NOT EXISTS harvests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    planting_id INTEGER NOT NULL REFERENCES plantings(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    harvest_date TEXT NOT NULL,
    quantity_g REAL NOT NULL,
    value_gbp REAL NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    expense_date TEXT NOT NULL,
    category TEXT NOT NULL,                -- 'fees' | 'tools' | 'compost' | 'seeds' | 'other'
    description TEXT,
    amount_gbp REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_plantings_user ON plantings(user_id, status);
CREATE INDEX IF NOT EXISTS idx_harvests_planting ON harvests(planting_id);
CREATE INDEX IF NOT EXISTS idx_harvests_user ON harvests(user_id, harvest_date);
CREATE INDEX IF NOT EXISTS idx_expenses_user ON expenses(user_id, expense_date);
