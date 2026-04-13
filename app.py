import streamlit as st
import anthropic
import json
import re
from pathlib import Path
import time

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Resume Screener",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Space+Mono:wght@400;700&display=swap');

:root {
    --bg: #0a0a0f;
    --surface: #13131a;
    --border: #1e1e2e;
    --accent: #7c3aed;
    --accent2: #06b6d4;
    --success: #10b981;
    --warn: #f59e0b;
    --danger: #ef4444;
    --text: #e2e8f0;
    --muted: #64748b;
}

html, body, [class*="css"] {
    font-family: 'Space Mono', monospace;
    background: var(--bg);
    color: var(--text);
}

.stApp { background: var(--bg); }

h1,h2,h3 { font-family: 'Syne', sans-serif; font-weight: 800; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border);
}

/* Metric cards */
.metric-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
}
.metric-value { font-size: 2.4rem; font-weight: 800; font-family: 'Syne', sans-serif; }
.metric-label { font-size: 0.7rem; color: var(--muted); text-transform: uppercase; letter-spacing: 2px; }

/* Score badge */
.score-badge {
    display: inline-block;
    padding: 6px 16px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 0.85rem;
    font-family: 'Syne', sans-serif;
}
.badge-high   { background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid rgba(16,185,129,0.3); }
.badge-medium { background: rgba(245,158,11,0.15); color: #f59e0b; border: 1px solid rgba(245,158,11,0.3); }
.badge-low    { background: rgba(239,68,68,0.15);  color: #ef4444; border: 1px solid rgba(239,68,68,0.3); }

/* Result card */
.result-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 28px;
    margin-bottom: 20px;
    transition: border-color 0.2s;
}
.result-card:hover { border-color: var(--accent); }

/* Section header */
.section-header {
    font-family: 'Syne', sans-serif;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--accent2);
    margin-bottom: 8px;
}

/* Tag pill */
.tag {
    display: inline-block;
    background: rgba(124,58,237,0.12);
    color: #a78bfa;
    border: 1px solid rgba(124,58,237,0.25);
    border-radius: 6px;
    padding: 2px 10px;
    font-size: 0.75rem;
    margin: 2px;
}
.tag-missing {
    background: rgba(239,68,68,0.1);
    color: #f87171;
    border-color: rgba(239,68,68,0.25);
}

/* Gauge bar */
.gauge-wrap { background: #1e1e2e; border-radius: 8px; height: 8px; overflow: hidden; margin: 6px 0 14px; }
.gauge-fill  { height: 100%; border-radius: 8px; transition: width 1s ease; }

/* Upload zone */
[data-testid="stFileUploader"] {
    background: var(--surface) !important;
    border: 2px dashed var(--border) !important;
    border-radius: 12px !important;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, var(--accent), #5b21b6) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: 1px !important;
    padding: 12px 28px !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 25px rgba(124,58,237,0.4) !important;
}

/* Text areas & inputs */
.stTextArea textarea, .stTextInput input {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 10px !important;
    font-family: 'Space Mono', monospace !important;
}

/* Divider */
hr { border-color: var(--border) !important; }

/* Info / warning boxes */
.stAlert { border-radius: 10px !important; }

/* Hide default header */
#MainMenu, header, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def score_color(score: int) -> str:
    if score >= 75: return "#10b981"
    if score >= 50: return "#f59e0b"
    return "#ef4444"

def score_badge_class(score: int) -> str:
    if score >= 75: return "badge-high"
    if score >= 50: return "badge-medium"
    return "badge-low"

def score_label(score: int) -> str:
    if score >= 80: return "🟢 Strong Match"
    if score >= 65: return "🟡 Good Match"
    if score >= 50: return "🟠 Moderate Match"
    return "🔴 Weak Match"


def gauge_html(value: int, color: str) -> str:
    return f"""
    <div class="gauge-wrap">
      <div class="gauge-fill" style="width:{value}%; background:{color};"></div>
    </div>"""


def extract_text_from_pdf(file) -> str:
    """Extract text from uploaded PDF using PyMuPDF."""
    try:
        import fitz
        pdf = fitz.open(stream=file.read(), filetype="pdf")
        text = ""
        for page in pdf:
            text += page.get_text()
        return text.strip()
    except Exception as e:
        return f"[Could not extract PDF text: {e}]"


def extract_text_from_docx(file) -> str:
    try:
        from docx import Document
        import io
        doc = Document(io.BytesIO(file.read()))
        return "\n".join(p.text for p in doc.paragraphs).strip()
    except Exception as e:
        return f"[Could not extract DOCX text: {e}]"


def screen_resume(resume_text: str, job_description: str, candidate_name: str) -> dict:
    """Call Claude to analyse the resume against the JD."""
    client = anthropic.Anthropic()

    prompt = f"""You are an expert technical recruiter. Analyse the resume against the job description and return a JSON object only — no markdown fences, no extra text.

JOB DESCRIPTION:
{job_description}

CANDIDATE NAME: {candidate_name}

RESUME:
{resume_text}

Return this exact JSON schema:
{{
  "overall_score": <0-100 integer>,
  "recommendation": "<Shortlist | Interview | Reject>",
  "summary": "<2-3 sentence executive summary>",
  "strengths": ["<strength1>", "<strength2>", ...],
  "gaps": ["<gap1>", "<gap2>", ...],
  "matched_skills": ["<skill>", ...],
  "missing_skills": ["<skill>", ...],
  "experience_score": <0-100>,
  "skills_score": <0-100>,
  "education_score": <0-100>,
  "culture_fit_score": <0-100>,
  "years_experience": <number or null>,
  "interview_questions": ["<question1>", "<question2>", "<question3>"],
  "red_flags": ["<flag>", ...],
  "positive_signals": ["<signal>", ...]
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    # Strip possible markdown fences
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<h2 style='font-family:Syne;margin-bottom:4px;'>🎯 ResumeAI</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#64748b;font-size:0.75rem;'>Powered by Claude · NLP Screening</p>", unsafe_allow_html=True)
    st.divider()

    st.markdown("**⚙️ Screening Settings**")
    shortlist_threshold = st.slider("Shortlist threshold", 50, 90, 70, 5)
    reject_threshold = st.slider("Reject threshold", 20, 60, 40, 5)
    max_resumes = st.number_input("Max resumes to screen", 1, 20, 10)

    st.divider()
    st.markdown("**📋 How it works**")
    st.markdown("""
<small style='color:#64748b;line-height:1.7;'>
1. Paste the Job Description<br>
2. Upload 1–10 resumes (PDF/DOCX/TXT)<br>
3. Click <b>Screen Resumes</b><br>
4. Get AI-powered rankings & insights
</small>""", unsafe_allow_html=True)


# ── Main UI ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style='padding: 40px 0 20px;'>
  <div class='section-header'>AI · NLP · LLM-Powered</div>
  <h1 style='font-size:2.8rem;margin:0;background:linear-gradient(135deg,#7c3aed,#06b6d4);-webkit-background-clip:text;-webkit-text-fill-color:transparent;'>
    Resume Screener
  </h1>
  <p style='color:#64748b;font-size:0.9rem;margin-top:8px;'>
    Rank candidates instantly · Identify skill gaps · Generate interview questions
  </p>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📥 Screen Resumes", "📊 Results Dashboard", "📝 About"])

# ─────────────────────── TAB 1 — INPUT ──────────────────────────────────────
with tab1:
    col_jd, col_upload = st.columns([1, 1], gap="large")

    with col_jd:
        st.markdown("### Job Description")
        job_desc = st.text_area(
            "Paste the full job description here",
            height=340,
            placeholder="Senior Software Engineer – Python & ML\n\nWe're looking for...\n\nRequired skills:\n- 5+ years Python\n- Machine Learning\n- AWS\n...",
            label_visibility="collapsed",
        )

        # Example JD
        if st.button("Load example JD", use_container_width=True):
            st.session_state["example_jd"] = True
            st.rerun()

        if st.session_state.get("example_jd"):
            job_desc = """Senior Data Scientist – Machine Learning Platform

We are building the next generation ML platform and looking for a seasoned Data Scientist.

Requirements:
• 5+ years experience in data science / ML engineering
• Strong Python skills (pandas, scikit-learn, PyTorch or TensorFlow)
• Experience with MLOps tools (MLflow, Kubeflow, or similar)
• Cloud platforms: AWS or GCP
• SQL and data pipeline experience
• Strong communication and stakeholder management

Nice to have:
• Experience with LLMs / NLP
• Kubernetes / Docker
• Published research or Kaggle achievements

Responsibilities:
• Build and deploy ML models at scale
• Collaborate with product and engineering teams
• Mentor junior data scientists"""

    with col_upload:
        st.markdown("### Upload Resumes")
        uploaded_files = st.file_uploader(
            "Drop PDF, DOCX, or TXT files",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )

        if uploaded_files:
            st.markdown(f"<div style='color:#10b981;font-size:0.85rem;'>✅ {len(uploaded_files)} file(s) ready</div>", unsafe_allow_html=True)
            for f in uploaded_files:
                size_kb = f.size // 1024
                st.markdown(f"<div style='color:#64748b;font-size:0.75rem;padding:2px 0;'>📄 {f.name} · {size_kb} KB</div>", unsafe_allow_html=True)

    st.divider()

    col_btn, col_hint = st.columns([1, 3])
    with col_btn:
        screen_btn = st.button("🚀 Screen Resumes", use_container_width=True)
    with col_hint:
        if not job_desc:
            st.warning("⚠️ Please add a job description first.")
        elif not uploaded_files:
            st.warning("⚠️ Upload at least one resume.")

    # ── Screening Logic ──────────────────────────────────────────────────────
    if screen_btn and job_desc and uploaded_files:
        results = []
        progress = st.progress(0, text="Starting analysis…")
        status = st.empty()

        files_to_process = uploaded_files[:max_resumes]

        for i, f in enumerate(files_to_process):
            status.markdown(f"<div style='color:#7c3aed;font-size:0.85rem;'>🔍 Analysing <b>{f.name}</b>…</div>", unsafe_allow_html=True)

            # Extract text
            name = Path(f.name).stem.replace("_", " ").replace("-", " ").title()
            if f.name.endswith(".pdf"):
                text = extract_text_from_pdf(f)
            elif f.name.endswith(".docx"):
                text = extract_text_from_docx(f)
            else:
                text = f.read().decode("utf-8", errors="ignore")

            try:
                result = screen_resume(text, job_desc, name)
                result["filename"] = f.name
                result["candidate_name"] = name
                results.append(result)
            except Exception as e:
                st.error(f"Error processing {f.name}: {e}")

            progress.progress((i + 1) / len(files_to_process), text=f"Processed {i+1}/{len(files_to_process)}")
            time.sleep(0.3)

        progress.empty()
        status.empty()

        # Sort by score
        results.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
        st.session_state["results"] = results
        st.session_state["job_desc"] = job_desc
        st.success(f"✅ Screened {len(results)} resume(s). Switch to **Results Dashboard** tab.")


# ─────────────────────── TAB 2 — RESULTS ────────────────────────────────────
with tab2:
    results = st.session_state.get("results", [])

    if not results:
        st.markdown("""
        <div style='text-align:center;padding:80px 0;color:#64748b;'>
          <div style='font-size:3rem;'>📊</div>
          <div style='font-family:Syne;font-size:1.2rem;margin-top:12px;'>No results yet</div>
          <div style='font-size:0.85rem;margin-top:6px;'>Screen some resumes in the first tab to see the dashboard here.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # ── Summary metrics ──────────────────────────────────────────────────
        shortlisted = [r for r in results if r.get("overall_score", 0) >= shortlist_threshold]
        rejected = [r for r in results if r.get("overall_score", 0) < reject_threshold]
        avg_score = int(sum(r.get("overall_score", 0) for r in results) / len(results))

        m1, m2, m3, m4 = st.columns(4)
        for col, val, label in [
            (m1, len(results), "Total Screened"),
            (m2, len(shortlisted), "Shortlisted"),
            (m3, len(rejected), "Rejected"),
            (m4, avg_score, "Avg Score"),
        ]:
            with col:
                color = "#7c3aed" if label == "Shortlisted" else ("#ef4444" if label == "Rejected" else "#06b6d4")
                st.markdown(f"""
                <div class='metric-card'>
                  <div class='metric-value' style='color:{color};'>{val}</div>
                  <div class='metric-label'>{label}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Candidate cards ──────────────────────────────────────────────────
        for rank, r in enumerate(results, 1):
            score = r.get("overall_score", 0)
            color = score_color(score)
            badge = score_badge_class(score)
            label = score_label(score)
            rec = r.get("recommendation", "—")

            with st.expander(f"#{rank}  {r.get('candidate_name','Unknown')}  ·  {label}  ·  Score: {score}/100", expanded=(rank == 1)):
                c1, c2 = st.columns([2, 1])

                with c1:
                    # Summary
                    st.markdown(f"<div class='section-header'>Executive Summary</div>", unsafe_allow_html=True)
                    st.markdown(f"<p style='font-size:0.88rem;line-height:1.65;color:#cbd5e1;'>{r.get('summary','—')}</p>", unsafe_allow_html=True)

                    # Dimension scores
                    st.markdown("<div class='section-header' style='margin-top:16px;'>Score Breakdown</div>", unsafe_allow_html=True)
                    dims = [
                        ("Experience", r.get("experience_score", 0)),
                        ("Skills Match", r.get("skills_score", 0)),
                        ("Education", r.get("education_score", 0)),
                        ("Culture Fit", r.get("culture_fit_score", 0)),
                    ]
                    for dim_name, dim_val in dims:
                        dim_color = score_color(dim_val)
                        st.markdown(f"<div style='display:flex;justify-content:space-between;font-size:0.78rem;color:#94a3b8;'><span>{dim_name}</span><span style='color:{dim_color};font-weight:700;'>{dim_val}%</span></div>", unsafe_allow_html=True)
                        st.markdown(gauge_html(dim_val, dim_color), unsafe_allow_html=True)

                    # Skills
                    st.markdown("<div class='section-header' style='margin-top:8px;'>Matched Skills</div>", unsafe_allow_html=True)
                    matched = r.get("matched_skills", [])
                    if matched:
                        tags = " ".join(f"<span class='tag'>{s}</span>" for s in matched)
                        st.markdown(tags, unsafe_allow_html=True)

                    missing = r.get("missing_skills", [])
                    if missing:
                        st.markdown("<div class='section-header' style='margin-top:12px;'>Missing Skills</div>", unsafe_allow_html=True)
                        tags = " ".join(f"<span class='tag tag-missing'>{s}</span>" for s in missing)
                        st.markdown(tags, unsafe_allow_html=True)

                with c2:
                    # Decision badge
                    rec_color = {"Shortlist": "#10b981", "Interview": "#f59e0b", "Reject": "#ef4444"}.get(rec, "#64748b")
                    st.markdown(f"""
                    <div class='metric-card' style='margin-bottom:16px;'>
                      <div class='metric-value' style='color:{color};font-size:3rem;'>{score}</div>
                      <div class='metric-label'>Overall Score</div>
                      <div style='margin-top:10px;'>
                        <span class='score-badge {badge}'>{rec}</span>
                      </div>
                    </div>""", unsafe_allow_html=True)

                    yoe = r.get("years_experience")
                    if yoe is not None:
                        st.markdown(f"<div style='font-size:0.8rem;color:#64748b;text-align:center;margin-bottom:12px;'>⏱ <b style='color:#e2e8f0;'>{yoe} yrs</b> experience</div>", unsafe_allow_html=True)

                    # Strengths
                    strengths = r.get("strengths", [])
                    if strengths:
                        st.markdown("<div class='section-header'>Strengths</div>", unsafe_allow_html=True)
                        for s in strengths[:4]:
                            st.markdown(f"<div style='font-size:0.78rem;color:#86efac;padding:2px 0;'>✓ {s}</div>", unsafe_allow_html=True)

                    # Gaps
                    gaps = r.get("gaps", [])
                    if gaps:
                        st.markdown("<div class='section-header' style='margin-top:10px;'>Gaps</div>", unsafe_allow_html=True)
                        for g in gaps[:3]:
                            st.markdown(f"<div style='font-size:0.78rem;color:#fca5a5;padding:2px 0;'>✗ {g}</div>", unsafe_allow_html=True)

                # Interview Qs
                iqs = r.get("interview_questions", [])
                if iqs:
                    st.markdown("<div class='section-header' style='margin-top:14px;'>Suggested Interview Questions</div>", unsafe_allow_html=True)
                    for q in iqs:
                        st.markdown(f"<div style='font-size:0.82rem;color:#c4b5fd;padding:4px 0;border-left:2px solid #7c3aed;padding-left:10px;margin:4px 0;'>❓ {q}</div>", unsafe_allow_html=True)

                # Red flags / positive signals
                rfl = r.get("red_flags", [])
                pos = r.get("positive_signals", [])
                if rfl or pos:
                    fl1, fl2 = st.columns(2)
                    with fl1:
                        if pos:
                            st.markdown("<div class='section-header' style='margin-top:10px;'>Positive Signals</div>", unsafe_allow_html=True)
                            for p in pos[:3]:
                                st.markdown(f"<div style='font-size:0.78rem;color:#6ee7b7;'>⚡ {p}</div>", unsafe_allow_html=True)
                    with fl2:
                        if rfl:
                            st.markdown("<div class='section-header' style='margin-top:10px;'>Red Flags</div>", unsafe_allow_html=True)
                            for rf in rfl[:3]:
                                st.markdown(f"<div style='font-size:0.78rem;color:#fca5a5;'>⚠ {rf}</div>", unsafe_allow_html=True)

        # ── Export ───────────────────────────────────────────────────────────
        st.divider()
        export_data = json.dumps(results, indent=2)
        st.download_button("⬇️  Export Results as JSON", export_data, "screening_results.json", "application/json")


# ─────────────────────── TAB 3 — ABOUT ──────────────────────────────────────
with tab3:
    st.markdown("""
    ## About This Project

    **AI Resume Screener** is an open-source project that demonstrates how to combine:

    | Technology | Role |
    |---|---|
    | **Streamlit** | Web interface |
    | **Anthropic Claude** | LLM reasoning engine |
    | **PyMuPDF / python-docx** | Document parsing |
    | **Python** | Orchestration & NLP |

    ### Architecture
    ```
    User → Streamlit UI
              ↓
          Resume Parser (PDF/DOCX/TXT)
              ↓
          Claude API (claude-sonnet)
              ↓ structured JSON
          Scoring Engine
              ↓
          Dashboard & Export
    ```

    ### Key Features
    - 📄 **Multi-format support** — PDF, DOCX, TXT
    - 🤖 **LLM-powered analysis** — Claude evaluates context, not just keywords
    - 📊 **Multi-dimensional scoring** — Experience, Skills, Education, Culture Fit
    - 💬 **Interview question generation** — Auto-generated per candidate
    - 🚩 **Red flag detection** — Identifies risks and inconsistencies
    - 📤 **JSON export** — Integrate with your ATS

    ### GitHub & Article
    - 🔗 [GitHub Repository](https://github.com/your-username/ai-resume-screener)
    - 📝 [Read the Medium Article](https://medium.com/@your-username/ai-resume-screener)

    ### Environment Setup
    ```bash
    pip install streamlit anthropic pymupdf python-docx
    export ANTHROPIC_API_KEY=your_key_here
    streamlit run app.py
    ```
    """)
