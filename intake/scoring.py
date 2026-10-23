"""Lead scoring, routing, and human-review flags.

The rules here are deliberately plain and kept in one place so a sales manager
(not just a developer) can read them and ask for changes. In a real rollout,
these weights would be tuned with the team after a few weeks of data.
"""

from __future__ import annotations

from .models import IntakeRecord

# Who handles what. Edit to match the team.
ROUTING = {
    "enterprise": "Senior Account Manager",
    "standard": "Sales Rep Queue",
    "small": "Inside Sales / Auto-reply",
}

SCORE_WEIGHTS = {
    "units": [(50, 40), (20, 30), (5, 20), (2, 10)],  # (min units, points)
    "property_type": {"multifamily": 15, "hoa": 15, "commercial": 12, "single_family": 5, "unknown": 0},
    "urgency": {"high": 20, "normal": 10, "low": 0},
    "per_service": 5,           # bundled services = bigger contract
    "has_company": 10,          # professional manager vs. individual owner
    "has_phone": 5,
}

TIER_CUTOFFS = [(65, "enterprise"), (35, "standard"), (0, "small")]


def score(rec: IntakeRecord) -> IntakeRecord:
    pts = 0
    units = rec.unit_count or 0
    for min_units, value in SCORE_WEIGHTS["units"]:
        if units >= min_units:
            pts += value
            break
    pts += SCORE_WEIGHTS["property_type"].get(rec.property_type, 0)
    pts += SCORE_WEIGHTS["urgency"].get(rec.urgency, 0)
    pts += SCORE_WEIGHTS["per_service"] * len([s for s in rec.services if s != "other"])
    if rec.company:
        pts += SCORE_WEIGHTS["has_company"]
    if rec.phone:
        pts += SCORE_WEIGHTS["has_phone"]

    rec.priority_score = min(pts, 100)
    rec.priority_tier = next(t for cutoff, t in TIER_CUTOFFS if rec.priority_score >= cutoff)
    rec.assigned_to = ROUTING[rec.priority_tier]
    _flag_for_review(rec)
    return rec


def _flag_for_review(rec: IntakeRecord) -> None:
    """Human-in-the-loop guardrail: the system says when it isn't sure."""
    reasons = rec.review_reasons
    if not rec.email and not rec.phone:
        reasons.append("no_contact_info")
    if not rec.contact_name:
        reasons.append("no_name")
    if rec.property_type == "unknown":
        reasons.append("property_type_unclear")
    if rec.services == ["other"]:
        reasons.append("service_unclear")
    if rec.priority_tier == "enterprise":
        reasons.append("high_value_lead")  # big deals always get a human touch
    rec.needs_human_review = bool(reasons)
