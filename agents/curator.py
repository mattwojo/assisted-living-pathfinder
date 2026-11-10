"""Flag missing, stale, and conflicting facility facts without overwriting them."""

from __future__ import annotations

from datetime import date
from typing import Any


STALE_AFTER_DAYS = 365


def _age_days(iso_date: str) -> int | None:
    try:
        checked = date.fromisoformat(str(iso_date)[:10])
    except ValueError:
        return None
    return (date.today() - checked).days


def curate_listing(
    facility: dict[str, Any], facts: list[dict[str, Any]]
) -> tuple[list[dict[str, str]], str]:
    flags: list[dict[str, str]] = []
    active = [fact for fact in facts if fact.get("active", 1)]

    if not facility.get("license_number"):
        flags.append(
            {
                "severity": "missing",
                "field_key": "license_number",
                "message": "No state license number is recorded yet.",
            }
        )
    if not facility.get("pricing_tiers"):
        flags.append(
            {
                "severity": "missing",
                "field_key": "pricing",
                "message": "No monthly price is recorded yet.",
            }
        )
    for tier in facility.get("pricing_tiers") or []:
        low = tier.get("monthly_min")
        high = tier.get("monthly_max")
        if low is not None and high is not None and low > high:
            flags.append(
                {
                    "severity": "conflict",
                    "field_key": "pricing",
                    "message": f"{tier.get('name') or 'A pricing tier'} has a minimum higher than its maximum.",
                }
            )

    grouped: dict[str, list[dict[str, Any]]] = {}
    for fact in active:
        grouped.setdefault(fact.get("field_key") or "", []).append(fact)

    for field_key, items in grouped.items():
        unique_values = []
        for item in items:
            value = (item.get("value_text") or "").strip()
            if value and value not in unique_values:
                unique_values.append(value)
        if len(unique_values) > 1:
            label = items[0].get("label") or field_key
            flags.append(
                {
                    "severity": "conflict",
                    "field_key": field_key,
                    "message": f"{label} has more than one recorded value. Both are kept until someone reviews them.",
                }
            )
        for item in items:
            if (item.get("value_text") or "") == "Not recorded":
                continue
            age = _age_days(item.get("last_checked") or "")
            if age is None or age > STALE_AFTER_DAYS:
                flags.append(
                    {
                        "severity": "stale",
                        "field_key": field_key,
                        "message": f"{item.get('label') or field_key} was last checked more than a year ago.",
                    }
                )

    severities = {flag["severity"] for flag in flags}
    unverified = any(
        fact.get("verification_status") != "verified"
        and (fact.get("value_text") or "") not in {"", "Not recorded"}
        for fact in active
    )
    if "conflict" in severities:
        status = "conflict"
    elif "missing" in severities or "stale" in severities or unverified:
        status = "pending_review"
    else:
        status = "verified"
    return flags, status
