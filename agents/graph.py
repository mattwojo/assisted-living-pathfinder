"""Durable LangGraph routing for ingest, curate, search, and engage."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph

from agents.curator import curate_listing
from agents.engagement import answer_question
from agents.ingestion import normalize_listing
from agents.search_agent import match_facilities
from agents.state import AgentState


def _logs(state: AgentState, message: str) -> list[str]:
    return [*state.get("agent_logs", []), message]


def ingest_node(state: AgentState) -> dict[str, Any]:
    facility, facts = normalize_listing(state["query_payload"])
    if not facility["name"]:
        raise ValueError("A community name is required.")
    name = facility["name"]
    return {
        "output_result": {"facility": facility, "facts": facts},
        "agent_logs": _logs(state, f"Ingestion normalized the listing for {name} and recorded {len(facts)} facility-provided facts."),
        "messages": [AIMessage(content=f"Normalized listing for {name}.")],
    }


def curate_node(state: AgentState) -> dict[str, Any]:
    result = dict(state.get("output_result") or {})
    payload = state["query_payload"]
    facility = result.get("facility") or payload.get("facility") or {}
    facts = list(result.get("facts") or payload.get("facts") or [])
    facts.extend(payload.get("existing_facts") or [])
    flags, status = curate_listing(facility, facts)
    result["flags"] = flags
    result["validation_status"] = status
    summary = f"Curator set status to {status} with {len(flags)} flag(s)."
    return {
        "output_result": result,
        "agent_logs": _logs(state, summary),
        "messages": [AIMessage(content=summary)],
    }


def search_node(state: AgentState) -> dict[str, Any]:
    payload = state["query_payload"]
    result = match_facilities(
        payload.get("facilities") or [],
        payload.get("query") or "",
        payload.get("filters") or {},
    )
    interpreted = result["interpreted"]
    summary = (
        f"Search interpreted care={interpreted['care_levels'] or ['any']}, "
        f"city={interpreted['city'] or 'any'} ({interpreted['city_mode'] or 'n/a'}), "
        f"budget={interpreted['max_budget'] if interpreted['max_budget'] is not None else 'any'}."
    )
    return {
        "output_result": result,
        "agent_logs": _logs(state, summary),
        "messages": [AIMessage(content=summary)],
    }


def engage_node(state: AgentState) -> dict[str, Any]:
    payload = state["query_payload"]
    result = answer_question(payload.get("facility") or {}, payload.get("question") or "")
    summary = "Engagement answered from the facility record and domain templates."
    if result.get("used_gemini"):
        summary += " Gemini rewrote the wording; citations still come from the record."
    return {
        "output_result": result,
        "agent_logs": _logs(state, summary),
        "messages": [AIMessage(content=summary)],
    }


def _route(state: AgentState) -> str:
    action = state.get("current_action") or ""
    if action not in {"ingest", "curate", "search", "engage"}:
        raise ValueError(f"Unknown agent action: {action}")
    return action


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("ingest", ingest_node)
    builder.add_node("curate", curate_node)
    builder.add_node("search", search_node)
    builder.add_node("engage", engage_node)
    builder.add_conditional_edges(
        START,
        _route,
        {"ingest": "ingest", "curate": "curate", "search": "search", "engage": "engage"},
    )
    builder.add_edge("ingest", "curate")
    builder.add_edge("curate", END)
    builder.add_edge("search", END)
    builder.add_edge("engage", END)
    return builder.compile()


graph = build_graph()


def run_action(action: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Run one agent path and return its structured result plus the audit log."""
    if action == "update":
        action = "ingest"
    preview = payload.get("query") or payload.get("question") or payload.get("name") or action
    state = graph.invoke(
        {
            "messages": [HumanMessage(content=str(preview))],
            "current_action": action,
            "query_payload": payload,
            "agent_logs": [f"Started {action}."],
            "output_result": {},
        }
    )
    result = dict(state.get("output_result") or {})
    result["agent_logs"] = state.get("agent_logs") or []
    return result
