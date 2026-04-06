from fpdf import FPDF
from agents.state import ContractState
import io


RISK_COLORS = {
    "red": (220, 53, 69),
    "yellow": (255, 193, 7),
    "green": (40, 167, 69),
}


def generate_pdf_report(state: ContractState) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ── Header ────────────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 12, "ContractSense AI", ln=True, align="C")

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 7, "Powered by AgentForge AI  |  NVIDIA NIM (Nemotron)", ln=True, align="C")
    pdf.ln(4)
    pdf.set_draw_color(200, 200, 200)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    # ── Overall Risk Score ────────────────────────────────────────────────────
    score = state["overall_risk_score"]
    if score >= 7:
        color = RISK_COLORS["red"]
        verdict = "HIGH RISK"
    elif score >= 4:
        color = RISK_COLORS["yellow"]
        verdict = "MODERATE RISK"
    else:
        color = RISK_COLORS["green"]
        verdict = "LOW RISK"

    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*color)
    pdf.cell(0, 8, f"Overall Risk Score: {score}/10  —  {verdict}", ln=True)
    pdf.ln(2)

    # ── Executive Summary ─────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 8, "Executive Summary", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 60)
    pdf.multi_cell(0, 6, state["overall_summary"])
    pdf.ln(6)

    # ── Stats Row ─────────────────────────────────────────────────────────────
    analyses = state["analyses"]
    red_count = sum(1 for a in analyses if a["risk_level"] == "red")
    yellow_count = sum(1 for a in analyses if a["risk_level"] == "yellow")
    green_count = sum(1 for a in analyses if a["risk_level"] == "green")

    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 7, f"Clauses Analyzed: {len(analyses)}   |   Red: {red_count}   Yellow: {yellow_count}   Green: {green_count}", ln=True)
    pdf.ln(4)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    # ── Clause Breakdown ──────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 8, "Clause-by-Clause Analysis", ln=True)
    pdf.ln(3)

    for i, clause in enumerate(analyses, 1):
        color = RISK_COLORS.get(clause["risk_level"], (100, 100, 100))

        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*color)
        label = f"[{clause['risk_level'].upper()}  {clause['risk_score']}/10]  {clause['clause_type']}"
        pdf.cell(0, 7, f"{i}. {label}", ln=True)

        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(80, 80, 80)
        snippet = clause["clause_text"][:200].replace("\n", " ") + ("..." if len(clause["clause_text"]) > 200 else "")
        pdf.multi_cell(0, 5, f'Original: "{snippet}"')

        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(0, 6, "Plain English:", ln=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(50, 50, 50)
        pdf.multi_cell(0, 5, clause["plain_english"])

        if clause["redline_suggestion"] and clause["redline_suggestion"] != "No change needed.":
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(0, 100, 180)
            pdf.cell(0, 6, "Suggested Redline:", ln=True)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, 5, clause["redline_suggestion"])

        pdf.ln(4)
        pdf.set_draw_color(220, 220, 220)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(4)

    # ── Footer ────────────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 6, "ContractSense AI is not a substitute for qualified legal advice. Always consult a licensed attorney for binding decisions.", ln=True, align="C")

    return pdf.output()