"""Turn a plain-language request plus filters into explainable facility matches."""

from __future__ import annotations

import re
from typing import Any

from agents.vocab import CARE_LEVELS, NEIGHBORS


STOPWORDS = {
    "a",
    "an",
    "and",
    "the",
    "for",
    "with",
    "near",
    "around",
    "under",
    "find",
    "facility",
    "facilities",
    "community",
    "communities",
    "home",
    "homes",
    "that",
    "has",
    "have",
    "per",
    "month",
    "monthly",
    "high",
    "staff",
    "ratios",
    "ratio",
}

CARE_TERMS = [
    ("memory_care", ["memory care", "dementia", "alzheimer"]),
    ("assisted_living", ["assisted living"]),
    ("independent_living", ["independent living"]),
    ("skilled_nursing", ["skilled nursing", "nursing home"]),
]


def residents_per_staff(text: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?::|to)\s*(\d+(?:\.\d+)?)", (text or "").lower())
    if not match:
        return None
    left, right = float(match.group(1)), float(match.group(2))
    if left <= 0 or right <= 0:
        return None
    if left <= 2:
        return right / left
    return None


def _known_cities() -> list[str]:
    cities = set(NEIGHBORS)
    for nearby in NEIGHBORS.values():
        cities.update(nearby)
    return sorted(cities, key=len, reverse=True)


def parse_query(query: str, filters: dict[str, Any] | None = None) -> dict[str, Any]:
    filters = filters or {}
    text = query or ""
    lowered = text.lower()
    care_levels = list(filters.get("care_levels") or [])
    for key, phrases in CARE_TERMS:
        if key not in care_levels and any(phrase in lowered for phrase in phrases):
            care_levels.append(key)

    city = (filters.get("city") or "").strip()
    city_mode = "exact" if city else ""
    if not city:
        for known in _known_cities():
            if re.search(rf"\b{re.escape(known)}\b", lowered):
                city = known.title()
                break
        if city and re.search(r"\b(near|around|nearby)\b", lowered):
            city_mode = "near"
        elif city:
            city_mode = "exact"
    else:
        city_mode = "exact"

    max_budget = filters.get("max_budget")
    if max_budget in ("", None):
        budget_match = re.search(
            r"(?:under|below|less than|up to|max(?:imum)?)\s*\$?\s*([\d,]+(?:\.\d+)?)",
            lowered,
        )
        if budget_match:
            max_budget = float(budget_match.group(1).replace(",", ""))
        else:
            max_budget = None
    else:
        max_budget = float(max_budget)

    amenities = list(filters.get("amenities") or [])
    wants_high_staff = bool(re.search(r"high staff ratios?|more staff|staff ratios?", lowered))
    available_only = bool(filters.get("available_only")) or bool(
        re.search(r"\b(opening|openings|available|availability)\b", lowered)
    )
    state = (filters.get("state") or "").strip().upper()
    return {
        "care_levels": care_levels,
        "city": city,
        "city_mode": city_mode,
        "max_budget": max_budget,
        "amenities": amenities,
        "wants_high_staff": wants_high_staff,
        "available_only": available_only,
        "state": state,
        "query": text.strip(),
    }


def _tier_for_care(facility: dict[str, Any], care_levels: list[str]) -> list[dict[str, Any]]:
    tiers = facility.get("pricing_tiers") or []
    if not care_levels:
        return tiers
    matching = [tier for tier in tiers if tier.get("care_level") in care_levels]
    return matching or tiers


def _budget_fit(tiers: list[dict[str, Any]], max_budget: float | None) -> tuple[bool, str]:
    if max_budget is None:
        return True, ""
    if not tiers:
        return False, "No monthly price is recorded."
    starters = [tier.get("monthly_min") for tier in tiers if tier.get("monthly_min") is not None]
    if not starters:
        starters = [tier.get("monthly_max") for tier in tiers if tier.get("monthly_max") is not None]
    if not starters:
        return False, "No monthly price is recorded."
    lowest = min(starters)
    if lowest <= max_budget:
        return True, f"A recorded price starts at ${lowest:,.0f}, within ${max_budget:,.0f}."
    return False, f"Recorded prices start at ${lowest:,.0f}, above ${max_budget:,.0f}."


def _city_fit(facility: dict[str, Any], city: str, mode: str) -> tuple[bool, str, float]:
    if not city:
        return True, "", 0
    facility_city = (facility.get("city") or "").lower()
    wanted = city.lower()
    if facility_city == wanted:
        return True, f"Located in {facility.get('city')}.", 3
    if mode == "near" and facility_city in NEIGHBORS.get(wanted, []):
        return True, f"In {facility.get('city')}, near {city}.", 1.5
    if mode == "near":
        return False, f"Not near {city}.", 0
    return False, f"Not in {city}.", 0


def _text_overlap(query: str, facility: dict[str, Any]) -> int:
    words = [
        word
        for word in re.findall(r"[a-z0-9]+", query.lower())
        if word not in STOPWORDS and len(word) > 2 and not word.isdigit()
    ]
    haystack = " ".join(
        [
            facility.get("name") or "",
            facility.get("description") or "",
            " ".join(facility.get("amenities") or []),
            facility.get("city") or "",
        ]
    ).lower()
    return sum(1 for word in words if word in haystack)


def match_facilities(
    facilities: list[dict[str, Any]], query: str, filters: dict[str, Any] | None = None
) -> dict[str, Any]:
    interpreted = parse_query(query, filters)
    matches = []
    close = []
    for facility in facilities:
        if not facility.get("published", 1):
            continue
        if facility.get("validation_status") == "draft":
            continue
        matched: list[str] = []
        missed: list[str] = []
        hard_misses = 0
        score = _text_overlap(interpreted["query"], facility)

        if interpreted["state"] and (facility.get("state") or "").upper() != interpreted["state"]:
            hard_misses += 1
            missed.append(f"Located in {facility.get('state') or 'an unlisted state'}.")
        elif interpreted["state"]:
            matched.append(f"In {facility.get('state')}.")

        if interpreted["care_levels"]:
            have = set(facility.get("care_levels") or [])
            wanted = interpreted["care_levels"]
            hit = [CARE_LEVELS[key] for key in wanted if key in have]
            if hit:
                matched.append("Offers " + ", ".join(hit) + ".")
                score += 2 * len(hit)
            else:
                hard_misses += 1
                offered = ", ".join(CARE_LEVELS[key] for key in facility.get("care_levels") or []) or "no care level"
                missed.append(f"Does not list the requested care. Lists {offered}.")

        city_ok, city_reason, city_score = _city_fit(
            facility, interpreted["city"], interpreted["city_mode"]
        )
        score += city_score
        if interpreted["city"]:
            if city_ok:
                matched.append(city_reason)
            else:
                hard_misses += 1
                missed.append(city_reason)

        relevant_tiers = _tier_for_care(facility, interpreted["care_levels"])
        budget_ok, budget_reason = _budget_fit(relevant_tiers, interpreted["max_budget"])
        if interpreted["max_budget"] is not None:
            if budget_ok:
                matched.append(budget_reason)
                score += 2
            else:
                hard_misses += 1
                missed.append(budget_reason)

        for amenity in interpreted["amenities"]:
            if amenity in (facility.get("amenities") or []):
                matched.append(f"Lists {amenity}.")
                score += 1
            else:
                hard_misses += 1
                missed.append(f"Does not list {amenity}.")

        if interpreted["available_only"]:
            beds = facility.get("beds_available")
            if beds and beds > 0:
                matched.append(f"{beds} recorded opening{'s' if beds != 1 else ''}.")
                score += 1
            else:
                hard_misses += 1
                missed.append("No current opening is recorded.")

        if interpreted["wants_high_staff"]:
            ratio = residents_per_staff(facility.get("staff_ratio") or "")
            if ratio is None:
                missed.append("Staff ratio is not recorded, so this preference could not be checked.")
            elif ratio <= 6:
                matched.append(f"Staff ratio {facility.get('staff_ratio')} meets a higher-staff preference.")
                score += 1.5
            else:
                missed.append(
                    f"Staff ratio {facility.get('staff_ratio')} is recorded, and it is not in the higher-staff range used here (1:6 or more staff)."
                )

        unverified = []
        for fact in facility.get("facts") or []:
            if not fact.get("active", 1):
                continue
            if fact.get("verification_status") != "verified":
                unverified.append(fact.get("label") or fact.get("field_key"))
        if facility.get("validation_status") == "conflict":
            missed.append("This listing has conflicting information waiting for review.")

        row = {
            "facility_id": facility["id"],
            "score": round(score, 2),
            "matched": [item for item in matched if item],
            "missed": [item for item in missed if item],
            "unverified": unverified[:6],
        }
        if hard_misses == 0:
            matches.append(row)
        elif hard_misses == 1:
            close.append(row)

    matches.sort(key=lambda item: item["score"], reverse=True)
    close.sort(key=lambda item: item["score"], reverse=True)
    return {
        "interpreted": interpreted,
        "matches": matches[:12],
        "close": close[:8],
    }
