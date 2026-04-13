import streamlit as st
import anthropic
import json
import re
from pathlib import Path
import time

# ── Page config ───────────────────────────────────────────────────────────────
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

[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border);
}

/* Step card */
.step-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 24px;
    position: relative;
}
.step-label {
    position: absolute;
    top: -12px; left: 24px;
    background: linear-gradient(135deg, #7c3aed, #5b21b6);
    color: white;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 0.7rem;
    letter-spacing: 2px;
    padding: 4px 14px;
    border-radius: 999px;
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

.result-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 28px;
    margin-bottom: 20px;
}
.result-card:hover { border-color: var(--accent); }

.section-header {
    font-family: 'Syne', sans-serif;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--accent2);
    margin-bottom: 8px;
}

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

.gauge-wrap { background: #1e1e2e; border-radius: 8px; height: 8px; overflow: hidden; margin: 6px 0 14px; }
.gauge-fill  { height: 100%; border-radius: 8px; }

/* Eligibility banner */
.eligible-yes {
    background: rgba(16,185,129,0.12);
    border: 1px solid rgba(16,185,129,0.35);
    border-radius: 12px;
    padding: 16px 22px;
    color: #6ee7b7;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 1rem;
    margin-bottom: 12px;
}
.eligible-no {
    background: rgba(239,68,68,0.1);
    border: 1px solid rgba(239,68,68,0.3);
    border-radius: 12px;
    padding: 16px 22px;
    color: #fca5a5;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 1rem;
    margin-bottom: 12px;
}

/* Info pill */
.info-pill {
    display: inline-block;
    background: rgba(6,182,212,0.1);
    color: #67e8f9;
    border: 1px solid rgba(6,182,212,0.25);
    border-radius: 8px;
    padding: 4px 12px;
    font-size: 0.78rem;
    margin: 3px 3px;
}

[data-testid="stFileUploader"] {
    background: var(--surface) !important;
    border: 2px dashed var(--border) !important;
    border-radius: 12px !important;
}

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

.stTextArea textarea, .stTextInput input, .stNumberInput input, .stSelectbox select {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 10px !important;
    font-family: 'Space Mono', monospace !important;
}
hr { border-color: var(--border) !important; }
#MainMenu, header, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def score_color(score):
    if score >= 75: return "#10b981"
    if score >= 50: return "#f59e0b"
    return "#ef4444"

def score_badge_class(score):
    if score >= 75: return "badge-high"
    if score >= 50: return "badge-medium"
    return "badge-low"

def score_label(score):
    if score >= 80: return "🟢 Strong Match"
    if score >= 65: return "🟡 Good Match"
    if score >= 50: return "🟠 Moderate Match"
    return "🔴 Weak Match"

def gauge_html(value, color):
    return f"""<div class="gauge-wrap"><div class="gauge-fill" style="width:{value}%;background:{color};"></div></div>"""

def extract_text_from_pdf(file):
    try:
        import fitz
        pdf = fitz.open(stream=file.read(), filetype="pdf")
        return "".join(page.get_text() for page in pdf).strip()
    except Exception as e:
        return f"[PDF parse error: {e}]"

def extract_text_from_docx(file):
    try:
        from docx import Document
        import io
        doc = Document(io.BytesIO(file.read()))
        return "\n".join(p.text for p in doc.paragraphs).strip()
    except Exception as e:
        return f"[DOCX parse error: {e}]"

def pct_color(pct):
    if pct >= 75: return "#10b981"
    if pct >= 60: return "#f59e0b"
    return "#ef4444"


def screen_resume(resume_text, job_description, candidate_info, api_key):
    """Send resume + candidate profile to Claude and get structured JSON back."""
    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""You are a senior technical recruiter and eligibility assessor.

You will be given:
1. A job description
2. A candidate's personal profile (name, address, academic scores)
3. The candidate's resume text

Your job is to:
- Check academic eligibility based on the school and college percentages provided
- Evaluate the resume against the job description
- Return a single JSON object only — no markdown, no extra text

CANDIDATE PROFILE:
Name:              {candidate_info['name']}
Address:           {candidate_info['address']}
School Name:       {candidate_info['school_name']}
School Percentage: {candidate_info['school_pct']}%
College Name:      {candidate_info['college_name']}
College Percentage:{candidate_info['college_pct']}%

JOB DESCRIPTION:
{job_description}

RESUME:
{resume_text}

Return this exact JSON:
{{
  "eligible": <true | false>,
  "eligibility_reason": "<one sentence explaining eligibility decision>",
  "overall_score": <0-100 integer>,
  "recommendation": "<Shortlist | Interview | Reject>",
  "summary": "<2-3 sentence executive summary>",
  "strengths": ["<s1>", "<s2>", "<s3>"],
  "gaps": ["<g1>", "<g2>"],
  "matched_skills": ["<skill>", ...],
  "missing_skills": ["<skill>", ...],
  "experience_score": <0-100>,
  "skills_score": <0-100>,
  "education_score": <0-100>,
  "culture_fit_score": <0-100>,
  "years_experience": <number or null>,
  "interview_questions": ["<q1>", "<q2>", "<q3>"],
  "red_flags": ["<flag>", ...],
  "positive_signals": ["<signal>", ...]
}}"""

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<h2 style='font-family:Syne;margin-bottom:4px;'>🎯 ResumeAI</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#64748b;font-size:0.75rem;'>Powered by Claude · NLP Screening</p>", unsafe_allow_html=True)
    st.divider()

    st.markdown("**🔑 Anthropic API Key**")
    api_key = st.text_input(
        "API Key", type="password", placeholder="sk-ant-...",
        label_visibility="collapsed",
    )
    if api_key:
        st.markdown("<div style='color:#10b981;font-size:0.75rem;'>✅ Key set</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='color:#f59e0b;font-size:0.75rem;'>⚠️ Required to screen</div>", unsafe_allow_html=True)
    st.markdown("<a href='https://console.anthropic.com' target='_blank' style='color:#7c3aed;font-size:0.72rem;'>Get a free API key →</a>", unsafe_allow_html=True)

    st.divider()
    st.markdown("**⚙️ Settings**")
    shortlist_threshold = st.slider("Shortlist threshold", 50, 90, 70, 5)
    reject_threshold    = st.slider("Reject threshold",    20, 60, 40, 5)
    min_school_pct      = st.slider("Min school % required",  40, 90, 60, 5)
    min_college_pct     = st.slider("Min college % required", 40, 90, 55, 5)

    st.divider()
    st.markdown("""
<small style='color:#64748b;line-height:1.8;'>
<b>How it works</b><br>
① Enter API key<br>
② Fill candidate details<br>
③ Paste Job Description<br>
④ Upload Resume<br>
⑤ Get eligibility + AI score
</small>""", unsafe_allow_html=True)


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='padding:40px 0 20px;'>
  <div class='section-header'>AI · NLP · LLM-Powered</div>
  <h1 style='font-size:2.8rem;margin:0;background:linear-gradient(135deg,#7c3aed,#06b6d4);
     -webkit-background-clip:text;-webkit-text-fill-color:transparent;'>
    Resume Screener
  </h1>
  <p style='color:#64748b;font-size:0.9rem;margin-top:8px;'>
    Fill candidate details → upload resume → get instant eligibility + AI match score
  </p>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📋 Candidate Form", "📊 Results Dashboard", "📝 About"])


# ═══════════════════════ TAB 1 — CANDIDATE FORM ══════════════════════════════
with tab1:

    # ── STEP 1 · Personal Details ─────────────────────────────────────────────
    st.markdown("""
    <div class='step-card'>
      <div class='step-label'>STEP 1 · PERSONAL DETAILS</div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        cand_name    = st.text_input("Full Name *", placeholder="e.g. Priya Sharma")
    with c2:
        cand_address = st.text_input("Address *", placeholder="e.g. 12 MG Road, Ludhiana, Punjab")

    st.markdown("</div>", unsafe_allow_html=True)

    # ── STEP 2 · Academic Details ─────────────────────────────────────────────
    st.markdown("""
    <div class='step-card'>
      <div class='step-label'>STEP 2 · ACADEMIC DETAILS</div>
    """, unsafe_allow_html=True)

    sc1, sc2, sc3, sc4 = st.columns([2, 1, 2, 1])
    with sc1:
        school_name = st.text_input("School / 10th Board Name *", placeholder="e.g. DAV Public School")
    with sc2:
        school_pct  = st.number_input("School % *", min_value=0.0, max_value=100.0,
                                       value=0.0, step=0.1, format="%.1f")
    with sc3:
        college_name = st.text_input("College / University Name *", placeholder="e.g. Punjab Engineering College")
    with sc4:
        college_pct  = st.number_input("College % *", min_value=0.0, max_value=100.0,
                                        value=0.0, step=0.1, format="%.1f")

    # Live eligibility preview
    if school_pct > 0 and college_pct > 0:
        school_ok  = school_pct  >= min_school_pct
        college_ok = college_pct >= min_college_pct
        if school_ok and college_ok:
            st.markdown(f"""
            <div class='eligible-yes'>
              ✅ Academic criteria met — School {school_pct}% ≥ {min_school_pct}%
              &nbsp;&nbsp;|&nbsp;&nbsp; College {college_pct}% ≥ {min_college_pct}%
            </div>""", unsafe_allow_html=True)
        else:
            reasons = []
            if not school_ok:  reasons.append(f"School {school_pct}% < {min_school_pct}% required")
            if not college_ok: reasons.append(f"College {college_pct}% < {min_college_pct}% required")
            st.markdown(f"""
            <div class='eligible-no'>
              ❌ Below academic threshold — {' · '.join(reasons)}
            </div>""", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ── STEP 3 · Job Description ──────────────────────────────────────────────
    st.markdown("""
    <div class='step-card'>
      <div class='step-label'>STEP 3 · JOB DESCRIPTION</div>
    """, unsafe_allow_html=True)

    job_desc = st.text_area(
        "Paste the full job description",
        height=220,
        placeholder="e.g. Senior Data Scientist – Python, ML, AWS\n\nRequirements:\n• 5+ years experience\n• PyTorch / TensorFlow\n• MLOps tools\n...",
        label_visibility="collapsed",
    )

    if st.button("Load example JD", use_container_width=False):
        st.session_state["example_jd"] = True
        st.rerun()

    if st.session_state.get("example_jd"):
        job_desc = """Senior Data Scientist – Machine Learning Platform

Requirements:
• 5+ years in data science / ML engineering
• Strong Python (pandas, scikit-learn, PyTorch or TensorFlow)
• MLOps tools (MLflow, Kubeflow, or similar)
• Cloud: AWS or GCP
• SQL and data pipelines
• Strong communication skills

Nice to have:
• LLMs / NLP experience
• Kubernetes / Docker
• Published research or Kaggle achievements

Responsibilities:
• Build and deploy ML models at scale
• Collaborate with product and engineering teams
• Mentor junior data scientists"""

    st.markdown("</div>", unsafe_allow_html=True)

    # ── STEP 4 · Resume Upload ────────────────────────────────────────────────
    st.markdown("""
    <div class='step-card'>
      <div class='step-label'>STEP 4 · UPLOAD RESUME</div>
    """, unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Drop PDF, DOCX, or TXT resume(s)",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded_files:
        for f in uploaded_files:
            st.markdown(f"<div style='color:#10b981;font-size:0.8rem;'>📄 {f.name} · {f.size//1024} KB</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Submit button ─────────────────────────────────────────────────────────
    col_btn, col_warn = st.columns([1, 3])
    with col_btn:
        screen_btn = st.button("🚀 Screen Candidate", use_container_width=True)
    with col_warn:
        missing = []
        if not api_key:       missing.append("API key")
        if not cand_name:     missing.append("candidate name")
        if not cand_address:  missing.append("address")
        if not school_name:   missing.append("school name")
        if school_pct == 0:   missing.append("school %")
        if not college_name:  missing.append("college name")
        if college_pct == 0:  missing.append("college %")
        if not job_desc:      missing.append("job description")
        if not uploaded_files:missing.append("resume file")

        if missing:
            st.warning(f"⚠️ Please fill in: {', '.join(missing)}")

    # ── Screening logic ───────────────────────────────────────────────────────
    if screen_btn and not missing:
        candidate_info = {
            "name":        cand_name,
            "address":     cand_address,
            "school_name": school_name,
            "school_pct":  school_pct,
            "college_name":college_name,
            "college_pct": college_pct,
        }

        results = []
        progress = st.progress(0, text="Starting AI analysis…")
        status   = st.empty()

        for i, f in enumerate(uploaded_files):
            status.markdown(f"<div style='color:#7c3aed;font-size:0.85rem;'>🔍 Analysing <b>{f.name}</b>…</div>", unsafe_allow_html=True)

            if f.name.endswith(".pdf"):
                text = extract_text_from_pdf(f)
            elif f.name.endswith(".docx"):
                text = extract_text_from_docx(f)
            else:
                text = f.read().decode("utf-8", errors="ignore")

            try:
                result = screen_resume(text, job_desc, candidate_info, api_key)
                result["filename"]       = f.name
                result["candidate_name"] = cand_name
                result["address"]        = cand_address
                result["school_name"]    = school_name
                result["school_pct"]     = school_pct
                result["college_name"]   = college_name
                result["college_pct"]    = college_pct
                results.append(result)
            except Exception as e:
                st.error(f"Error processing {f.name}: {e}")

            progress.progress((i + 1) / len(uploaded_files))
            time.sleep(0.2)

        progress.empty()
        status.empty()

        results.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
        st.session_state["results"] = results
        st.success("✅ Analysis complete! Switch to the **Results Dashboard** tab.")


# ═══════════════════════ TAB 2 — RESULTS ═════════════════════════════════════
with tab2:
    results = st.session_state.get("results", [])

    if not results:
        st.markdown("""
        <div style='text-align:center;padding:80px 0;color:#64748b;'>
          <div style='font-size:3rem;'>📊</div>
          <div style='font-family:Syne;font-size:1.2rem;margin-top:12px;'>No results yet</div>
          <div style='font-size:0.85rem;margin-top:6px;'>
            Fill the candidate form and screen a resume to see results here.
          </div>
        </div>""", unsafe_allow_html=True)
    else:
        shortlisted = [r for r in results if r.get("overall_score", 0) >= shortlist_threshold]
        rejected    = [r for r in results if r.get("overall_score", 0) <  reject_threshold]
        avg_score   = int(sum(r.get("overall_score", 0) for r in results) / len(results))

        m1, m2, m3, m4 = st.columns(4)
        for col, val, label, color in [
            (m1, len(results),    "Total Screened", "#06b6d4"),
            (m2, len(shortlisted),"Shortlisted",    "#7c3aed"),
            (m3, len(rejected),   "Rejected",       "#ef4444"),
            (m4, avg_score,       "Avg Score",      "#10b981"),
        ]:
            with col:
                st.markdown(f"""
                <div class='metric-card'>
                  <div class='metric-value' style='color:{color};'>{val}</div>
                  <div class='metric-label'>{label}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        for rank, r in enumerate(results, 1):
            score  = r.get("overall_score", 0)
            color  = score_color(score)
            badge  = score_badge_class(score)
            label  = score_label(score)
            rec    = r.get("recommendation", "—")
            eligible = r.get("eligible", True)

            header = f"#{rank}  {r.get('candidate_name','—')}  ·  {label}  ·  Score: {score}/100"
            with st.expander(header, expanded=(rank == 1)):

                # ── Eligibility banner ────────────────────────────────────────
                if eligible:
                    st.markdown(f"""
                    <div class='eligible-yes'>
                      ✅ ELIGIBLE — {r.get('eligibility_reason','Meets all academic criteria')}
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class='eligible-no'>
                      ❌ NOT ELIGIBLE — {r.get('eligibility_reason','Does not meet academic criteria')}
                    </div>""", unsafe_allow_html=True)

                # ── Candidate info pills ──────────────────────────────────────
                st.markdown(f"""
                <div style='margin-bottom:16px;'>
                  <span class='info-pill'>📍 {r.get('address','—')}</span>
                  <span class='info-pill'>🏫 {r.get('school_name','—')} · {r.get('school_pct',0)}%</span>
                  <span class='info-pill'>🎓 {r.get('college_name','—')} · {r.get('college_pct',0)}%</span>
                </div>""", unsafe_allow_html=True)

                c1, c2 = st.columns([2, 1])

                with c1:
                    st.markdown("<div class='section-header'>Executive Summary</div>", unsafe_allow_html=True)
                    st.markdown(f"<p style='font-size:0.88rem;line-height:1.65;color:#cbd5e1;'>{r.get('summary','—')}</p>", unsafe_allow_html=True)

                    st.markdown("<div class='section-header' style='margin-top:16px;'>Score Breakdown</div>", unsafe_allow_html=True)
                    for dim, key in [("Experience","experience_score"),("Skills Match","skills_score"),
                                     ("Education","education_score"),("Culture Fit","culture_fit_score")]:
                        val = r.get(key, 0)
                        c = score_color(val)
                        st.markdown(f"<div style='display:flex;justify-content:space-between;font-size:0.78rem;color:#94a3b8;'><span>{dim}</span><span style='color:{c};font-weight:700;'>{val}%</span></div>", unsafe_allow_html=True)
                        st.markdown(gauge_html(val, c), unsafe_allow_html=True)

                    matched = r.get("matched_skills", [])
                    if matched:
                        st.markdown("<div class='section-header' style='margin-top:8px;'>Matched Skills</div>", unsafe_allow_html=True)
                        st.markdown(" ".join(f"<span class='tag'>{s}</span>" for s in matched), unsafe_allow_html=True)

                    missing_s = r.get("missing_skills", [])
                    if missing_s:
                        st.markdown("<div class='section-header' style='margin-top:12px;'>Missing Skills</div>", unsafe_allow_html=True)
                        st.markdown(" ".join(f"<span class='tag tag-missing'>{s}</span>" for s in missing_s), unsafe_allow_html=True)

                with c2:
                    rec_color = {"Shortlist":"#10b981","Interview":"#f59e0b","Reject":"#ef4444"}.get(rec,"#64748b")
                    st.markdown(f"""
                    <div class='metric-card' style='margin-bottom:16px;'>
                      <div class='metric-value' style='color:{color};font-size:3rem;'>{score}</div>
                      <div class='metric-label'>Overall Score</div>
                      <div style='margin-top:10px;'>
                        <span class='score-badge {badge}'>{rec}</span>
                      </div>
                    </div>""", unsafe_allow_html=True)

                    yoe = r.get("years_experience")
                    if yoe:
                        st.markdown(f"<div style='font-size:0.8rem;color:#64748b;text-align:center;margin-bottom:12px;'>⏱ <b style='color:#e2e8f0;'>{yoe} yrs</b> experience</div>", unsafe_allow_html=True)

                    strengths = r.get("strengths", [])
                    if strengths:
                        st.markdown("<div class='section-header'>Strengths</div>", unsafe_allow_html=True)
                        for s in strengths[:4]:
                            st.markdown(f"<div style='font-size:0.78rem;color:#86efac;padding:2px 0;'>✓ {s}</div>", unsafe_allow_html=True)

                    gaps = r.get("gaps", [])
                    if gaps:
                        st.markdown("<div class='section-header' style='margin-top:10px;'>Gaps</div>", unsafe_allow_html=True)
                        for g in gaps[:3]:
                            st.markdown(f"<div style='font-size:0.78rem;color:#fca5a5;padding:2px 0;'>✗ {g}</div>", unsafe_allow_html=True)

                iqs = r.get("interview_questions", [])
                if iqs:
                    st.markdown("<div class='section-header' style='margin-top:14px;'>Interview Questions</div>", unsafe_allow_html=True)
                    for q in iqs:
                        st.markdown(f"<div style='font-size:0.82rem;color:#c4b5fd;padding:4px 0;border-left:2px solid #7c3aed;padding-left:10px;margin:4px 0;'>❓ {q}</div>", unsafe_allow_html=True)

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

        st.divider()
        st.download_button("⬇️ Export Results as JSON",
                           json.dumps(results, indent=2),
                           "screening_results.json", "application/json")


# ═══════════════════════ TAB 3 — ABOUT ═══════════════════════════════════════
with tab3:
    st.markdown("""
## About This Project

**AI Resume Screener** combines a structured candidate intake form with LLM-powered resume analysis.

| Technology | Role |
|---|---|
| **Streamlit** | Web interface & form |
| **Anthropic Claude** | Reasoning & eligibility engine |
| **PyMuPDF** | PDF text extraction |
| **python-docx** | DOCX text extraction |

### Screening Flow
```
Step 1 → Personal Details  (name, address)
Step 2 → Academic Details  (school %, college %)
Step 3 → Job Description   (paste or load example)
Step 4 → Resume Upload     (PDF / DOCX / TXT)
           ↓
     Claude API Analysis
           ↓
     Eligibility Check + AI Score + Dashboard
```

### Setup
```bash
pip install streamlit anthropic pymupdf python-docx
export ANTHROPIC_API_KEY=sk-ant-...
streamlit run app.py
```
""")
