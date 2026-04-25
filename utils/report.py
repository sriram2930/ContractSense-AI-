from fpdf import FPDF
from agents.state import ContractState


RISK_COLORS = {
    "red":    (220, 53, 69),
    "yellow": (255, 193, 7),
    "green":  (40, 167, 69),
}


def sanitize_text(text: str) -> str:
    """Replace Unicode characters unsupported by Helvetica with ASCII equivalents."""
    if not text:
        return ""
    replacements = {
        "\u2014": "--",   "\u2013": "-",    "\u2012": "-",
        "\u2011": "-",    "\u2010": "-",    "\u2018": "'",
        "\u2019": "'",    "\u201A": ",",    "\u201B": "'",
        "\u201C": '"',    "\u201D": '"',    "\u201E": '"',
        "\u201F": '"',    "\u2026": "...",  "\u2022": "-",
        "\u2023": "-",    "\u2043": "-",    "\u00A0": " ",
        "\u00AB": '"',    "\u00BB": '"',    "\u2039": "'",
        "\u203A": "'",    "\u00B7": "-",    "\u2044": "/",
        "\u2015": "--",   "\u2017": "_",    "\u2020": "+",
        "\u2021": "++",   "\u2122": "(TM)", "\u00AE": "(R)",
        "\u00A9": "(C)",  "\u00B0": " deg", "\u00D7": "x",
        "\u00F7": "/",    "\u2248": "~",    "\u2260": "!=",
        "\u2264": "<=",   "\u2265": ">=",
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text.encode("latin-1", errors="ignore").decode("latin-1")


def _section_header(pdf: FPDF, title: str):
    """Reusable navy section header bar."""
    pdf.set_fill_color(30, 39, 97)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, sanitize_text(title), ln=True, fill=True)
    pdf.set_text_color(30, 30, 30)
    pdf.ln(2)


def generate_pdf_report(state: ContractState) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ── Header ────────────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(30, 39, 97)
    pdf.cell(0, 12, "ContractSense AI", ln=True, align="C")

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, "Powered by AgentForge AI  |  NVIDIA NIM (Nemotron)  |  LangGraph", ln=True, align="C")
    pdf.ln(3)
    pdf.set_draw_color(30, 39, 97)
    pdf.set_line_width(0.8)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    # ── Contract Overview ─────────────────────────────────────────────────────
    _section_header(pdf, "  Contract Overview")

    contract_type  = state.get("contract_type", "Unknown")
    jurisdiction   = state.get("jurisdiction", "Unknown")
    jurisdiction_notes = state.get("jurisdiction_notes", "")

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(45, 7, "Contract Type:", ln=False)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, sanitize_text(contract_type), ln=True)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(45, 7, "Governing Jurisdiction:", ln=False)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, sanitize_text(jurisdiction), ln=True)

    if jurisdiction_notes:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(74, 108, 247)
        pdf.cell(0, 6, "Web Search MCP -- Live Legal Context:", ln=True)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(60, 60, 60)
        pdf.multi_cell(0, 5, sanitize_text(jurisdiction_notes))

    pdf.ln(4)

    # ── Overall Risk Score ────────────────────────────────────────────────────
    score = state["overall_risk_score"]
    if score >= 7:
        color  = RISK_COLORS["red"]
        verdict = "HIGH RISK"
    elif score >= 4:
        color  = RISK_COLORS["yellow"]
        verdict = "MODERATE RISK"
    else:
        color  = RISK_COLORS["green"]
        verdict = "LOW RISK"

    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*color)
    pdf.cell(0, 10, sanitize_text(f"Overall Risk Score: {score}/10  -  {verdict}"), ln=True, align="C")
    pdf.ln(2)

    # ── Stats Row ─────────────────────────────────────────────────────────────
    analyses     = state["analyses"]
    red_count    = sum(1 for a in analyses if a["risk_level"] == "red")
    yellow_count = sum(1 for a in analyses if a["risk_level"] == "yellow")
    green_count  = sum(1 for a in analyses if a["risk_level"] == "green")

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 7, sanitize_text(
        f"Clauses Analyzed: {len(analyses)}   |   "
        f"Red (High Risk): {red_count}   "
        f"Yellow (Moderate): {yellow_count}   "
        f"Green (Low Risk): {green_count}"
    ), ln=True, align="C")
    pdf.ln(4)

    # ── Executive Summary ─────────────────────────────────────────────────────
    _section_header(pdf, "  Executive Summary")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 60)
    pdf.multi_cell(0, 6, sanitize_text(state["overall_summary"]))
    pdf.ln(6)

    # ── Clause-by-Clause Analysis ─────────────────────────────────────────────
    _section_header(pdf, "  Clause-by-Clause Analysis")
    pdf.ln(2)

    for i, clause in enumerate(analyses, 1):
        risk_color = RISK_COLORS.get(clause["risk_level"], (100, 100, 100))

        # Clause header
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*risk_color)
        label = sanitize_text(
            f"{i}. [{clause['risk_level'].upper()}  {clause['risk_score']}/10]  {clause['clause_type']}"
        )
        pdf.cell(0, 7, label, ln=True)

        # Original snippet
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(100, 100, 100)
        snippet = clause["clause_text"][:200].replace("\n", " ")
        snippet += "..." if len(clause["clause_text"]) > 200 else ""
        pdf.multi_cell(0, 5, sanitize_text(f'Original: "{snippet}"'))
        pdf.ln(1)

        # Plain English
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(0, 6, "Plain English:", ln=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(50, 50, 50)
        pdf.multi_cell(0, 5, sanitize_text(clause["plain_english"]))
        pdf.ln(1)

        # Jurisdiction flag
        jflag = clause.get("jurisdiction_flag", "")
        if jflag:
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(180, 90, 0)
            pdf.cell(0, 6, "Jurisdiction Note:", ln=True)
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(130, 60, 0)
            pdf.multi_cell(0, 5, sanitize_text(jflag))
            pdf.ln(1)

        # Redline suggestion
        if clause["redline_suggestion"] and clause["redline_suggestion"] != "No change needed.":
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(0, 100, 180)
            pdf.cell(0, 6, "Suggested Redline:", ln=True)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, 5, sanitize_text(clause["redline_suggestion"]))
        else:
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(40, 167, 69)
            pdf.cell(0, 6, "No changes needed for this clause.", ln=True)

        pdf.ln(3)
        pdf.set_draw_color(220, 220, 220)
        pdf.set_line_width(0.3)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

    # ── Footer ────────────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(
        0, 6,
        "ContractSense AI is not a substitute for qualified legal advice. Always consult a licensed attorney.",
        ln=True, align="C"
    )

    return bytes(pdf.output())