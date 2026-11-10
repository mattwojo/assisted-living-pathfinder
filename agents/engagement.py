"""Answer follow-up questions from the facility record and plain-language templates."""

from __future__ import annotations

import os
from typing import Any

from agents.vocab import CARE_LEVELS, DISCLAIMER


CARE_EXPLAINERS = {
    "independent_living": "Independent living is a community setting for people who mostly handle daily activities on their own.",
    "assisted_living": "Assisted living generally means help with daily activities such as bathing, dressing, meals, and medication reminders, without hospital-level care.",
    "memory_care": "Memory care is a more structured, often secured setting for people living with dementia, with staff who are trained for memory loss.",
    "skilled_nursing": "Skilled nursing is licensed nursing care. It is a different setting from assisted living and is often arranged separately.",
}

CONTRACT_TEMPLATE = (
    "A residency agreement usually covers the base monthly rate, which services are included, "
    "how fees change if care needs increase, how much notice is required to move out, and when "
    "the community can end the agreement. Ask for the current agreement and a fee sheet. "
    "This tool cannot review a contract."
)

FINANCIAL_TEMPLATE = (
    "Many assisted living communities are private pay. Some families also look at long-term care insurance, "
    "veterans benefits, or state Medicaid programs. Whether a community accepts those sources depends on the "
    "community and the state. A benefits counselor or financial advisor can look at a specific situation."
)


def _facts(facility: dict[str, Any]) -> list[dict[str, Any]]:
    return [fact for fact in facility.get("facts") or [] if fact.get("active", 1)]


def _by_key(facts: list[dict[str, Any]], prefix: str) -> list[dict[str, Any]]:
    return [fact for fact in facts if str(fact.get("field_key") or "").startswith(prefix)]


def _citation(fact: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": fact.get("label") or fact.get("field_key"),
        "value": fact.get("value_text"),
        "source_type": fact.get("source_type"),
        "source_label": fact.get("source_label"),
        "verification_status": fact.get("verification_status"),
        "last_checked": fact.get("last_checked"),
    }


def _topics(question: str) -> list[str]:
    text = question.lower()
    topics = []
    checks = [
        ("pricing", ["price", "cost", "fee", "monthly", "rate", "expensive", "charge"]),
        ("care", ["memory", "dementia", "alzheimer", "care level", "assisted", "skilled", "kind of care", "care type"]),
        ("contract", ["contract", "agreement", "lease", "notice", "move out", "discharge"]),
        ("license", ["license", "licensed", "safety", "violation", "inspection", "citation"]),
        ("availability", ["available", "availability", "opening", "apartment", "waitlist", "wait list", "bed"]),
        ("staff", ["staff", "ratio", "caregiver", "nurse"]),
        ("financial", ["medicaid", "medicare", "insurance", "veteran", "financial", "pay for", "afford"]),
        ("amenities", ["pet", "garden", "amenit", "activity", "meal", "food", "transport"]),
    ]
    for name, words in checks:
        if any(word in text for word in words):
            topics.append(name)
    return topics or ["overview"]


def _needs_personal_advice(question: str) -> bool:
    text = question.lower()
    markers = [
        "should my",
        "does my mother",
        "does my father",
        "does mom",
        "does dad",
        "need memory care",
        "diagnose",
        "what care does",
        "is this the right",
        "medication dose",
    ]
    return any(marker in text for marker in markers)


def _compose_with_gemini(question: str, draft: str, citations: list[dict[str, Any]]) -> str | None:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
    except Exception:
        return None
    source_lines = "\n".join(
        f"- {item['label']}: {item['value']} ({item['source_label']}, {item['verification_status']})"
        for item in citations
    )
    prompt = (
        "You help families understand one assisted living community. "
        "Use only the facts listed below. If a fact is missing, say it is not recorded. "
        "Do not give legal, medical, or financial advice. Keep the answer under 160 words.\n\n"
        f"Question: {question}\n\nFacts:\n{source_lines or '- No supporting facts were selected.'}\n\n"
        f"Draft to improve, without adding new numbers:\n{draft}"
    )
    try:
        client = genai.Client(api_key=api_key)
        model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        response = client.models.generate_content(model=model, contents=prompt)
        text = (getattr(response, "text", None) or "").strip()
        return text or None
    except Exception:
        return None


def answer_question(facility: dict[str, Any], question: str) -> dict[str, Any]:
    facts = _facts(facility)
    topics = _topics(question)
    paragraphs: list[str] = []
    uncertainty: list[str] = []
    used: list[dict[str, Any]] = []

    if _needs_personal_advice(question):
        uncertainty.append(
            "This tool cannot tell you what care a specific person needs. A clinician or geriatric care manager can do an assessment."
        )

    if "overview" in topics:
        description = next((fact for fact in facts if fact.get("field_key") == "description"), None)
        care = next((fact for fact in facts if fact.get("field_key") == "care_levels"), None)
        if description:
            used.append(description)
            paragraphs.append(description["value_text"])
        if care:
            used.append(care)
            paragraphs.append(f"Care recorded for this community: {care['value_text']}.")

    if "care" in topics:
        offered = facility.get("care_levels") or []
        if offered:
            names = [CARE_LEVELS[key] for key in offered if key in CARE_LEVELS]
            paragraphs.append("This community lists " + ", ".join(names) + ".")
            paragraphs.extend(CARE_EXPLAINERS[key] for key in offered if key in CARE_EXPLAINERS)
            care_fact = next((fact for fact in facts if fact.get("field_key") == "care_levels"), None)
            if care_fact:
                used.append(care_fact)
        else:
            uncertainty.append("No care levels are recorded for this community.")

    if "pricing" in topics:
        price_facts = _by_key(facts, "pricing:")
        if price_facts:
            used.extend(price_facts)
            lines = [f"{fact['label']}: {fact['value_text']}" for fact in price_facts]
            paragraphs.append("Recorded monthly pricing — " + " ".join(lines))
            paragraphs.append(
                "A published range is not a quote. The rate often depends on the apartment and the care assessment."
            )
        else:
            uncertainty.append("No monthly price is recorded yet. Ask the community for a current fee sheet.")

    if "financial" in topics:
        paragraphs.append(FINANCIAL_TEMPLATE)
        uncertainty.append("Nothing here says this community accepts a particular benefit or insurance plan.")

    if "contract" in topics:
        paragraphs.append(CONTRACT_TEMPLATE)
        policy = next((fact for fact in facts if fact.get("field_key") == "policies"), None)
        if policy and policy.get("value_text") not in {"", "Not recorded"}:
            used.append(policy)
            paragraphs.append(f"The community recorded this policy note: {policy['value_text']}")
        else:
            uncertainty.append("No contract terms are stored in this listing.")

    if "license" in topics:
        license_fact = next((fact for fact in facts if fact.get("field_key") == "license_number"), None)
        if license_fact and license_fact.get("value_text") not in {"", "Not recorded"}:
            used.append(license_fact)
            paragraphs.append(f"License on file: {license_fact['value_text']}.")
            if license_fact.get("verification_status") != "verified":
                uncertainty.append("The license number has not been checked against the state record in this app.")
        else:
            uncertainty.append("No license number is recorded.")
        paragraphs.append(
            "A license number does not describe inspection history. Ask the state licensing agency about recent surveys or citations."
        )

    if "availability" in topics:
        availability = next((fact for fact in facts if fact.get("field_key") == "availability"), None)
        if availability:
            used.append(availability)
            paragraphs.append(f"Availability on file: {availability['value_text']}.")
        uncertainty.append("Openings change quickly. Call the community to confirm.")

    if "staff" in topics:
        staff = next((fact for fact in facts if fact.get("field_key") == "staff_ratio"), None)
        if staff and staff.get("value_text") not in {"", "Not recorded"}:
            used.append(staff)
            paragraphs.append(f"Recorded staff ratio: {staff['value_text']}.")
            paragraphs.append(
                "A ratio is a snapshot the community supplied. Ask how it changes on nights, weekends, and when several people need help at once."
            )
        else:
            uncertainty.append("No staff ratio is recorded.")

    if "amenities" in topics:
        amenities = next((fact for fact in facts if fact.get("field_key") == "amenities"), None)
        if amenities and amenities.get("value_text") not in {"", "Not recorded"}:
            used.append(amenities)
            paragraphs.append(f"Amenities on file: {amenities['value_text']}.")
        else:
            uncertainty.append("No amenities are recorded.")

    if any(fact.get("verification_status") == "conflict" for fact in used) or facility.get("validation_status") == "conflict":
        uncertainty.append("At least one related detail has a conflict. Read each source before relying on a number.")

    if not paragraphs:
        paragraphs.append(
            "I can help with recorded pricing, care, availability, licensing, staff ratios, amenities, and what to ask about an agreement."
        )
        uncertainty.append("I don't have a specific recorded fact that answers this question.")

    draft = "\n\n".join(paragraphs)
    rewritten = _compose_with_gemini(question, draft, [_citation(fact) for fact in used])
    answer = rewritten or draft
    if DISCLAIMER not in answer:
        answer = f"{answer}\n\n{DISCLAIMER}"

    # Preserve citation order while dropping duplicates.
    seen = set()
    citations = []
    for fact in used:
        marker = (fact.get("field_key"), fact.get("value_text"), fact.get("source_type"))
        if marker in seen:
            continue
        seen.add(marker)
        citations.append(_citation(fact))

    return {
        "answer": answer,
        "citations": citations,
        "uncertainty": uncertainty,
        "disclaimer": DISCLAIMER,
        "topics": topics,
        "used_gemini": bool(rewritten),
    }
