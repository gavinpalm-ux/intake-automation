"""Turn a free-text inquiry into structured fields.

Two engines, same output:

* AIExtractor   - sends the message to Claude and asks for strict JSON.
                  Used when ANTHROPIC_API_KEY is set.
* RuleExtractor - regex + keyword rules. No API key, no cost, fully offline.
                  Also serves as the fallback if the AI call fails, so intake
                  never stops because a vendor is down.
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional

from .models import IntakeRecord, PROPERTY_TYPES, SERVICES, URGENCY_LEVELS

# --------------------------------------------------------------------------
# Rule-based engine
# --------------------------------------------------------------------------

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")
UNITS_RE = re.compile(
    r"(\d{1,4})\s*(?:-\s*)?(?:[\w-]+\s+){0,2}?(?:units?|doors?|apartments?|homes?|houses?|rentals?|properties|condos?|townhomes?|lots?|storefronts?|suites?)\b",
    re.I,
)
WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "twelve": 12, "fifteen": 15, "twenty": 20,
    "a couple": 2, "a few": 3, "a dozen": 12,
}
WORD_UNITS_RE = re.compile(
    r"\b(" + "|".join(WORD_NUMBERS) + r")\s+(?:\w+\s+)?(?:units?|doors?|apartments?|homes?|houses?|rentals?|properties|condos?|townhomes?)\b",
    re.I,
)

SINGLE_UNIT_RE = re.compile(
    r"\b(?:a|my|one)\s+(?:[\w-]+\s+){0,3}?(?:home|house|condo|townhome)\b", re.I
)

PROPERTY_KEYWORDS = {
    "hoa": ["hoa", "homeowners association", "association", "community board", "common areas"],
    "commercial": ["office", "retail", "commercial", "warehouse", "strip mall", "plaza", "storefront"],
    "multifamily": ["apartment", "complex", "multifamily", "multi-family", "duplex", "fourplex", "building with"],
    "single_family": ["single family", "single-family", "house", "home", "rental home", "condo", "townhome"],
}

SERVICE_KEYWORDS = {
    "turnover_cleaning": ["turnover", "move-out clean", "move out clean", "make-ready", "make ready", r"\bcleaning\b", "between tenants"],
    "maintenance": ["maintenance", "repair", "fix", "leak", "hvac", "a/c", "ac unit", "plumbing", "handyman", "drywall", "work orders"],
    "landscaping": ["landscap", "lawn", "mowing", "yard", "irrigation", "trees", "grounds"],
    "pest_control": ["pest", "roach", "termite", r"\bants\b", "rodent", "bugs", "exterminat"],
    "inspection": ["inspection", "inspect", "walkthrough", "walk-through", "condition report", "move-in report"],
}

HIGH_URGENCY = ["asap", "urgent", "emergency", "today", "tomorrow", "this week", "immediately",
                "right away", "as soon as possible", "flooding", "no ac", "no a/c"]
LOW_URGENCY = ["no rush", "next year", "just exploring", "just curious", "budgeting", "down the road",
               "next quarter", "in a few months", "eventually", "planning for"]

SIGNOFF_RE = re.compile(
    r"(?:thanks|thank you|best|regards|cheers|sincerely|-|—)[,!.]?\s*\n+\s*([A-Z][a-zA-Z'.-]+(?:\s+[A-Z][a-zA-Z'.-]+)?)",
    re.I,
)
DASH_SIGNOFF_RE = re.compile(r"^\s*[-—]\s*([A-Z][a-zA-Z'.-]+(?:\s+[A-Z][a-zA-Z'.-]+)?)\s*$", re.M)
INTRO_RE = re.compile(
    r"\b(?i:my name is|this is|i'm|i am)\s+([A-Z][a-z'-]+(?:\s+[A-Z][a-z'-]+)?)"
)
COMPANY_RE = re.compile(
    r"\b(?:with|from|at|manage for|work for|represent)\s+((?:[A-Z][\w&'.-]*\s?){1,5}?"
    r"(?:Properties|Property Management|Management|Realty|Group|Holdings|HOA|Association|LLC|Inc\.?|Co\.?|Rentals|Partners|Investments))\b"
)


def _first_match(keyword_map: dict[str, list[str]], text: str) -> list[str]:
    """Labels whose keywords appear. Keywords starting with \\b are treated as regex."""
    hits = []
    for label, words in keyword_map.items():
        if any((re.search(w, text) if w.startswith("\\b") else w in text) for w in words):
            hits.append(label)
    return hits


class RuleExtractor:
    name = "rules"

    def extract(self, inquiry: dict) -> IntakeRecord:
        body = inquiry.get("body", "")
        subject = inquiry.get("subject", "")
        text = f"{subject}\n{body}"
        lower = text.lower()

        rec = IntakeRecord(
            inquiry_id=inquiry["id"],
            channel=inquiry.get("channel", "email"),
            received_at=inquiry.get("received_at", ""),
        )

        # Contact details: prefer the form fields / sender header if present
        sender = inquiry.get("from", "") or ""
        email = EMAIL_RE.search(sender) or EMAIL_RE.search(text)
        rec.email = email.group(0).lower() if email else None
        phone = PHONE_RE.search(text)
        rec.phone = _normalize_phone(phone.group(0)) if phone else None

        rec.contact_name = (
            inquiry.get("form_name")
            or _match_group(INTRO_RE, body)
            or _match_group(SIGNOFF_RE, body)
            or _match_group(DASH_SIGNOFF_RE, body)
        )
        company = COMPANY_RE.search(body)
        rec.company = company.group(1).strip() if company else None

        # Property type: first category that matches, in priority order
        types = _first_match(PROPERTY_KEYWORDS, lower)
        rec.property_type = types[0] if types else "unknown"

        # Unit count
        m = UNITS_RE.search(text)
        if m:
            rec.unit_count = int(m.group(1))
        else:
            w = WORD_UNITS_RE.search(text)
            if w:
                rec.unit_count = WORD_NUMBERS[w.group(1).lower()]
            elif rec.property_type == "single_family" and SINGLE_UNIT_RE.search(text):
                rec.unit_count = 1

        rec.services = _first_match(SERVICE_KEYWORDS, lower) or ["other"]

        if any(w in lower for w in HIGH_URGENCY):
            rec.urgency = "high"
        elif any(w in lower for w in LOW_URGENCY):
            rec.urgency = "low"

        rec.summary = _one_line(body)
        rec.extracted_by = self.name
        return rec


def _match_group(pattern: re.Pattern, text: str) -> Optional[str]:
    m = pattern.search(text)
    return m.group(1).strip() if m else None


def _normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}" if len(digits) == 10 else raw


def _one_line(body: str, limit: int = 140) -> str:
    flat = " ".join(body.split())
    return flat if len(flat) <= limit else flat[: limit - 1].rstrip() + "…"


# --------------------------------------------------------------------------
# AI engine
# --------------------------------------------------------------------------

SYSTEM_PROMPT = f"""You extract structured intake data from customer inquiries sent to a
property services company (cleaning, maintenance, landscaping, pest control, inspections).

Return ONLY a JSON object with exactly these keys:
- contact_name: string or null (the person writing, not their tenant or boss)
- company: string or null
- email: string or null
- phone: string or null, formatted (XXX) XXX-XXXX
- property_type: one of {PROPERTY_TYPES}
- unit_count: integer or null (total units/doors/homes they want serviced)
- services: list, each one of {SERVICES}
- urgency: one of {URGENCY_LEVELS} (high = needs help within ~a week or an active problem)
- summary: one sentence, under 25 words, describing what they want

If a value is not stated, use null (or "unknown" / ["other"]). Do not guess contact details."""


class AIExtractor:
    name = "ai"

    def __init__(self, model: Optional[str] = None):
        import anthropic  # imported lazily so the rule engine works without the SDK

        self.client = anthropic.Anthropic()
        self.model = model or os.environ.get("INTAKE_MODEL", "claude-haiku-5-5")
        self.fallback = RuleExtractor()

    def extract(self, inquiry: dict) -> IntakeRecord:
        try:
            data = self._call(inquiry)
            return self._to_record(inquiry, data)
        except Exception as exc:  # network error, bad JSON, rate limit...
            rec = self.fallback.extract(inquiry)
            rec.review_reasons.append(f"ai_fallback: {type(exc).__name__}")
            return rec

    def _call(self, inquiry: dict) -> dict:
        message = (
            f"Channel: {inquiry.get('channel')}\n"
            f"From: {inquiry.get('from', '')}\n"
            f"Form name field: {inquiry.get('form_name', '')}\n"
            f"Subject: {inquiry.get('subject', '')}\n\n"
            f"{inquiry.get('body', '')}"
        )
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": message}],
        )
        text = resp.content[0].text.strip()
        text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
        return json.loads(text)

    def _to_record(self, inquiry: dict, d: dict) -> IntakeRecord:
        rec = IntakeRecord(
            inquiry_id=inquiry["id"],
            channel=inquiry.get("channel", "email"),
            received_at=inquiry.get("received_at", ""),
            contact_name=d.get("contact_name"),
            company=d.get("company"),
            email=(d.get("email") or None),
            phone=d.get("phone"),
            property_type=d.get("property_type") if d.get("property_type") in PROPERTY_TYPES else "unknown",
            unit_count=d.get("unit_count") if isinstance(d.get("unit_count"), int) else None,
            services=[s for s in d.get("services", []) if s in SERVICES] or ["other"],
            urgency=d.get("urgency") if d.get("urgency") in URGENCY_LEVELS else "normal",
            summary=d.get("summary", ""),
        )
        rec.extracted_by = self.name
        return rec


def get_extractor(force_rules: bool = False):
    """Use AI when a key is configured, otherwise the offline rule engine."""
    if not force_rules and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return AIExtractor()
        except ImportError:
            pass
    return RuleExtractor()
