"""Read and write facility records."""

from __future__ import annotations

import json
import re
from typing import Any

from agents.graph import run_action
from backend.app.db import LOCK, connect
from backend.app.security import now_iso

FACILITY_COLUMNS = """
    id, owner_user_id, name, slug, description, phone, email, website,
    street, city, state, postal_code, care_levels, amenities, staff_ratio,
    license_number, license_state, beds_available, waitlist, availability_notes,
    policies, validation_status, validation_flags, published, created_at, updated_at
"""


def _loads(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def slugify(name: str, connection, ignore_id: int | None = None) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "community"
    slug = base
    number = 2
    while True:
        row = connection.execute("SELECT id FROM facilities WHERE slug = ?", (slug,)).fetchone()
        if row is None or row["id"] == ignore_id:
            return slug
        slug = f"{base}-{number}"
        number += 1


def _tiers(connection, facility_id: int) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, name, care_level, monthly_min, monthly_max, includes, sort_order
        FROM pricing_tiers WHERE facility_id = ? ORDER BY sort_order, id
        """,
        (facility_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _facts(connection, facility_id: int, active_only: bool = False) -> list[dict[str, Any]]:
    query = """
        SELECT id, facility_id, field_key, label, value_text, source_type,
               source_label, verification_status, last_checked, active
        FROM facts WHERE facility_id = ?
    """
    if active_only:
        query += " AND active = 1"
    query += " ORDER BY id"
    return [dict(row) for row in connection.execute(query, (facility_id,)).fetchall()]


def _photos(connection, facility_id: int) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, facility_id, stored_name, caption, sort_order, created_at
        FROM photos WHERE facility_id = ? ORDER BY sort_order, id
        """,
        (facility_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def facility_dict(connection, row: Any, *, detail: bool = False) -> dict[str, Any]:
    item = dict(row)
    item["care_levels"] = _loads(item["care_levels"], [])
    item["amenities"] = _loads(item["amenities"], [])
    item["validation_flags"] = _loads(item["validation_flags"], [])
    item["published"] = bool(item["published"])
    item["waitlist"] = bool(item["waitlist"])
    item["pricing_tiers"] = _tiers(connection, item["id"])
    item["facts"] = _facts(connection, item["id"], active_only=not detail)
    if detail:
        item["photos"] = _photos(connection, item["id"])
    else:
        item["photos"] = _photos(connection, item["id"])
    return item


def audit(connection, facility_id: int | None, user_id: int | None, action: str, detail: str) -> None:
    connection.execute(
        """
        INSERT INTO audit_log (facility_id, user_id, action, detail, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (facility_id, user_id, action, detail, now_iso()),
    )


def _save_children(connection, facility_id: int, facility: dict[str, Any], facts: list[dict[str, Any]]) -> None:
    connection.execute("DELETE FROM pricing_tiers WHERE facility_id = ?", (facility_id,))
    for tier in facility["pricing_tiers"]:
        connection.execute(
            """
            INSERT INTO pricing_tiers
                (facility_id, name, care_level, monthly_min, monthly_max, includes, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                facility_id,
                tier["name"],
                tier["care_level"],
                tier["monthly_min"],
                tier["monthly_max"],
                tier["includes"],
                tier["sort_order"],
            ),
        )
    connection.execute(
        "DELETE FROM facts WHERE facility_id = ? AND source_type = 'facility_provided'",
        (facility_id,),
    )
    for fact in facts:
        connection.execute(
            """
            INSERT INTO facts (
                facility_id, field_key, label, value_text, source_type, source_label,
                verification_status, last_checked, active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                facility_id,
                fact["field_key"],
                fact["label"],
                fact["value_text"],
                fact["source_type"],
                fact["source_label"],
                fact["verification_status"],
                fact["last_checked"],
            ),
        )


def _apply_status(published: bool, curator_status: str) -> str:
    if not published:
        return "draft"
    return curator_status


def create_facility(owner_user_id: int | None, payload: dict[str, Any]) -> dict[str, Any]:
    with LOCK:
        connection = connect()
        try:
            external = payload.get("existing_facts") or []
            result = run_action("ingest", payload)
            facility = result["facility"]
            status = _apply_status(facility["published"], result["validation_status"])
            timestamp = now_iso()
            slug = slugify(facility["name"], connection)
            cursor = connection.execute(
                """
                INSERT INTO facilities (
                    owner_user_id, name, slug, description, phone, email, website,
                    street, city, state, postal_code, care_levels, amenities, staff_ratio,
                    license_number, license_state, beds_available, waitlist, availability_notes,
                    policies, validation_status, validation_flags, published, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    owner_user_id,
                    facility["name"],
                    slug,
                    facility["description"],
                    facility["phone"],
                    facility["email"],
                    facility["website"],
                    facility["street"],
                    facility["city"],
                    facility["state"],
                    facility["postal_code"],
                    json.dumps(facility["care_levels"]),
                    json.dumps(facility["amenities"]),
                    facility["staff_ratio"],
                    facility["license_number"],
                    facility["license_state"],
                    facility["beds_available"],
                    int(facility["waitlist"]),
                    facility["availability_notes"],
                    facility["policies"],
                    status,
                    json.dumps(result["flags"]),
                    int(facility["published"]),
                    timestamp,
                    timestamp,
                ),
            )
            facility_id = cursor.lastrowid
            _save_children(connection, facility_id, facility, result["facts"])
            for fact in external:
                connection.execute(
                    """
                    INSERT INTO facts (
                        facility_id, field_key, label, value_text, source_type, source_label,
                        verification_status, last_checked, active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        facility_id,
                        fact["field_key"],
                        fact["label"],
                        fact["value_text"],
                        fact["source_type"],
                        fact["source_label"],
                        fact["verification_status"],
                        fact["last_checked"],
                        int(fact.get("active", 1)),
                    ),
                )
            audit(
                connection,
                facility_id,
                owner_user_id,
                "create",
                f"Created {facility['name']} with status {status}.",
            )
            connection.commit()
            saved = get_facility(facility_id, connection=connection)
        finally:
            connection.close()
    if external:
        return revalidate(saved["id"])
    saved["agent_logs"] = result["agent_logs"]
    return saved


def update_facility(facility_id: int, user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    with LOCK:
        connection = connect()
        try:
            current = get_facility(facility_id, connection=connection)
            if current is None:
                return None
            previous = [
                fact
                for fact in current["facts"]
                if fact["source_type"] == "facility_provided" and fact["active"]
            ]
            external = [
                fact
                for fact in current["facts"]
                if fact["source_type"] != "facility_provided" and fact["active"]
            ]
            payload = {**payload, "previous_facts": previous, "existing_facts": external}
            result = run_action("ingest", payload)
            facility = result["facility"]
            status = _apply_status(facility["published"], result["validation_status"])
            connection.execute(
                """
                UPDATE facilities SET
                    name=?, description=?, phone=?, email=?, website=?, street=?, city=?,
                    state=?, postal_code=?, care_levels=?, amenities=?, staff_ratio=?,
                    license_number=?, license_state=?, beds_available=?, waitlist=?,
                    availability_notes=?, policies=?, validation_status=?, validation_flags=?,
                    published=?, updated_at=?
                WHERE id=?
                """,
                (
                    facility["name"],
                    facility["description"],
                    facility["phone"],
                    facility["email"],
                    facility["website"],
                    facility["street"],
                    facility["city"],
                    facility["state"],
                    facility["postal_code"],
                    json.dumps(facility["care_levels"]),
                    json.dumps(facility["amenities"]),
                    facility["staff_ratio"],
                    facility["license_number"],
                    facility["license_state"],
                    facility["beds_available"],
                    int(facility["waitlist"]),
                    facility["availability_notes"],
                    facility["policies"],
                    status,
                    json.dumps(result["flags"]),
                    int(facility["published"]),
                    now_iso(),
                    facility_id,
                ),
            )
            _save_children(connection, facility_id, facility, result["facts"])
            audit(connection, facility_id, user_id, "update", f"Updated {facility['name']} ({status}).")
            connection.commit()
            saved = get_facility(facility_id, connection=connection)
            saved["agent_logs"] = result["agent_logs"]
            return saved
        finally:
            connection.close()


def revalidate(facility_id: int) -> dict[str, Any]:
    with LOCK:
        connection = connect()
        try:
            current = get_facility(facility_id, connection=connection)
            result = run_action(
                "curate",
                {"facility": current, "facts": [fact for fact in current["facts"] if fact["active"]]},
            )
            status = _apply_status(current["published"], result["validation_status"])
            connection.execute(
                """
                UPDATE facilities SET validation_status=?, validation_flags=?, updated_at=? WHERE id=?
                """,
                (status, json.dumps(result["flags"]), now_iso(), facility_id),
            )
            connection.commit()
            saved = get_facility(facility_id, connection=connection)
            saved["agent_logs"] = result["agent_logs"]
            return saved
        finally:
            connection.close()


def get_facility(facility_id: int, connection=None) -> dict[str, Any] | None:
    own_connection = connection is None
    if own_connection:
        connection = connect()
    try:
        row = connection.execute(
            f"SELECT {FACILITY_COLUMNS} FROM facilities WHERE id = ?",
            (facility_id,),
        ).fetchone()
        if row is None:
            return None
        return facility_dict(connection, row, detail=True)
    finally:
        if own_connection:
            connection.close()


def list_public_facilities() -> list[dict[str, Any]]:
    connection = connect()
    try:
        rows = connection.execute(
            f"""
            SELECT {FACILITY_COLUMNS} FROM facilities
            WHERE published = 1 AND validation_status != 'draft'
            ORDER BY name
            """
        ).fetchall()
        return [facility_dict(connection, row) for row in rows]
    finally:
        connection.close()


def list_owned_facilities(user_id: int) -> list[dict[str, Any]]:
    connection = connect()
    try:
        rows = connection.execute(
            f"SELECT {FACILITY_COLUMNS} FROM facilities WHERE owner_user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        ).fetchall()
        return [facility_dict(connection, row) for row in rows]
    finally:
        connection.close()


def list_for_review() -> list[dict[str, Any]]:
    connection = connect()
    try:
        rows = connection.execute(
            f"""
            SELECT {FACILITY_COLUMNS} FROM facilities
            WHERE published = 1 AND validation_status IN ('conflict', 'pending_review')
            ORDER BY CASE validation_status WHEN 'conflict' THEN 0 ELSE 1 END, updated_at DESC
            """
        ).fetchall()
        return [facility_dict(connection, row, detail=True) for row in rows]
    finally:
        connection.close()


def set_fact_state(fact_id: int, user_id: int, *, status: str | None = None, active: int | None = None) -> dict[str, Any]:
    with LOCK:
        connection = connect()
        try:
            fact = connection.execute("SELECT * FROM facts WHERE id = ?", (fact_id,)).fetchone()
            if fact is None:
                return None
            if status is not None:
                connection.execute(
                    """
                    UPDATE facts SET verification_status = ?, last_checked = ? WHERE id = ?
                    """,
                    (status, now_iso()[:10], fact_id),
                )
            if active is not None:
                connection.execute("UPDATE facts SET active = ? WHERE id = ?", (active, fact_id))
            action = "verify_fact" if status == "verified" else "update_fact"
            audit(
                connection,
                fact["facility_id"],
                user_id,
                action,
                f"{action} on {fact['label']}.",
            )
            connection.commit()
            facility_id = fact["facility_id"]
        finally:
            connection.close()
    return revalidate(facility_id)


def add_photo(facility_id: int, user_id: int, stored_name: str, caption: str) -> dict[str, Any]:
    with LOCK:
        connection = connect()
        try:
            order = connection.execute(
                "SELECT COALESCE(MAX(sort_order), -1) + 1 AS next FROM photos WHERE facility_id = ?",
                (facility_id,),
            ).fetchone()["next"]
            cursor = connection.execute(
                """
                INSERT INTO photos (facility_id, stored_name, caption, sort_order, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (facility_id, stored_name, caption.strip(), order, now_iso()),
            )
            audit(connection, facility_id, user_id, "add_photo", "Uploaded a photo.")
            connection.commit()
            photo_id = cursor.lastrowid
            row = connection.execute("SELECT * FROM photos WHERE id = ?", (photo_id,)).fetchone()
            return dict(row)
        finally:
            connection.close()


def update_photo(photo_id: int, user_id: int, caption: str | None) -> dict[str, Any] | None:
    with LOCK:
        connection = connect()
        try:
            row = connection.execute("SELECT * FROM photos WHERE id = ?", (photo_id,)).fetchone()
            if row is None:
                return None
            if caption is not None:
                connection.execute("UPDATE photos SET caption = ? WHERE id = ?", (caption.strip(), photo_id))
            audit(connection, row["facility_id"], user_id, "update_photo", "Updated a photo caption.")
            connection.commit()
            updated = connection.execute("SELECT * FROM photos WHERE id = ?", (photo_id,)).fetchone()
            return dict(updated)
        finally:
            connection.close()


def reorder_photos(facility_id: int, user_id: int, photo_ids: list[int]) -> list[dict[str, Any]]:
    with LOCK:
        connection = connect()
        try:
            existing = {
                row["id"]
                for row in connection.execute(
                    "SELECT id FROM photos WHERE facility_id = ?", (facility_id,)
                ).fetchall()
            }
            if set(photo_ids) != existing:
                raise ValueError("Photo order must include every photo for this community once.")
            for index, photo_id in enumerate(photo_ids):
                connection.execute(
                    "UPDATE photos SET sort_order = ? WHERE id = ? AND facility_id = ?",
                    (index, photo_id, facility_id),
                )
            audit(connection, facility_id, user_id, "reorder_photos", "Reordered photos.")
            connection.commit()
            return _photos(connection, facility_id)
        finally:
            connection.close()


def delete_photo(photo_id: int, user_id: int) -> dict[str, Any] | None:
    with LOCK:
        connection = connect()
        try:
            row = connection.execute("SELECT * FROM photos WHERE id = ?", (photo_id,)).fetchone()
            if row is None:
                return None
            connection.execute("DELETE FROM photos WHERE id = ?", (photo_id,))
            audit(connection, row["facility_id"], user_id, "delete_photo", "Removed a photo.")
            connection.commit()
            return dict(row)
        finally:
            connection.close()


def list_audit(facility_id: int) -> list[dict[str, Any]]:
    connection = connect()
    try:
        rows = connection.execute(
            """
            SELECT audit_log.id, audit_log.action, audit_log.detail, audit_log.created_at,
                   users.name AS actor
            FROM audit_log LEFT JOIN users ON users.id = audit_log.user_id
            WHERE audit_log.facility_id = ?
            ORDER BY audit_log.id DESC
            """,
            (facility_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()
