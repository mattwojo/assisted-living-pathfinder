"""Normalize a facility submission into a consistent record and fact list."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from agents.vocab import AMENITIES, CARE_LEVELS


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _money(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    digits = re.sub(r"[^0-9.]", "", str(value))
    if not digits:
        return None
    return round(float(digits), 2)


def pricing_key(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return f"pricing:{slug or 'tier'}"


def canonical_care_levels(values: list[Any]) -> list[str]:
    found: list[str] = []
    aliases = {
        "independent": "independent_living",
        "independent living": "independent_living",
        "assisted": "assisted_living",
        "assisted living": "assisted_living",
        "memory": "memory_care",
        "memory care": "memory_care",
        "dementia": "memory_care",
        "skilled": "skilled_nursing",
        "skilled nursing": "skilled_nursing",
        "nursing": "skilled_nursing",
    }
    for value in values or []:
        text = _clean(value).lower().replace("-", " ")
        key = text if text in CARE_LEVELS else aliases.get(text)
        if key and key not in found:
            found.append(key)
    return found


def canonical_amenities(values: list[Any]) -> list[str]:
    allowed = {item.lower(): item for item in AMENITIES}
    found: list[str] = []
    for value in values or []:
        text = _clean(value)
        match = allowed.get(text.lower())
        if match and match not in found:
            found.append(match)
    return found


def format_money(value: float | None) -> str:
    if value is None:
        return ""
    return f"${value:,.0f}" if float(value).is_integer() else f"${value:,.2f}"


def _fact(
    field_key: str,
    label: str,
    value: str,
    *,
    today: str,
) -> dict[str, Any]:
    return {
        "field_key": field_key,
        "label": label,
        "value_text": value,
        "source_type": "facility_provided",
        "source_label": "Provided by the community",
        "verification_status": "unverified",
        "last_checked": today,
        "active": 1,
    }


def apply_carry_forward(
    new_facts: list[dict[str, Any]], previous: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Keep a prior verification when the community did not change the value."""
    previous_by_value = {
        (item.get("field_key"), _clean(item.get("value_text"))): item
        for item in previous
        if item.get("active", 1)
    }
    for fact in new_facts:
        old = previous_by_value.get((fact["field_key"], fact["value_text"]))
        if old and old.get("verification_status") == "verified":
            fact["verification_status"] = "verified"
            fact["last_checked"] = old.get("last_checked") or fact["last_checked"]
    return new_facts


def normalize_listing(payload: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    today = date.today().isoformat()
    care_levels = canonical_care_levels(payload.get("care_levels") or [])
    amenities = canonical_amenities(payload.get("amenities") or [])
    tiers = []
    for index, tier in enumerate(payload.get("pricing_tiers") or []):
        name = _clean(tier.get("name")) or f"Pricing tier {index + 1}"
        monthly_min = _money(tier.get("monthly_min"))
        monthly_max = _money(tier.get("monthly_max"))
        tiers.append(
            {
                "name": name,
                "care_level": (canonical_care_levels([tier.get("care_level")]) or [""])[0]
                if tier.get("care_level")
                else "",
                "monthly_min": monthly_min,
                "monthly_max": monthly_max,
                "includes": _clean(tier.get("includes")),
                "sort_order": index,
            }
        )

    beds = payload.get("beds_available")
    beds_available = None
    if beds is not None and beds != "":
        beds_available = int(beds)

    facility = {
        "name": _clean(payload.get("name")),
        "description": _clean(payload.get("description")),
        "phone": _clean(payload.get("phone")),
        "email": _clean(payload.get("email")).lower(),
        "website": _clean(payload.get("website")),
        "street": _clean(payload.get("street")),
        "city": _clean(payload.get("city")),
        "state": _clean(payload.get("state")).upper()[:2],
        "postal_code": _clean(payload.get("postal_code")),
        "care_levels": care_levels,
        "amenities": amenities,
        "staff_ratio": _clean(payload.get("staff_ratio")),
        "license_number": _clean(payload.get("license_number")),
        "license_state": _clean(payload.get("license_state") or payload.get("state")).upper()[:2],
        "beds_available": beds_available,
        "waitlist": bool(payload.get("waitlist")),
        "availability_notes": _clean(payload.get("availability_notes")),
        "policies": _clean(payload.get("policies")),
        "pricing_tiers": tiers,
        "published": bool(payload.get("submit", True)),
    }

    facts = [
        _fact("name", "Community name", facility["name"], today=today),
        _fact("description", "Description", facility["description"], today=today),
        _fact(
            "address",
            "Location",
            ", ".join(
                part
                for part in [
                    facility["street"],
                    facility["city"],
                    facility["state"],
                    facility["postal_code"],
                ]
                if part
            ),
            today=today,
        ),
        _fact(
            "care_levels",
            "Care offered",
            ", ".join(CARE_LEVELS[key] for key in care_levels) or "Not recorded",
            today=today,
        ),
        _fact(
            "amenities",
            "Amenities",
            ", ".join(amenities) or "Not recorded",
            today=today,
        ),
        _fact(
            "staff_ratio",
            "Staff ratio",
            facility["staff_ratio"] or "Not recorded",
            today=today,
        ),
        _fact(
            "license_number",
            "License",
            " ".join(
                part
                for part in [facility["license_state"], facility["license_number"]]
                if part
            )
            or "Not recorded",
            today=today,
        ),
        _fact("policies", "Policies", facility["policies"] or "Not recorded", today=today),
    ]
    if facility["phone"]:
        facts.append(_fact("phone", "Phone", facility["phone"], today=today))

    if beds_available is None and not facility["waitlist"]:
        availability = facility["availability_notes"] or "Not recorded"
    elif beds_available == 0 or facility["waitlist"]:
        availability = "Waitlist"
        if beds_available:
            availability = f"{beds_available} openings, with a waitlist"
        if facility["availability_notes"]:
            availability = f"{availability}. {facility['availability_notes']}"
    else:
        noun = "opening" if beds_available == 1 else "openings"
        availability = f"{beds_available} {noun}"
        if facility["availability_notes"]:
            availability = f"{availability}. {facility['availability_notes']}"
    facts.append(_fact("availability", "Availability", availability, today=today))

    for tier in tiers:
        low = format_money(tier["monthly_min"])
        high = format_money(tier["monthly_max"])
        if low and high:
            price = f"{low}–{high} per month"
        elif low:
            price = f"From {low} per month"
        elif high:
            price = f"Up to {high} per month"
        else:
            price = "Price not recorded"
        if tier["includes"]:
            price = f"{price}. Includes {tier['includes']}"
        care = CARE_LEVELS.get(tier["care_level"], "")
        label = tier["name"] if not care else f"{tier['name']} ({care})"
        facts.append(_fact(pricing_key(tier["name"]), label, price, today=today))

    facts = [fact for fact in facts if fact["value_text"]]
    facts = apply_carry_forward(facts, payload.get("previous_facts") or [])
    return facility, facts
