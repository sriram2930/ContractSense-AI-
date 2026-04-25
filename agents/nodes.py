import json
import re
import urllib.request
import urllib.parse
from agents.state import ContractState, ClauseAnalysis
from utils.nim_client import call_nim
from utils.parser import chunk_into_clauses


# ── JSON Safety Layer ─────────────────────────────────────────────────────────

def safe_parse_json(raw: str, fallback: dict) -> dict:
    """
    Attempts multiple strategies to parse LLM JSON output.
    Handles truncated responses, extra preamble text, and malformed JSON.
    Falls back gracefully if all strategies fail.

    Strategy 1: Strip markdown fences and direct parse
    Strategy 2: Extract first { } block via regex
    Strategy 3: Attempt to close truncated JSON
    Strategy 4: Return fallback dict
    """
    # Strategy 1 — strip markdown fences and direct parse
    try:
        clean = re.sub(r"```json|```", "", raw).strip()
        return json.loads(clean)
    except Exception:
        pass

    # Strategy 2 — extract first complete { } block
    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass

    # Strategy 3 — attempt to close truncated JSON
    try:
        clean = re.sub(r"```json|```", "", raw).strip()
        clean = re.sub(r",\s*$", "", clean)   # remove trailing comma
        if clean.count('"') % 2 != 0:         # close open string
            clean += '"'
        if not clean.endswith("}"):            # close open object
            clean += "}"
        return json.loads(clean)
    except Exception:
        pass

    # All strategies failed — return fallback
    return fallback


# ── Node 1: Clause Extractor ──────────────────────────────────────────────────

def clause_extractor_node(state: ContractState) -> ContractState:
    """Splits raw contract text into individual clauses and detects contract type."""
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
            parsed = json.loads(clean)
            if isinstance(parsed, list):
                clauses = parsed
            else:
                clauses = [state["raw_text"]]
        except Exception:
            clauses = [state["raw_text"]]

    # Detect contract type
    type_system = (
        "You are a legal document classifier. Based on the contract text below, "
        "identify the contract type. Return ONLY one of these exact strings: "
        "NDA, Employment, Freelance, SaaS, Lease, Other"
    )
    try:
        contract_type = call_nim(
            type_system, state["raw_text"][:2000], max_tokens=10
        ).strip()
        if contract_type not in ["NDA", "Employment", "Freelance", "SaaS", "Lease"]:
            contract_type = "Other"
    except Exception:
        contract_type = "Other"

    return {**state, "clauses": clauses, "contract_type": contract_type}


# ── Node 2: Risk Classifier ───────────────────────────────────────────────────

CLAUSE_SYSTEM = """You are an expert contract lawyer protecting the interests of the person signing this contract.

For the given clause, return a JSON object with EXACTLY these keys:
{
  "clause_type": "<type, e.g. Indemnification, Non-Compete, IP Assignment, Payment, Termination, Liability Cap, Confidentiality, Governing Law, Arbitration, Security Deposit, Early Termination, Subletting, Other>",
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

CLAUSE_FALLBACK = {
    "clause_type": "Unknown",
    "risk_level": "yellow",
    "risk_score": 5,
    "plain_english": "Could not analyze this clause — please review manually.",
    "redline_suggestion": "Review manually.",
}


def risk_classifier_node(state: ContractState) -> ContractState:
    """Classifies each clause by risk level using Nemotron."""
    analyses: list[ClauseAnalysis] = []

    for clause in state["clauses"]:
        if len(clause.strip()) < 50:
            continue
        try:
            raw = call_nim(CLAUSE_SYSTEM, clause[:2000], max_tokens=512)
            data = safe_parse_json(raw, CLAUSE_FALLBACK)
            analyses.append(
                ClauseAnalysis(
                    clause_text=clause,
                    clause_type=data.get("clause_type", "Other"),
                    risk_level=data.get("risk_level", "yellow"),
                    risk_score=int(data.get("risk_score", 5)),
                    plain_english=data.get("plain_english", ""),
                    redline_suggestion=data.get("redline_suggestion", ""),
                    jurisdiction_flag="",
                )
            )
        except Exception:
            analyses.append(
                ClauseAnalysis(
                    clause_text=clause,
                    clause_type="Unknown",
                    risk_level="yellow",
                    risk_score=5,
                    plain_english="Could not analyze this clause.",
                    redline_suggestion="Review manually.",
                    jurisdiction_flag="",
                )
            )

    return {**state, "analyses": analyses}


# ── Node 3: Jurisdiction Agent + Web Search MCP ───────────────────────────────

# All 50 US states for validation — prevents hallucinated non-state values
KNOWN_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming",
]


def _web_search_mcp(query: str) -> str:
    """
    Web Search MCP tool call.
    Uses DuckDuckGo instant answer API as the MCP search backend.
    Returns a plain text summary of search results.
    """
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={"User-Agent": "ContractSenseAI/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            result = data.get("Abstract", "") or data.get("Answer", "")
            if not result and data.get("RelatedTopics"):
                result = data["RelatedTopics"][0].get("Text", "")
            return result if result else "No specific legal data found."
    except Exception as e:
        return f"Web search unavailable: {str(e)}"


def jurisdiction_agent_node(state: ContractState) -> ContractState:
    """
    Detects governing law from analyses, fires Web Search MCP for
    real-time state law context, and enriches risky clause flags.

    Two-stage detection:
    Stage 1a: Look for a dedicated Governing Law clause in analyses
    Stage 1b: Fallback — scan raw contract text for state law citations
              (handles CA standard leases, state-specific forms, etc.)
    """
    analyses = state["analyses"]
    jurisdiction = "Unknown"
    jurisdiction_notes = ""

    # ── Stage 1a: Check for dedicated Governing Law clause ────────────────────
    for analysis in analyses:
        if analysis["clause_type"] == "Governing Law":
            system = (
                "Extract ONLY the US state name from this governing law clause. "
                "Return just the state name, e.g. 'California'. "
                "If no US state is mentioned, return 'Unknown'."
            )
            try:
                result = call_nim(
                    system, analysis["clause_text"][:500], max_tokens=10
                ).strip()
                if result in KNOWN_STATES:
                    jurisdiction = result
            except Exception:
                pass
            break

    # ── Stage 1b: Fallback — scan raw text for state law references ───────────
    # Catches contracts like California standard leases (C.A.R. Form LR) that
    # reference "California Civil Code § 1950.5" throughout without a single
    # dedicated Governing Law clause.
    if jurisdiction == "Unknown":
        system = (
            "You are a legal document analyzer. Read this contract and identify "
            "which US state's laws govern it. Look for any of: explicit state "
            "names in legal citations (e.g. 'California Civil Code'), state-specific "
            "form identifiers (e.g. 'C.A.R. Form' = California), governing law "
            "language, or state statutes referenced. "
            "Return ONLY the state name, e.g. 'California'. "
            "If truly unknown, return 'Unknown'."
        )
        try:
            result = call_nim(
                system, state["raw_text"][:3000], max_tokens=10
            ).strip()
            if result in KNOWN_STATES:
                jurisdiction = result
        except Exception:
            jurisdiction = "Unknown"

    # ── Stage 2: Web Search MCP for real-time legal context ──────────────────
    if jurisdiction != "Unknown":
        query = f"{jurisdiction} tenant landlord rental agreement law rights 2024"
        search_result = _web_search_mcp(query)

        system = (
            f"You are a legal advisor. Based on this information about {jurisdiction} law, "
            "write 2 sentences explaining the key legal context for someone signing a contract "
            f"governed by {jurisdiction} law. Be specific and practical."
        )
        try:
            jurisdiction_notes = call_nim(
                system, search_result[:1500], max_tokens=200
            )
        except Exception:
            jurisdiction_notes = f"Contract governed by {jurisdiction} law. Review state-specific regulations carefully."
    else:
        jurisdiction_notes = "Governing law not detected. Review contract jurisdiction carefully before signing."

    # ── Stage 3: Enrich clause analyses with jurisdiction flags ──────────────
    updated_analyses = []
    HIGH_RISK_IN_SOME_STATES = [
        "Non-Compete", "IP Assignment", "Arbitration", "Indemnification",
        "Early Termination", "Security Deposit", "Subletting",
    ]
    STATE_FRIENDLY   = ["California", "Minnesota", "North Dakota", "Oklahoma"]
    STATE_UNFRIENDLY = ["Delaware", "Florida", "Texas", "New York"]

    for analysis in analyses:
        flag = ""
        if analysis["clause_type"] in HIGH_RISK_IN_SOME_STATES:
            if jurisdiction in STATE_FRIENDLY:
                flag = f"Note: {jurisdiction} has strong tenant/worker protections — this clause may be limited or unenforceable."
            elif jurisdiction in STATE_UNFRIENDLY:
                flag = f"Warning: {jurisdiction} enforces this clause strictly — negotiate carefully."
        updated_analyses.append({**analysis, "jurisdiction_flag": flag})

    return {
        **state,
        "analyses": updated_analyses,
        "jurisdiction": jurisdiction,
        "jurisdiction_notes": jurisdiction_notes,
    }


# ── Node 4: Redline Negotiator ────────────────────────────────────────────────

REDLINE_SYSTEM = """You are an expert contract negotiator. Your job is to rewrite risky contract clauses into fairer alternatives that protect the signer.

Given a clause, its type, risk score, and jurisdiction context, return a JSON object with EXACTLY these keys:
{
  "improved_redline": "<a specific, professional, legally-sound alternative clause wording that is fairer to the signer>",
  "negotiation_tip": "<one practical sentence on how to raise this in negotiation>"
}

Rules:
- Be specific — write actual clause language, not generic advice
- Keep the redline professional and legally appropriate
- If the clause is already green (risk score 1-3), return the original wording with 'No change needed.'
- Return ONLY the JSON object. No preamble."""

REDLINE_FALLBACK = {
    "improved_redline": "",
    "negotiation_tip": "",
}


def redline_negotiator_node(state: ContractState) -> ContractState:
    """
    Standalone redline agent — improves redline suggestions for all
    red and yellow clauses using jurisdiction context.
    """
    updated_analyses = []
    jurisdiction = state.get("jurisdiction", "Unknown")
    jurisdiction_notes = state.get("jurisdiction_notes", "")

    for analysis in state["analyses"]:
        if analysis["risk_score"] <= 3:
            updated_analyses.append(analysis)
            continue

        user_prompt = f"""Clause type: {analysis["clause_type"]}
Risk score: {analysis["risk_score"]}/10
Jurisdiction: {jurisdiction}
Jurisdiction context: {jurisdiction_notes}

Original clause:
{analysis["clause_text"][:1000]}

Current redline suggestion:
{analysis["redline_suggestion"]}

Generate an improved, specific redline and negotiation tip."""

        try:
            raw = call_nim(REDLINE_SYSTEM, user_prompt, max_tokens=400)
            data = safe_parse_json(raw, REDLINE_FALLBACK)
            improved = data.get("improved_redline", "") or analysis["redline_suggestion"]
            tip = data.get("negotiation_tip", "")
            updated_plain = analysis["plain_english"]
            if tip:
                updated_plain += f" Tip: {tip}"
            updated_analyses.append({
                **analysis,
                "redline_suggestion": improved,
                "plain_english": updated_plain,
            })
        except Exception:
            updated_analyses.append(analysis)

    return {**state, "analyses": updated_analyses}


# ── Node 5: HITL Checkpoint ───────────────────────────────────────────────────

def hitl_checkpoint_node(state: ContractState) -> ContractState:
    """
    Human-in-the-Loop checkpoint.
    Checks hitl_approved flag — Streamlit handles the UI pause.
    """
    if not state.get("hitl_approved", False):
        return {**state, "hitl_approved": False}
    return {**state, "hitl_approved": True}


# ── Node 6: Report Generator ──────────────────────────────────────────────────

def report_generator_node(state: ContractState) -> ContractState:
    """Computes overall risk score and writes an executive summary."""
    analyses = state["analyses"]
    if not analyses:
        return {**state, "overall_risk_score": 0.0, "overall_summary": "No clauses found."}

    avg_score    = sum(a["risk_score"] for a in analyses) / len(analyses)
    red_count    = sum(1 for a in analyses if a["risk_level"] == "red")
    yellow_count = sum(1 for a in analyses if a["risk_level"] == "yellow")
    green_count  = sum(1 for a in analyses if a["risk_level"] == "green")
    red_types    = [a["clause_type"] for a in analyses if a["risk_level"] == "red"]

    jurisdiction       = state.get("jurisdiction", "Unknown")
    jurisdiction_notes = state.get("jurisdiction_notes", "")
    contract_type      = state.get("contract_type", "Unknown")

    system = "You are a legal risk advisor. Write a concise 3-sentence executive summary for a non-lawyer."
    user = f"""Contract analysis results:
- Contract type: {contract_type}
- Governing jurisdiction: {jurisdiction}
- Jurisdiction context: {jurisdiction_notes}
- Overall risk score: {avg_score:.1f}/10
- Red clauses ({red_count}): {', '.join(red_types) if red_types else 'None'}
- Yellow clauses: {yellow_count}
- Green clauses: {green_count}

Summarize the key risks and whether the signer should proceed, negotiate, or reject."""

    try:
        summary = call_nim(system, user, max_tokens=300)
    except Exception:
        summary = f"Overall risk score: {avg_score:.1f}/10. Found {red_count} high-risk clauses. Review carefully before signing."

    return {
        **state,
        "overall_risk_score": round(avg_score, 1),
        "overall_summary": summary,
    }