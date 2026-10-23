"""Measure extraction accuracy against hand-labeled answers.

This is the part that answers the question every stakeholder asks before
approving an AI rollout: "How often is it right?"
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import IntakeRecord

FIELDS = ["contact_name", "email", "phone", "property_type", "unit_count", "services", "urgency"]


def _norm(field: str, value):
    if value is None:
        return None
    if field == "services":
        return sorted(value) if isinstance(value, list) else sorted(value.split(";"))
    if isinstance(value, str):
        return value.strip().lower()
    return value


def evaluate(records: list[IntakeRecord], labels_path: str | Path) -> dict:
    labels = {row["id"]: row for row in json.loads(Path(labels_path).read_text(encoding="utf-8"))}
    per_field = {f: {"correct": 0, "total": 0} for f in FIELDS}
    misses = []

    for rec in records:
        truth = labels.get(rec.inquiry_id)
        if not truth:
            continue
        for f in FIELDS:
            got, want = _norm(f, getattr(rec, f)), _norm(f, truth.get(f))
            per_field[f]["total"] += 1
            if got == want:
                per_field[f]["correct"] += 1
            else:
                misses.append({"id": rec.inquiry_id, "field": f, "expected": want, "got": got})

    total_c = sum(v["correct"] for v in per_field.values())
    total_n = sum(v["total"] for v in per_field.values())
    return {
        "overall_accuracy": round(100 * total_c / total_n, 1) if total_n else 0,
        "per_field": {f: round(100 * v["correct"] / v["total"], 1) if v["total"] else 0 for f, v in per_field.items()},
        "misses": misses,
    }


def render_eval(result: dict, engine: str) -> str:
    lines = [
        f"# Extraction Accuracy ({engine} engine)",
        "",
        f"**Overall field accuracy: {result['overall_accuracy']}%**",
        "",
        "| Field | Accuracy |",
        "|---|---|",
    ]
    lines += [f"| {f} | {a}% |" for f, a in result["per_field"].items()]
    lines += ["", "## Misses", "", "| Inquiry | Field | Expected | Got |", "|---|---|---|---|"]
    lines += [f"| {m['id']} | {m['field']} | {m['expected']} | {m['got']} |" for m in result["misses"]]
    return "\n".join(lines) + "\n"
