"""End-to-end run: inbox -> structured leads -> routing -> drafts -> reports."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from .extractor import get_extractor
from .models import IntakeRecord
from .responder import draft_reply
from .scoring import score

# Baseline for the manual process (see docs/case_study.md for where these come from)
MANUAL_MINUTES_PER_INQUIRY = 12
AUTOMATED_MINUTES_PER_REVIEWED = 3   # human checks a flagged record + edits draft
AUTOMATED_MINUTES_PER_CLEAN = 1      # human skims the draft and hits send


def load_inquiries(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def process(inquiries: list[dict], force_rules: bool = False) -> list[IntakeRecord]:
    extractor = get_extractor(force_rules=force_rules)
    records = []
    for inq in inquiries:
        rec = extractor.extract(inq)
        rec = score(rec)
        rec = draft_reply(rec)
        records.append(rec)
    records.sort(key=lambda r: r.priority_score, reverse=True)
    return records


def write_outputs(records: list[IntakeRecord], out_dir: str | Path) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    rows = [r.to_row() for r in records]
    fields = list(rows[0].keys()) if rows else []

    with open(out / "leads.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    review = [r for r in rows if r["needs_human_review"]]
    with open(out / "review_queue.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(review)

    drafts_dir = out / "drafts"
    drafts_dir.mkdir(exist_ok=True)
    for r in records:
        to = r.email or r.phone or "UNKNOWN - needs review"
        (drafts_dir / f"{r.inquiry_id}.txt").write_text(
            f"To: {to}\nAssigned: {r.assigned_to}\nPriority: {r.priority_tier} ({r.priority_score})\n\n{r.draft_reply}\n",
            encoding="utf-8",
        )

    stats = summarize(records)
    (out / "summary.md").write_text(render_summary(records, stats), encoding="utf-8")
    return stats


def summarize(records: list[IntakeRecord]) -> dict:
    n = len(records)
    reviewed = sum(r.needs_human_review for r in records)
    manual_min = n * MANUAL_MINUTES_PER_INQUIRY
    auto_min = reviewed * AUTOMATED_MINUTES_PER_REVIEWED + (n - reviewed) * AUTOMATED_MINUTES_PER_CLEAN
    return {
        "total": n,
        "needs_review": reviewed,
        "auto_ready": n - reviewed,
        "tiers": dict(Counter(r.priority_tier for r in records)),
        "urgent": sum(r.urgency == "high" for r in records),
        "engine": records[0].extracted_by if records else "",
        "manual_minutes": manual_min,
        "automated_minutes": auto_min,
        "minutes_saved": manual_min - auto_min,
        "pct_time_saved": round(100 * (manual_min - auto_min) / manual_min, 1) if manual_min else 0,
    }


def render_summary(records: list[IntakeRecord], s: dict) -> str:
    lines = [
        "# Intake Run Summary",
        "",
        f"- Inquiries processed: **{s['total']}** (engine: `{s['engine']}`)",
        f"- Ready to send after a quick skim: **{s['auto_ready']}**",
        f"- Flagged for human review: **{s['needs_review']}**",
        f"- Urgent requests: **{s['urgent']}**",
        f"- Tiers: " + ", ".join(f"{k} {v}" for k, v in sorted(s["tiers"].items())),
        "",
        "## Estimated staff time",
        "",
        "| Process | Minutes |",
        "|---|---|",
        f"| Manual (12 min each) | {s['manual_minutes']} |",
        f"| Automated + human review | {s['automated_minutes']} |",
        f"| **Saved** | **{s['minutes_saved']} ({s['pct_time_saved']}%)** |",
        "",
        "## Lead queue (highest priority first)",
        "",
        "| ID | Contact | Type | Units | Services | Urgency | Score | Assigned | Review |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in records:
        lines.append(
            f"| {r.inquiry_id} | {r.contact_name or '—'} | {r.property_type} | {r.unit_count or '—'} | "
            f"{', '.join(r.services)} | {r.urgency} | {r.priority_score} | {r.assigned_to} | "
            f"{'⚠ ' + ', '.join(r.review_reasons) if r.needs_human_review else '✓'} |"
        )
    return "\n".join(lines) + "\n"
