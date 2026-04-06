import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from utils.parser import extract_text
from utils.report import generate_pdf_report
from agents.pipeline import analyze_contract

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ContractSense AI",
    page_icon="⚖️",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-title { font-size: 2.4rem; font-weight: 700; color: #1a1a2e; }
    .sub-title  { font-size: 1rem; color: #6c757d; margin-bottom: 1.5rem; }
    .score-box  { padding: 1.2rem; border-radius: 12px; text-align: center; }
    .clause-card { background: #f8f9fa; border-radius: 10px; padding: 1rem 1.2rem; margin-bottom: 1rem; border-left: 5px solid #dee2e6; }
    .red-card   { border-left-color: #dc3545 !important; }
    .yellow-card{ border-left-color: #ffc107 !important; }
    .green-card { border-left-color: #28a745 !important; }
    .badge      { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
    .badge-red  { background: #f8d7da; color: #842029; }
    .badge-yellow{ background: #fff3cd; color: #664d03; }
    .badge-green{ background: #d1e7dd; color: #0a3622; }
    .redline    { background: #e8f4fd; border-left: 3px solid #0d6efd; padding: 0.6rem 0.8rem; border-radius: 6px; font-size: 0.88rem; }
    .plain-eng  { background: #fff9e6; border-left: 3px solid #ffc107; padding: 0.6rem 0.8rem; border-radius: 6px; font-size: 0.88rem; }
    .stProgress > div > div { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)


# ── Header ────────────────────────────────────────────────────────────────────
col_logo, col_title = st.columns([1, 8])
with col_logo:
    st.markdown("<div style='font-size:3rem;padding-top:0.3rem'>⚖️</div>", unsafe_allow_html=True)
with col_title:
    st.markdown('<div class="main-title">ContractSense AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Upload any contract · Get instant risk analysis · Powered by NVIDIA NIM (Nemotron) · AgentForge AI</div>', unsafe_allow_html=True)

st.divider()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    api_key = st.text_input("NVIDIA API Key", type="password", placeholder="nvapi-...")
    if api_key:
        os.environ["NVIDIA_API_KEY"] = api_key

    st.markdown("---")
    st.markdown("### 📋 How it works")
    st.markdown("""
1. **Upload** your contract (PDF, DOCX, TXT)
2. **Agents fire** — clauses extracted, risk scored, explained
3. **Review** each clause with plain-English explanation
4. **Download** your full risk report PDF
    """)
    st.markdown("---")
    st.caption("ContractSense AI is not a substitute for qualified legal advice.")


# ── Upload Zone ───────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader(
    "Drop your contract here",
    type=["pdf", "docx", "txt"],
    help="Supports PDF, Word (.docx), and plain text files"
)

if uploaded_file:
    st.success(f"✅ Loaded: **{uploaded_file.name}**")

    if st.button("🔍 Analyze Contract", type="primary", use_container_width=True):

        if not os.getenv("NVIDIA_API_KEY"):
            st.error("⚠️ Please enter your NVIDIA API Key in the sidebar.")
            st.stop()

        # ── Extract Text ──────────────────────────────────────────────────────
        with st.spinner("📄 Extracting text from document..."):
            try:
                raw_text = extract_text(uploaded_file)
            except Exception as e:
                st.error(f"Could not read file: {e}")
                st.stop()

        st.info(f"📝 Extracted {len(raw_text):,} characters from document")

        # ── Run Pipeline ──────────────────────────────────────────────────────
        progress = st.progress(0, text="🤖 Agent 1/3 — Extracting clauses...")
        with st.spinner("Running ContractSense pipeline..."):
            try:
                result = analyze_contract(raw_text)
                progress.progress(100, text="✅ Analysis complete!")
            except Exception as e:
                st.error(f"Pipeline error: {e}")
                st.stop()

        # ── Overall Risk Score ────────────────────────────────────────────────
        st.markdown("## 📊 Risk Overview")

        score = result["overall_risk_score"]
        analyses = result["analyses"]
        red_count = sum(1 for a in analyses if a["risk_level"] == "red")
        yellow_count = sum(1 for a in analyses if a["risk_level"] == "yellow")
        green_count = sum(1 for a in analyses if a["risk_level"] == "green")

        if score >= 7:
            score_color = "#dc3545"
            verdict = "🔴 HIGH RISK"
        elif score >= 4:
            score_color = "#ffc107"
            verdict = "🟡 MODERATE RISK"
        else:
            score_color = "#28a745"
            verdict = "🟢 LOW RISK"

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Overall Score", f"{score}/10")
        m2.metric("Verdict", verdict)
        m3.metric("🔴 Red Clauses", red_count)
        m4.metric("🟡 Yellow Clauses", yellow_count)
        m5.metric("🟢 Green Clauses", green_count)

        st.progress(int(score * 10), text=f"Risk Level: {score}/10")

        # ── Executive Summary ─────────────────────────────────────────────────
        st.markdown("### 📋 Executive Summary")
        st.info(result["overall_summary"])

        st.divider()

        # ── Clause Breakdown ──────────────────────────────────────────────────
        st.markdown("## 🔍 Clause-by-Clause Analysis")

        tab_all, tab_red, tab_yellow, tab_green = st.tabs([
            f"All ({len(analyses)})",
            f"🔴 Red ({red_count})",
            f"🟡 Yellow ({yellow_count})",
            f"🟢 Green ({green_count})"
        ])

        def render_clauses(clauses_list):
            for i, clause in enumerate(clauses_list, 1):
                level = clause["risk_level"]
                card_class = f"{level}-card"
                badge_class = f"badge-{level}"

                with st.expander(
                    f"**{i}. {clause['clause_type']}** — Score: {clause['risk_score']}/10",
                    expanded=(level == "red")
                ):
                    st.markdown(
                        f'<span class="badge {badge_class}">{level.upper()} — {clause["risk_score"]}/10</span>',
                        unsafe_allow_html=True
                    )
                    st.markdown("**Original Clause:**")
                    st.caption(clause["clause_text"][:400] + ("..." if len(clause["clause_text"]) > 400 else ""))

                    st.markdown("**Plain English:**")
                    st.markdown(
                        f'<div class="plain-eng">{clause["plain_english"]}</div>',
                        unsafe_allow_html=True
                    )

                    if clause["redline_suggestion"] and clause["redline_suggestion"] != "No change needed.":
                        st.markdown("**💡 Suggested Redline:**")
                        st.markdown(
                            f'<div class="redline">{clause["redline_suggestion"]}</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.success("✅ No changes needed for this clause.")

        with tab_all:
            render_clauses(analyses)
        with tab_red:
            render_clauses([a for a in analyses if a["risk_level"] == "red"])
        with tab_yellow:
            render_clauses([a for a in analyses if a["risk_level"] == "yellow"])
        with tab_green:
            render_clauses([a for a in analyses if a["risk_level"] == "green"])

        st.divider()

        # ── Download Report ───────────────────────────────────────────────────
        st.markdown("## 📥 Download Report")
        with st.spinner("Generating PDF report..."):
            pdf_bytes = generate_pdf_report(result)

        st.download_button(
            label="⬇️ Download Full Risk Report (PDF)",
            data=pdf_bytes,
            file_name="contractsense_report.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

else:
    # ── Empty State ───────────────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center; padding: 3rem 1rem; color: #6c757d;">
        <div style="font-size: 4rem;">📄</div>
        <h3 style="color:#495057">Upload a contract to get started</h3>
        <p>Supports NDA, employment agreements, freelance contracts, service agreements, and more.</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Feature Pills ─────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        **🔍 Clause Extraction**
        Automatically identifies and separates individual contract clauses
        """)
    with c2:
        st.markdown("""
        **⚠️ Risk Classification**
        Each clause scored Red / Yellow / Green with a 1–10 risk score
        """)
    with c3:
        st.markdown("""
        **✏️ Redline Suggestions**
        Fairer alternative wording suggested for every risky clause
        """)