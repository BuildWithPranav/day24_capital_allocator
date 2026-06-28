from __future__ import annotations
from typing import TypedDict, Optional
import structlog
from langgraph.graph import StateGraph, END
from .models import RawListing, Financials, TriageResult, SynergyAnalysis, DealMemo
from .agents.triage import run_triage
from .agents.synergy import analyze_synergy
from .agents.memo import build_memo

log = structlog.get_logger()

class GraphState(TypedDict, total=False):
    listing: RawListing
    financials: Optional[Financials]
    triage: Optional[TriageResult]
    synergy: Optional[SynergyAnalysis]
    memo: Optional[DealMemo]
    error: Optional[str]

async def node_triage(state: GraphState) -> GraphState:
    triage = await run_triage(state["listing"])
    return {"triage": triage, "financials": triage.financials}

def gate_triage(state: GraphState) -> str:
    t = state.get("triage")
    if not t or not t.pass_triage:
        return "reject"
    return "continue"

async def node_synergy(state: GraphState) -> GraphState:
    synergy = await analyze_synergy(state["listing"], state["triage"])  # type: ignore
    return {"synergy": synergy}

async def node_memo(state: GraphState) -> GraphState:
    memo = await build_memo(state["listing"], state["triage"], state["synergy"])  # type: ignore
    return {"memo": memo}

def build_allocator_graph():
    g = StateGraph(GraphState)
    g.add_node("triage", node_triage)
    g.add_node("synergy", node_synergy)
    g.add_node("memo", node_memo)
    g.set_entry_point("triage")
    g.add_conditional_edges("triage", gate_triage, {"continue": "synergy", "reject": END})
    g.add_edge("synergy", "memo")
    g.add_edge("memo", END)
    return g.compile()

allocator_graph = build_allocator_graph()

async def run_deal(listing: RawListing) -> DealMemo | None:
    result = await allocator_graph.ainvoke({"listing": listing})
    return result.get("memo")
