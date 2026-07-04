"""Pure calculation helpers for sow windows, progress bars, next-due tasks,
value scoring, succession reminders and bed-sharing suggestions. Kept free
of Flask/DB imports so the logic is easy to reason about and test on its own.
"""
from datetime import date, timedelta


def month_in_range(month, start, end):
    """True if `month` (1-12) falls within [start, end], handling ranges
    that wrap across the year boundary (e.g. garlic: Oct-Dec)."""
    if start is None or end is None:
        return False
    if start <= end:
        return start <= month <= end
    return month >= start or month <= end


def sowable_now(plant, month=None):
    """Returns a list of methods ('indoor' / 'outdoor') sowable this month."""
    month = month or date.today().month
    methods = []
    if plant["sow_indoor_start_month"] and month_in_range(
        month, plant["sow_indoor_start_month"], plant["sow_indoor_end_month"]
    ):
        methods.append("indoor")
    if plant["sow_outdoor_start_month"] and month_in_range(
        month, plant["sow_outdoor_start_month"], plant["sow_outdoor_end_month"]
    ):
        methods.append("outdoor")
    return methods


def total_lifecycle_days(plant, midpoint=True):
    """Total days from sow date to expected harvest, folding in any
    indoor-growing-on period before transplant."""
    pre_days = 0
    if plant["maturity_from"] == "transplant" and plant["transplant_weeks_after_sow"]:
        pre_days = plant["transplant_weeks_after_sow"] * 7
    harvest_days = (
        (plant["days_to_harvest_min"] + plant["days_to_harvest_max"]) / 2
        if midpoint
        else plant["days_to_harvest_max"]
    )
    return pre_days + harvest_days


def value_per_sqm_per_week(plant):
    """£ saved per square metre of bed, per week the bed is occupied.
    Normalises fast/cheap crops against slow/expensive ones so 'worth
    growing' accounts for how long a crop ties up limited space."""
    if not plant["typical_yield_g"] or not plant["ref_price_gbp_per_kg"]:
        return None
    weeks = total_lifecycle_days(plant) / 7
    if weeks <= 0:
        return None
    value_gbp = (plant["typical_yield_g"] / 1000) * plant["ref_price_gbp_per_kg"]
    if plant["yield_unit"] == "per_plant":
        spacing_m = (plant["spacing_cm"] or 30) / 100
        area_m2 = spacing_m * spacing_m
    else:  # per_metre_row - assume rows 30cm apart as a rough default
        area_m2 = 1 * 0.3
    return round(value_gbp / area_m2 / weeks, 3)


def progress_percent(planting, plant, today=None):
    today = today or date.today()
    sow_date = date.fromisoformat(planting["sow_date"])
    total_days = total_lifecycle_days(plant)
    target_date = sow_date + timedelta(days=total_days)
    span = (target_date - sow_date).days
    if span <= 0:
        return 100
    elapsed = (today - sow_date).days
    return max(0, min(100, round(elapsed / span * 100)))


def progress_color(pct):
    """Red (0%) -> amber (50%) -> green (100%), as an HSL hue 0-120."""
    hue = round(pct * 1.2)
    return f"hsl({hue}, 70%, 45%)"


def next_task(planting, plant, today=None):
    """Returns dict(label, due_date, overdue) for the next stage this
    planting is waiting on, or None if it's fully harvested/closed."""
    today = today or date.today()
    sow_date = date.fromisoformat(planting["sow_date"])
    needs_transplant = plant["maturity_from"] == "transplant" or planting["sow_method"] in (
        "indoor",
        "indoor_heat",
    )

    if needs_transplant and not planting["transplanted_date"]:
        weeks = plant["transplant_weeks_after_sow"] or 4
        due = sow_date + timedelta(weeks=weeks)
        return {"label": "Transplant outdoors", "due_date": due.isoformat(), "overdue": today > due}

    anchor = (
        date.fromisoformat(planting["transplanted_date"])
        if planting["transplanted_date"]
        else sow_date
    )

    if not planting["first_harvest_date"]:
        due = anchor + timedelta(days=plant["days_to_harvest_min"])
        return {"label": "Check for harvest", "due_date": due.isoformat(), "overdue": today > due}

    if planting["status"] == "active" and not planting["last_harvest_date"]:
        due = anchor + timedelta(days=plant["days_to_harvest_max"])
        return {"label": "Finish harvesting / close out bed", "due_date": due.isoformat(), "overdue": today > due}

    return None


def succession_due(plant, last_sow_date, today=None):
    """True if it's time to sow another batch of a succession crop."""
    if not plant["succession_interval_days"] or not last_sow_date:
        return False
    today = today or date.today()
    last = date.fromisoformat(last_sow_date)
    return (today - last).days >= plant["succession_interval_days"]


def bed_sharing_candidates(slow_planting, slow_plant, catalog, today=None):
    """Fast crops from the catalog that would fit in the remaining time
    before `slow_planting` needs its bed space back. Timing-based only -
    doesn't account for companion-planting compatibility (e.g. avoiding
    alliums next to legumes)."""
    today = today or date.today()
    sow_date = date.fromisoformat(slow_planting["sow_date"])
    target_date = sow_date + timedelta(days=total_lifecycle_days(slow_plant))
    remaining_days = (target_date - today).days
    if remaining_days <= 0:
        return []

    candidates = []
    for plant in catalog:
        if plant["id"] == slow_plant["id"]:
            continue
        if total_lifecycle_days(plant) <= remaining_days and sowable_now(plant, today.month):
            candidates.append(plant)
    return candidates
