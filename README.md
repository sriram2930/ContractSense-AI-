# ContractSense AI ⚖️
### Powered by AgentForge AI × NVIDIA NIM (Nemotron)

> Upload any contract. Get instant risk analysis. Protect yourself before you sign.

---

## What it does

ContractSense AI is a multi-agent legal assistant that analyzes contracts and flags unfavorable terms — without needing a lawyer.

**Agent Pipeline (LangGraph):**
```
PDF/DOCX Upload → Clause Extractor → Risk Classifier → Explainer → Redline Agent → Report Generator
```

Each clause gets:
- A **risk level**: 🔴 Red / 🟡 Yellow / 🟢 Green
- A **risk score**: 1–10
- A **plain English explanation** of what it means for you
- A **redline suggestion** — a fairer alternative wording

---

## Setup

```bash
# 1. Clone and enter the project
cd contractsense

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your API key
cp .env.example .env
# Edit .env and add your NVIDIA_API_KEY

# 4. Run the app
streamlit run app.py
```

---

## Project Structure

```
contractsense/
├── app.py                        # Streamlit frontend
├── requirements.txt
├── .env.example
├── agents/
│   ├── state.py                  # LangGraph state schema
│   ├── nodes.py                  # Agent node functions
│   └── pipeline.py               # LangGraph graph builder
├── utils/
│   ├── parser.py                 # PDF/DOCX/TXT text extraction
│   ├── nim_client.py             # NVIDIA NIM API client
│   └── report.py                 # PDF report generator
└── sample_contracts/
    └── sample_nda.txt            # Demo contract for hackathon
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| LLM | NVIDIA NIM — Nemotron 70B |
| Agent Orchestration | LangGraph |
| Frontend | Streamlit |
| Document Parsing | pdfplumber, python-docx |
| Report Generation | fpdf2 |

---

## Hackathon Demo Flow

1. Launch app → upload `sample_contracts/sample_nda.txt`
2. Enter NVIDIA API key in sidebar
3. Click **Analyze Contract**
4. Watch agents fire in real time
5. Review clause-by-clause breakdown
6. Download the PDF risk report

---

*ContractSense AI is not a substitute for qualified legal advice.*
