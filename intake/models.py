"""Data model for a structured customer intake record."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional

PROPERTY_TYPES = ["single_family", "multifamily", "commercial", "hoa", "unknown"]
SERVICES = ["turnover_cleaning", "maintenance", "landscaping", "pest_control", "inspection", "other"]
URGENCY_LEVELS = ["low", "normal", "high"]


@dataclass
class IntakeRecord:
    """One inbound inquiry, turned into fields a sales team can act on."""

    inquiry_id: str
    channel: str
    received_at: str
    contact_name: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    property_type: str = "unknown"
    unit_count: Optional[int] = None
    services: list[str] = field(default_factory=list)
    urgency: str = "normal"
    summary: str = ""

    # Filled in by scoring/routing
    priority_score: int = 0
    priority_tier: str = ""
    assigned_to: str = ""
    needs_human_review: bool = False
    review_reasons: list[str] = field(default_factory=list)

    # Filled in by responder
    draft_reply: str = ""

    # Which engine produced the extraction ("ai" or "rules")
    extracted_by: str = ""

    def to_row(self) -> dict:
        row = asdict(self)
        row["services"] = ";".join(self.services)
        row["review_reasons"] = ";".join(self.review_reasons)
        return row
