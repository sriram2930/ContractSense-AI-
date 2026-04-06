from typing import TypedDict, Optional


class ClauseAnalysis(TypedDict):
    clause_text: str
    clause_type: str
    risk_level: str          # "red" | "yellow" | "green"
    risk_score: int          # 1–10
    plain_english: str
    redline_suggestion: str


class ContractState(TypedDict):
    raw_text: str
    clauses: list[str]
    analyses: list[ClauseAnalysis]
    overall_risk_score: float
    overall_summary: str
    error: Optional[str]