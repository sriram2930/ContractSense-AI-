from langgraph.graph import StateGraph, END
from agents.state import ContractState
from agents.nodes import clause_extractor_node, risk_classifier_node, report_generator_node


def build_pipeline() -> StateGraph:
    graph = StateGraph(ContractState)

    graph.add_node("clause_extractor", clause_extractor_node)
    graph.add_node("risk_classifier", risk_classifier_node)
    graph.add_node("report_generator", report_generator_node)

    graph.set_entry_point("clause_extractor")
    graph.add_edge("clause_extractor", "risk_classifier")
    graph.add_edge("risk_classifier", "report_generator")
    graph.add_edge("report_generator", END)

    return graph.compile()


pipeline = build_pipeline()


def analyze_contract(raw_text: str) -> ContractState:
    initial_state: ContractState = {
        "raw_text": raw_text,
        "clauses": [],
        "analyses": [],
        "overall_risk_score": 0.0,
        "overall_summary": "",
        "error": None,
    }
    return pipeline.invoke(initial_state)