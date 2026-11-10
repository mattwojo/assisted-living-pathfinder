"""Natural-language search and follow-up questions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from agents.graph import run_action
from backend.app.present import present_facility
from backend.app.repository import get_facility, list_public_facilities
from backend.app.security import get_current_user

router = APIRouter()


class SearchIn(BaseModel):
    query: str = ""
    care_levels: list[str] = []
    city: str = ""
    state: str = ""
    max_budget: float | None = None
    amenities: list[str] = []
    available_only: bool = False


class QuestionIn(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


def _visible(user: dict | None, facility: dict) -> bool:
    if facility["published"] and facility["validation_status"] != "draft":
        return True
    if user is None:
        return False
    return user["role"] == "admin" or user["id"] == facility["owner_user_id"]


@router.post("/search")
def search(body: SearchIn) -> dict:
    facilities = list_public_facilities()
    result = run_action(
        "search",
        {
            "query": body.query,
            "filters": {
                "care_levels": body.care_levels,
                "city": body.city,
                "state": body.state,
                "max_budget": body.max_budget,
                "amenities": body.amenities,
                "available_only": body.available_only,
            },
            "facilities": facilities,
        },
    )
    by_id = {item["id"]: present_facility(item) for item in facilities}

    def attach(rows: list[dict]) -> list[dict]:
        attached = []
        for row in rows:
            facility = by_id.get(row["facility_id"])
            if facility is None:
                continue
            attached.append(
                {
                    "score": row["score"],
                    "matched": row["matched"],
                    "missed": row["missed"],
                    "unverified": row["unverified"],
                    "facility": facility,
                }
            )
        return attached

    interpreted = result["interpreted"]
    return {
        "interpreted": {
            "query": interpreted["query"],
            "care_levels": interpreted["care_levels"],
            "city": interpreted["city"],
            "city_mode": interpreted["city_mode"],
            "max_budget": interpreted["max_budget"],
            "amenities": interpreted["amenities"],
            "wants_high_staff": interpreted["wants_high_staff"],
            "available_only": interpreted["available_only"],
            "state": interpreted["state"],
        },
        "matches": attach(result["matches"]),
        "close": attach(result["close"]),
        "agent_logs": result["agent_logs"],
    }


@router.post("/facilities/{facility_id}/questions")
def ask(
    facility_id: int,
    body: QuestionIn,
    user: dict | None = Depends(get_current_user),
) -> dict:
    facility = get_facility(facility_id)
    if facility is None or not _visible(user, facility):
        raise HTTPException(status_code=404, detail="That community could not be found.")
    result = run_action("engage", {"facility": facility, "question": body.question})
    return {
        "answer": result["answer"],
        "citations": result["citations"],
        "uncertainty": result["uncertainty"],
        "disclaimer": result["disclaimer"],
        "topics": result["topics"],
        "agent_logs": result["agent_logs"],
    }
