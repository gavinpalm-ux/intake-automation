"""Draft a first reply for each inquiry.

Replies are DRAFTS. Nothing is sent automatically: a rep reviews and sends.
Templates (not free-form AI text) keep tone, pricing language and promises
consistent and approved.
"""

from __future__ import annotations

from .models import IntakeRecord

COMPANY_NAME = "Gulf Coast Property Services"   # fictional demo company
SIGNATURE = f"The {COMPANY_NAME} Team"

SERVICE_LABELS = {
    "turnover_cleaning": "turnover cleaning",
    "maintenance": "maintenance",
    "landscaping": "landscaping",
    "pest_control": "pest control",
    "inspection": "property inspections",
    "other": "property services",
}

NEXT_STEP = {
    "enterprise": "One of our senior account managers will call you within one business day to "
                  "set up a walkthrough and put together a portfolio proposal.",
    "standard": "A member of our team will reach out within one business day with pricing and "
                "available start dates.",
    "small": "Reply with the property address and a good time to visit, and we'll send you a "
             "quote and get you on the schedule.",
}


def _join(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def draft_reply(rec: IntakeRecord) -> IntakeRecord:
    first = (rec.contact_name or "").split(" ")[0] or "there"
    services = _join([SERVICE_LABELS[s] for s in rec.services])
    scope = f" across your {rec.unit_count} units" if rec.unit_count and rec.unit_count > 1 else ""

    if rec.urgency == "high":
        # Urgent requests get a fast call-back promise regardless of deal size
        next_step = ("I see this is time-sensitive, so I've flagged it as a priority. Someone from "
                     "our team will call you within two business hours to get this scheduled.")
    else:
        next_step = NEXT_STEP[rec.priority_tier]

    rec.draft_reply = (
        f"Hi {first},\n\n"
        f"Thanks for reaching out to {COMPANY_NAME} about {services}{scope}. "
        f"{next_step}\n\n"
        f"Best,\n{SIGNATURE}"
    )
    return rec
