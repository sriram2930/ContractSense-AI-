import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from utils.parser import extract_text
from utils.report import generate_pdf_report
from agents.pipeline import analyze_contract_pre_hitl, analyze_contract_post_hitl

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
    .clause-card { background: #f8f9fa; border-radius: 10px; padding: 1rem 1.2rem; margin-bottom: 1rem; border-left: 5px solid #dee2e6; }
    .red-card    { border-left-color: #dc3545 !important; }
    .yellow-card { border-left-color: #ffc107 !important; }
    .green-card  { border-left-color: #28a745 !important; }
    .badge       { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
    .badge-red   { background: #f8d7da; color: #842029; }
    .badge-yellow{ background: #fff3cd; color: #664d03; }
    .badge-green { background: #d1e7dd; color: #0a3622; }
    .redline     { background: #e8f4fd; border-left: 3px solid #0d6efd; padding: 0.6rem 0.8rem; border-radius: 6px; font-size: 0.88rem; color: #0a2d4a; }
    .plain-eng   { background: #fff9e6; border-left: 3px solid #ffc107; padding: 0.6rem 0.8rem; border-radius: 6px; font-size: 0.88rem; color: #4a3800; }
    .juris-flag  { background: #fff3e0; border-left: 3px solid #ff9800; padding: 0.5rem 0.8rem; border-radius: 6px; font-size: 0.85rem; color: #7a4100; margin-top: 0.5rem; }
    .juris-box   { background: #f0f4ff; border-left: 4px solid #4A6CF7; padding: 0.8rem 1rem; border-radius: 8px; font-size: 0.92rem; color: #1E2761; margin-bottom: 1rem; }
    .hitl-box    { background: #fff8e1; border: 2px solid #ffc107; border-radius: 12px; padding: 1.2rem; margin: 1rem 0; color: #1a1a1a; }
    .hitl-box h4 { color: #1a1a1a !important; }
    .hitl-box p  { color: #2d2d2d !important; }
    .stProgress > div > div { border-radius: 8px; }
    .contract-type-pill { display: inline-block; background: #e8eaff; color: #1E2761; padding: 4px 14px; border-radius: 20px; font-size: 0.82rem; font-weight: 600; margin-right: 8px; }
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
2. **Agent 1** — extracts & chunks clauses
3. **Agent 2** — classifies risk per clause
4. **Agent 3** — detects jurisdiction via Web Search MCP
5. **Agent 4** — generates improved redlines
6. **You confirm** — HITL checkpoint
7. **Agent 5** — compiles final risk report
8. **Download** your PDF report
    """)
    st.markdown("---")
    st.caption("ContractSense AI is not a substitute for qualified legal advice.")

# ── Session state for HITL ────────────────────────────────────────────────────
if "pipeline_result" not in st.session_state:
    st.session_state.pipeline_result = None
if "hitl_pending" not in st.session_state:
    st.session_state.hitl_pending = False
if "raw_text" not in st.session_state:
    st.session_state.raw_text = None

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
                if not raw_text or len(raw_text.strip()) < 100:
                    st.error("⚠️ The uploaded file appears to be empty or unreadable. Please try a different file.")
                    st.stop()
                st.session_state.raw_text = raw_text
            except Exception as e:
                st.error(f"Could not read file: {e}")
                st.stop()

        st.info(f"📝 Extracted {len(raw_text):,} characters from document")

        # ── Run Pipeline (stops before report — HITL pending) ─────────────────
        progress = st.progress(0, text="🤖 Agent 1/6 — Extracting clauses...")

        steps = [
            (17,  "🤖 Agent 1/6 — Extracting clauses..."),
            (34,  "🤖 Agent 2/6 — Classifying risk..."),
            (51,  "🤖 Agent 3/6 — Detecting jurisdiction via Web Search MCP..."),
            (68,  "🤖 Agent 4/6 — Generating redlines..."),
            (85,  "⏸️  HITL Checkpoint — awaiting your confirmation..."),
        ]

        with st.spinner("Running ContractSense pipeline..."):
            try:
                for pct, msg in steps:
                    progress.progress(pct, text=msg)
                # Run pre-HITL pipeline — stops after redline negotiator
                result = analyze_contract_pre_hitl(raw_text)
                st.session_state.pipeline_result = result
                st.session_state.hitl_pending = True
                progress.progress(85, text="⏸️ HITL Checkpoint — awaiting your confirmation...")
            except Exception as e:
                st.error(f"Pipeline error: {e}")
                st.stop()

# ── Show results if pipeline has run ─────────────────────────────────────────
if st.session_state.pipeline_result:
    result = st.session_state.pipeline_result
    analyses = result["analyses"]

    if not analyses:
        st.warning("⚠️ No clauses were detected in this document. Try a different contract.")
        st.stop()

    score = result["overall_risk_score"]
    red_count    = sum(1 for a in analyses if a["risk_level"] == "red")
    yellow_count = sum(1 for a in analyses if a["risk_level"] == "yellow")
    green_count  = sum(1 for a in analyses if a["risk_level"] == "green")

    if score >= 7:
        verdict = "🔴 HIGH RISK"
    elif score >= 4:
        verdict = "🟡 MODERATE RISK"
    else:
        verdict = "🟢 LOW RISK"

    # ── Contract Type + Jurisdiction Info ─────────────────────────────────────
    st.markdown("## 📄 Contract Overview")
    col_ct, col_j = st.columns(2)
    with col_ct:
        contract_type = result.get("contract_type", "Unknown")
        st.markdown(
            f'<span class="contract-type-pill">📋 {contract_type}</span>',
            unsafe_allow_html=True
        )
        st.caption("Contract type detected")
    with col_j:
        jurisdiction = result.get("jurisdiction", "Unknown")
        st.markdown(
            f'<span class="contract-type-pill">⚖️ {jurisdiction}</span>',
            unsafe_allow_html=True
        )
        st.caption("Governing jurisdiction")

    jurisdiction_notes = result.get("jurisdiction_notes", "")
    if jurisdiction_notes:
        st.markdown(
            f'<div class="juris-box">🌐 <b>Web Search MCP — Live Legal Context:</b><br>{jurisdiction_notes}</div>',
            unsafe_allow_html=True
        )

    st.divider()

    # ── Overall Risk Score ────────────────────────────────────────────────────
    st.markdown("## 📊 Risk Overview")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Overall Score", f"{score}/10")
    m2.metric("Verdict", verdict)
    m3.metric("🔴 Red Clauses", red_count)
    m4.metric("🟡 Yellow Clauses", yellow_count)
    m5.metric("🟢 Green Clauses", green_count)
    st.progress(int(score * 10), text=f"Risk Level: {score}/10")

    # ── HITL Checkpoint ───────────────────────────────────────────────────────
    if st.session_state.hitl_pending:
        st.markdown("---")
        st.markdown(
            f"""<div class="hitl-box">
            <h4>⏸️ Human-in-the-Loop Checkpoint</h4>
            <p>The pipeline has analyzed <b>{len(analyses)} clauses</b> and found 
            <b style='color:#dc3545'>{red_count} high-risk</b>, 
            <b style='color:#ffc107'>{yellow_count} moderate</b>, and 
            <b style='color:#28a745'>{green_count} low-risk</b> clauses.</p>
            <p>Confirm to generate the executive summary and downloadable PDF report.</p>
            </div>""",
            unsafe_allow_html=True
        )

        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("✅ Confirm — Generate Full Report", type="primary", use_container_width=True):
                with st.spinner("🤖 Agent 6/6 — Generating report..."):
                    try:
                        final_result = analyze_contract_post_hitl(
                            st.session_state.pipeline_result
                        )
                        st.session_state.pipeline_result = final_result
                        st.session_state.hitl_pending = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Report generation failed: {e}")
        with col_no:
            if st.button("❌ Cancel Analysis", use_container_width=True):
                st.session_state.pipeline_result = None
                st.session_state.hitl_pending = False
                st.session_state.raw_text = None
                st.rerun()

    # ── Executive Summary (only after HITL approved) ──────────────────────────
    if not st.session_state.hitl_pending and result.get("overall_summary"):
        st.markdown("### 📋 Executive Summary")
        st.info(result["overall_summary"])

    st.divider()

    # ── Clause Breakdown ──────────────────────────────────────────────────────
    st.markdown("## 🔍 Clause-by-Clause Analysis")

    tab_all, tab_red, tab_yellow, tab_green = st.tabs([
        f"All ({len(analyses)})",
        f"🔴 Red ({red_count})",
        f"🟡 Yellow ({yellow_count})",
        f"🟢 Green ({green_count})"
    ])

    def render_clauses(clauses_list):
        if not clauses_list:
            st.info("No clauses in this category.")
            return
        for i, clause in enumerate(clauses_list, 1):
            level = clause["risk_level"]
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

                # Jurisdiction flag
                jflag = clause.get("jurisdiction_flag", "")
                if jflag:
                    st.markdown(
                        f'<div class="juris-flag">⚖️ {jflag}</div>',
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

    # ── Download Report (only after HITL approved) ────────────────────────────
    if not st.session_state.hitl_pending and result.get("overall_summary"):
        st.divider()
        st.markdown("## 📥 Download Report")
        with st.spinner("Generating PDF report..."):
            try:
                pdf_bytes = generate_pdf_report(result)
                st.download_button(
                    label="⬇️ Download Full Risk Report (PDF)",
                    data=bytes(pdf_bytes),
                    file_name="contractsense_report.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"PDF generation failed: {e}")

else:
    # ── Empty State ───────────────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center; padding: 3rem 1rem; color: #6c757d;">
        <div style="font-size: 4rem;">📄</div>
        <h3 style="color:#495057">Upload a contract to get started</h3>
        <p>Supports NDA, employment agreements, freelance contracts, service agreements, and more.</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        **🔍 Clause Extraction**
        Automatically identifies and separates individual contract clauses
        """)
    with c2:
        st.markdown("""
        **⚠️ Risk Classification**
        Each clause scored Red / Yellow / Green with a 1-10 risk score
        """)
    with c3:
        st.markdown("""
        **✏️ Redline Suggestions**
        Fairer alternative wording with negotiation tips for every risky clause
        """)