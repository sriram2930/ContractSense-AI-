from langgraph.graph import StateGraph, END
from agents.state import ContractState
from agents.nodes import (
    clause_extractor_node,
    risk_classifier_node,
    jurisdiction_agent_node,
    redline_negotiator_node,
    report_generator_node,
)


def build_pre_hitl_pipeline() -> StateGraph:
    """
    Pipeline that runs up to redline negotiator and stops.
    Streamlit shows HITL confirmation UI after this completes.
    """
    graph = StateGraph(ContractState)

    graph.add_node("clause_extractor",   clause_extractor_node)
    graph.add_node("risk_classifier",    risk_classifier_node)
    graph.add_node("jurisdiction_agent", jurisdiction_agent_node)
    graph.add_node("redline_negotiator", redline_negotiator_node)

    graph.set_entry_point("clause_extractor")
    graph.add_edge("clause_extractor",   "risk_classifier")
    graph.add_edge("risk_classifier",    "jurisdiction_agent")
    graph.add_edge("jurisdiction_agent", "redline_negotiator")
    graph.add_edge("redline_negotiator", END)

    return graph.compile()


def build_post_hitl_pipeline() -> StateGraph:
    """
    Pipeline that runs only the report generator after HITL confirmation.
    Receives the full state from the pre-HITL run.
    """
    graph = StateGraph(ContractState)
    graph.add_node("report_generator", report_generator_node)
    graph.set_entry_point("report_generator")
    graph.add_edge("report_generator", END)
    return graph.compile()


pre_hitl_pipeline  = build_pre_hitl_pipeline()
post_hitl_pipeline = build_post_hitl_pipeline()


def analyze_contract_pre_hitl(raw_text: str) -> ContractState:
    """Run pipeline up to HITL checkpoint. Returns state for Streamlit to display."""
    initial_state: ContractState = {
        "raw_text": raw_text,
        "contract_type": "Unknown",
        "clauses": [],
        "analyses": [],
        "jurisdiction": "Unknown",
        "jurisdiction_notes": "",
        "overall_risk_score": 0.0,
        "overall_summary": "",
        "hitl_approved": False,
        "error": None,
    }
    return pre_hitl_pipeline.invoke(initial_state)


def analyze_contract_post_hitl(state: ContractState) -> ContractState:
    """Run report generator after user confirms HITL. Receives existing state."""
    return post_hitl_pipeline.invoke({**state, "hitl_approved": True})