"""Create, update, and review community listings."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.app.db import upload_dir
from backend.app.present import present_facility
from backend.app.repository import (
    add_photo,
    create_facility,
    delete_photo,
    get_facility,
    list_audit,
    list_for_review,
    list_owned_facilities,
    reorder_photos,
    set_fact_state,
    update_facility,
    update_photo,
)
from backend.app.security import get_current_user, require_roles, require_user

router = APIRouter()
MAX_PHOTO_BYTES = 5 * 1024 * 1024


class PricingTierIn(BaseModel):
    name: str = ""
    care_level: str = ""
    monthly_min: float | None = None
    monthly_max: float | None = None
    includes: str = ""


class FacilityIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""
    street: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    care_levels: list[str] = []
    amenities: list[str] = []
    staff_ratio: str = ""
    license_number: str = ""
    license_state: str = ""
    beds_available: int | None = Field(default=None, ge=0, le=500)
    waitlist: bool = False
    availability_notes: str = ""
    policies: str = ""
    pricing_tiers: list[PricingTierIn] = []
    submit: bool = True


class CaptionIn(BaseModel):
    caption: str = Field(max_length=180)


class ReorderIn(BaseModel):
    photo_ids: list[int]


def _visible(user: dict | None, facility: dict) -> bool:
    if facility["published"] and facility["validation_status"] != "draft":
        return True
    if user is None:
        return False
    return user["role"] == "admin" or user["id"] == facility["owner_user_id"]


def _can_edit(user: dict, facility: dict) -> bool:
    if user["role"] == "admin":
        return True
    return user["role"] == "representative" and user["id"] == facility["owner_user_id"]


def _require_facility(facility_id: int) -> dict:
    facility = get_facility(facility_id)
    if facility is None:
        raise HTTPException(status_code=404, detail="That community could not be found.")
    return facility


def sniff_image(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(data) > 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _suffix(media_type: str) -> str:
    return {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[media_type]


@router.get("/my/facilities")
def my_facilities(user: dict = Depends(require_roles("representative", "admin"))) -> dict:
    return {"facilities": [present_facility(item) for item in list_owned_facilities(user["id"])]}


@router.get("/review/facilities")
def review_facilities(user: dict = Depends(require_roles("admin"))) -> dict:
    del user
    return {"facilities": [present_facility(item) for item in list_for_review()]}


@router.get("/facilities/{facility_id}")
def read_facility(facility_id: int, user: dict | None = Depends(get_current_user)) -> dict:
    facility = _require_facility(facility_id)
    if not _visible(user, facility):
        raise HTTPException(status_code=404, detail="That community could not be found.")
    return {"facility": present_facility(facility)}


@router.get("/facilities/{facility_id}/audit")
def read_audit(facility_id: int, user: dict = Depends(require_user)) -> dict:
    facility = _require_facility(facility_id)
    if not _can_edit(user, facility):
        raise HTTPException(status_code=403, detail="You do not have access to that history.")
    return {"events": list_audit(facility_id)}


@router.post("/facilities", status_code=201)
def post_facility(
    body: FacilityIn,
    user: dict = Depends(require_roles("representative", "admin")),
) -> dict:
    saved = create_facility(user["id"], body.model_dump())
    return {"facility": present_facility(saved), "agent_logs": saved.get("agent_logs") or []}


@router.put("/facilities/{facility_id}")
def put_facility(
    facility_id: int,
    body: FacilityIn,
    user: dict = Depends(require_user),
) -> dict:
    facility = _require_facility(facility_id)
    if not _can_edit(user, facility):
        raise HTTPException(status_code=403, detail="You can only edit a community you represent.")
    saved = update_facility(facility_id, user["id"], body.model_dump())
    return {"facility": present_facility(saved), "agent_logs": saved.get("agent_logs") or []}


@router.post("/facts/{fact_id}/verify")
def verify_fact(fact_id: int, user: dict = Depends(require_roles("admin"))) -> dict:
    saved = set_fact_state(fact_id, user["id"], status="verified")
    if saved is None:
        raise HTTPException(status_code=404, detail="That fact could not be found.")
    return {"facility": present_facility(saved)}


@router.post("/facts/{fact_id}/set-aside")
def set_aside_fact(fact_id: int, user: dict = Depends(require_roles("admin"))) -> dict:
    saved = set_fact_state(fact_id, user["id"], active=0)
    if saved is None:
        raise HTTPException(status_code=404, detail="That fact could not be found.")
    return {"facility": present_facility(saved)}


@router.post("/facilities/{facility_id}/photos", status_code=201)
async def upload_photo(
    facility_id: int,
    file: UploadFile = File(...),
    caption: str = Form(""),
    user: dict = Depends(require_user),
) -> dict:
    facility = _require_facility(facility_id)
    if not _can_edit(user, facility):
        raise HTTPException(status_code=403, detail="You can only add photos to a community you represent.")
    data = await file.read()
    if len(data) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=400, detail="Photos need to be 5 MB or smaller.")
    media_type = sniff_image(data)
    if media_type is None:
        raise HTTPException(status_code=400, detail="Upload a JPEG, PNG, or WebP photo.")
    stored_name = f"{uuid.uuid4().hex}{_suffix(media_type)}"
    destination = upload_dir() / stored_name
    destination.write_bytes(data)
    photo = add_photo(facility_id, user["id"], stored_name, caption[:180])
    return {
        "photo": {
            "id": photo["id"],
            "caption": photo["caption"],
            "sort_order": photo["sort_order"],
            "url": f"/api/photos/{photo['id']}/file",
        }
    }


@router.get("/photos/{photo_id}/file")
def photo_file(photo_id: int, user: dict | None = Depends(get_current_user)):
    from backend.app.db import connect

    connection = connect()
    try:
        row = connection.execute("SELECT * FROM photos WHERE id = ?", (photo_id,)).fetchone()
    finally:
        connection.close()
    if row is None:
        raise HTTPException(status_code=404, detail="That photo could not be found.")
    facility = _require_facility(row["facility_id"])
    if not _visible(user, facility):
        raise HTTPException(status_code=404, detail="That photo could not be found.")
    path = upload_dir() / row["stored_name"]
    if not path.exists():
        raise HTTPException(status_code=404, detail="That photo file is missing.")
    media_type = sniff_image(path.read_bytes()[:16]) or "application/octet-stream"
    return FileResponse(path, media_type=media_type)


@router.patch("/photos/{photo_id}")
def patch_photo(photo_id: int, body: CaptionIn, user: dict = Depends(require_user)) -> dict:
    from backend.app.db import connect

    connection = connect()
    try:
        row = connection.execute("SELECT facility_id FROM photos WHERE id = ?", (photo_id,)).fetchone()
    finally:
        connection.close()
    if row is None:
        raise HTTPException(status_code=404, detail="That photo could not be found.")
    facility = _require_facility(row["facility_id"])
    if not _can_edit(user, facility):
        raise HTTPException(status_code=403, detail="You can only edit photos for a community you represent.")
    photo = update_photo(photo_id, user["id"], body.caption)
    return {
        "photo": {
            "id": photo["id"],
            "caption": photo["caption"],
            "sort_order": photo["sort_order"],
            "url": f"/api/photos/{photo['id']}/file",
        }
    }


@router.post("/facilities/{facility_id}/photos/reorder")
def post_reorder(facility_id: int, body: ReorderIn, user: dict = Depends(require_user)) -> dict:
    facility = _require_facility(facility_id)
    if not _can_edit(user, facility):
        raise HTTPException(status_code=403, detail="You can only reorder photos for a community you represent.")
    try:
        photos = reorder_photos(facility_id, user["id"], body.photo_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "photos": [
            {
                "id": photo["id"],
                "caption": photo["caption"],
                "sort_order": photo["sort_order"],
                "url": f"/api/photos/{photo['id']}/file",
            }
            for photo in photos
        ]
    }


@router.delete("/photos/{photo_id}")
def remove_photo(photo_id: int, user: dict = Depends(require_user)) -> dict:
    from backend.app.db import connect

    connection = connect()
    try:
        row = connection.execute("SELECT * FROM photos WHERE id = ?", (photo_id,)).fetchone()
    finally:
        connection.close()
    if row is None:
        raise HTTPException(status_code=404, detail="That photo could not be found.")
    facility = _require_facility(row["facility_id"])
    if not _can_edit(user, facility):
        raise HTTPException(status_code=403, detail="You can only remove photos from a community you represent.")
    delete_photo(photo_id, user["id"])
    path = upload_dir() / row["stored_name"]
    if path.exists() and not path.name.startswith("seed-"):
        path.unlink()
    return {"ok": True}
