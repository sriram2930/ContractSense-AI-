import json
import re
from agents.state import ContractState, ClauseAnalysis
from utils.nim_client import call_nim
from utils.parser import chunk_into_clauses


# ── Node 1: Clause Extractor ──────────────────────────────────────────────────

def clause_extractor_node(state: ContractState) -> ContractState:
    """Splits raw contract text into individual clauses."""
    clauses = chunk_into_clauses(state["raw_text"])

    # Fallback: if chunking yields < 3 clauses, ask NIM to extract them
    if len(clauses) < 3:
        system = (
            "You are a legal document parser. Extract individual clauses from "
            "the contract below. Return a JSON array of strings, each string "
            "being one clause. Return ONLY the JSON array, no other text."
        )
        raw = call_nim(system, state["raw_text"][:6000], max_tokens=2048)
        try:
            clean = re.sub(r"```json|```", "", raw).strip()
            clauses = json.loads(clean)
        except Exception:
            clauses = [state["raw_text"]]

    return {**state, "clauses": clauses}


# ── Node 2: Risk Classifier + Explainer + Redline (combined for efficiency) ───

CLAUSE_SYSTEM = """You are an expert contract lawyer protecting the interests of the person signing this contract.

For the given clause, return a JSON object with EXACTLY these keys:
{
  "clause_type": "<type, e.g. Indemnification, Non-Compete, IP Assignment, Payment, Termination, Liability Cap, Confidentiality, Governing Law, Arbitration, Other>",
  "risk_level": "<red | yellow | green>",
  "risk_score": <integer 1-10, where 10 is most dangerous to the signer>,
  "plain_english": "<2-3 sentence explanation of what this clause means for the signer in simple language>",
  "redline_suggestion": "<a fairer alternative clause wording, or 'No change needed.' if green>"
}

Risk guidelines:
- red (7-10): Severely favors the other party — e.g. unlimited liability, perpetual IP assignment, broad non-compete
- yellow (4-6): Moderately unfavorable — worth negotiating
- green (1-3): Standard or neutral — acceptable as-is

Return ONLY the JSON object. No preamble, no explanation."""


def risk_classifier_node(state: ContractState) -> ContractState:
    """Classifies, explains, and generates redlines for each clause."""
    analyses: list[ClauseAnalysis] = []

    for clause in state["clauses"]:
        if len(clause.strip()) < 50:
            continue
        try:
            raw = call_nim(CLAUSE_SYSTEM, clause[:2000], max_tokens=512)
            clean = re.sub(r"```json|```", "", raw).strip()
            data = json.loads(clean)
            analyses.append(
                ClauseAnalysis(
                    clause_text=clause,
                    clause_type=data.get("clause_type", "Other"),
                    risk_level=data.get("risk_level", "yellow"),
                    risk_score=int(data.get("risk_score", 5)),
                    plain_english=data.get("plain_english", ""),
                    redline_suggestion=data.get("redline_suggestion", ""),
                )
            )
        except Exception as e:
            analyses.append(
                ClauseAnalysis(
                    clause_text=clause,
                    clause_type="Unknown",
                    risk_level="yellow",
                    risk_score=5,
                    plain_english="Could not analyze this clause.",
                    redline_suggestion="Review manually.",
                )
            )

    return {**state, "analyses": analyses}


# ── Node 3: Report Generator ──────────────────────────────────────────────────

def report_generator_node(state: ContractState) -> ContractState:
    """Computes overall risk score and writes an executive summary."""
    analyses = state["analyses"]
    if not analyses:
        return {**state, "overall_risk_score": 0.0, "overall_summary": "No clauses found."}

    avg_score = sum(a["risk_score"] for a in analyses) / len(analyses)
    red_count = sum(1 for a in analyses if a["risk_level"] == "red")
    yellow_count = sum(1 for a in analyses if a["risk_level"] == "yellow")
    green_count = sum(1 for a in analyses if a["risk_level"] == "green")

    red_types = [a["clause_type"] for a in analyses if a["risk_level"] == "red"]

    system = "You are a legal risk advisor. Write a concise 3-sentence executive summary for a non-lawyer."
    user = f"""Contract analysis results:
- Overall risk score: {avg_score:.1f}/10
- Red clauses ({red_count}): {', '.join(red_types) if red_types else 'None'}
- Yellow clauses: {yellow_count}
- Green clauses: {green_count}

Summarize the key risks and whether the signer should proceed, negotiate, or reject."""

    summary = call_nim(system, user, max_tokens=300)

    return {**state, "overall_risk_score": round(avg_score, 1), "overall_summary": summary}