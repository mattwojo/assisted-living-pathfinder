"""Shape facility records for the web app."""

from __future__ import annotations

from typing import Any

from agents.vocab import CARE_LEVELS, STATUS_LABELS

VALIDATION_LABELS = {
    "draft": "Draft",
    "pending_review": "Waiting for review",
    "verified": "Verified",
    "conflict": "Conflicting details",
}


def present_facility(facility: dict[str, Any]) -> dict[str, Any]:
    photos = [
        {
            "id": photo["id"],
            "caption": photo["caption"],
            "sort_order": photo["sort_order"],
            "url": f"/api/photos/{photo['id']}/file",
        }
        for photo in facility.get("photos") or []
    ]
    facts = [
        {
            "id": fact["id"],
            "field_key": fact["field_key"],
            "label": fact["label"],
            "value": fact["value_text"],
            "source_type": fact["source_type"],
            "source_label": fact["source_label"],
            "verification_status": fact["verification_status"],
            "verification_label": STATUS_LABELS.get(fact["verification_status"], fact["verification_status"]),
            "last_checked": fact["last_checked"],
            "active": bool(fact["active"]),
        }
        for fact in facility.get("facts") or []
    ]
    return {
        "id": facility["id"],
        "slug": facility["slug"],
        "name": facility["name"],
        "description": facility["description"],
        "phone": facility["phone"],
        "email": facility["email"],
        "website": facility["website"],
        "address": {
            "street": facility["street"],
            "city": facility["city"],
            "state": facility["state"],
            "postal_code": facility["postal_code"],
        },
        "care_levels": [
            {"id": key, "label": CARE_LEVELS.get(key, key)} for key in facility.get("care_levels") or []
        ],
        "amenities": facility.get("amenities") or [],
        "staff_ratio": facility["staff_ratio"],
        "license": {
            "number": facility["license_number"],
            "state": facility["license_state"],
        },
        "availability": {
            "beds": facility["beds_available"],
            "waitlist": facility["waitlist"],
            "notes": facility["availability_notes"],
        },
        "policies": facility["policies"],
        "pricing_tiers": facility.get("pricing_tiers") or [],
        "photos": photos,
        "facts": facts,
        "validation": {
            "status": facility["validation_status"],
            "label": VALIDATION_LABELS.get(facility["validation_status"], facility["validation_status"]),
            "flags": facility.get("validation_flags") or [],
        },
        "published": facility["published"],
        "owner_user_id": facility["owner_user_id"],
        "created_at": facility["created_at"],
        "updated_at": facility["updated_at"],
    }
