from typing import TypedDict, Optional


class ClauseAnalysis(TypedDict):
    clause_text: str
    clause_type: str
    risk_level: str             # "red" | "yellow" | "green"
    risk_score: int             # 1-10
    plain_english: str
    redline_suggestion: str
    jurisdiction_flag: str      # extra warning if jurisdiction makes it worse


class ContractState(TypedDict):
    raw_text: str
    contract_type: str          # "NDA" | "Employment" | "Freelance" | "SaaS" | "Unknown"
    clauses: list[str]
    analyses: list[ClauseAnalysis]
    jurisdiction: str           # e.g. "California" | "Delaware" | "Unknown"
    jurisdiction_notes: str     # real-time legal context from web search MCP
    overall_risk_score: float
    overall_summary: str
    hitl_approved: bool         # HITL checkpoint flag
    error: Optional[str]