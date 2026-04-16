import streamlit as st
import anthropic
import json
import re
from pathlib import Path
import time

st.set_page_config(page_title="AI Resume Screener", page_icon="🎯", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Space+Mono:wght@400;700&display=swap');
:root{--bg:#0a0a0f;--surface:#13131a;--border:#1e1e2e;--accent:#7c3aed;--accent2:#06b6d4;--text:#e2e8f0;--muted:#64748b;}
html,body,[class*="css"]{font-family:'Space Mono',monospace;background:var(--bg);color:var(--text);}
.stApp{background:var(--bg);}
h1,h2,h3{font-family:'Syne',sans-serif;font-weight:800;}
[data-testid="stSidebar"]{background:var(--surface)!important;border-right:1px solid var(--border);}
.step-box{background:var(--surface);border:1px solid var(--border);border-left:4px solid var(--accent);border-radius:10px;padding:14px 20px;margin-bottom:18px;}
.step-num{font-family:'Syne';font-size:0.62rem;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:var(--accent2);}
.step-name{font-family:'Syne';font-size:1.05rem;font-weight:800;margin:2px 0 0;color:var(--text);}
.metric-card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px;text-align:center;position:relative;overflow:hidden;}
.metric-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--accent),var(--accent2));}
.metric-value{font-size:2.4rem;font-weight:800;font-family:'Syne',sans-serif;}
.metric-label{font-size:0.7rem;color:var(--muted);text-transform:uppercase;letter-spacing:2px;}
.score-badge{display:inline-block;padding:6px 16px;border-radius:999px;font-weight:700;font-size:0.82rem;font-family:'Syne',sans-serif;}
.badge-high{background:rgba(16,185,129,.15);color:#10b981;border:1px solid rgba(16,185,129,.3);}
.badge-medium{background:rgba(245,158,11,.15);color:#f59e0b;border:1px solid rgba(245,158,11,.3);}
.badge-low{background:rgba(239,68,68,.15);color:#ef4444;border:1px solid rgba(239,68,68,.3);}
.section-header{font-family:'Syne';font-size:0.62rem;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:var(--accent2);margin-bottom:8px;}
.tag{display:inline-block;background:rgba(124,58,237,.12);color:#a78bfa;border:1px solid rgba(124,58,237,.25);border-radius:6px;padding:2px 10px;font-size:0.75rem;margin:2px;}
.tag-missing{background:rgba(239,68,68,.1);color:#f87171;border-color:rgba(239,68,68,.25);}
.profile-card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:16px 20px;margin-bottom:16px;}
.prow{display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid var(--border);font-size:0.82rem;}
.prow:last-child{border-bottom:none;}
.pkey{color:var(--muted);}
.pval{color:var(--text);font-weight:700;}
.pct-pass{color:#10b981;} .pct-warn{color:#f59e0b;} .pct-fail{color:#ef4444;}
.gauge-wrap{background:#1e1e2e;border-radius:8px;height:8px;overflow:hidden;margin:5px 0 13px;}
.gauge-fill{height:100%;border-radius:8px;}
[data-testid="stFileUploader"]{background:var(--surface)!important;border:2px dashed var(--border)!important;border-radius:12px!important;}
.stButton>button{background:linear-gradient(135deg,var(--accent),#5b21b6)!important;color:white!important;border:none!important;border-radius:10px!important;font-family:'Syne',sans-serif!important;font-weight:700!important;letter-spacing:1px!important;padding:12px 28px!important;transition:all .2s!important;}
.stButton>button:hover{transform:translateY(-1px)!important;box-shadow:0 8px 25px rgba(124,58,237,.4)!important;}
.stTextArea textarea,.stTextInput input,.stNumberInput input{background:var(--surface)!important;border:1px solid var(--border)!important;color:var(--text)!important;border-radius:10px!important;font-family:'Space Mono',monospace!important;}
hr{border-color:var(--border)!important;}
#MainMenu,header,footer{visibility:hidden;}
</style>
""", unsafe_allow_html=True)

def score_color(s): return "#10b981" if s>=75 else ("#f59e0b" if s>=50 else "#ef4444")
def badge_class(s): return "badge-high" if s>=75 else ("badge-medium" if s>=50 else "badge-low")
def score_label(s):
    if s>=80: return "🟢 Strong Match"
    if s>=65: return "🟡 Good Match"
    if s>=50: return "🟠 Moderate Match"
    return "🔴 Weak Match"
def pct_cls(p): return "pct-pass" if p>=70 else ("pct-warn" if p>=50 else "pct-fail")
def gauge(val,color): return f'<div class="gauge-wrap"><div class="gauge-fill" style="width:{val}%;background:{color};"></div></div>'

def read_pdf(f):
    try:
        import fitz
        pdf=fitz.open(stream=f.read(),filetype="pdf")
        return "".join(p.get_text() for p in pdf).strip()
    except Exception as e: return f"[PDF error: {e}]"

def read_docx(f):
    try:
        from docx import Document
        import io
        return "\n".join(p.text for p in Document(io.BytesIO(f.read())).paragraphs).strip()
    except Exception as e: return f"[DOCX error: {e}]"

def screen_resume(resume_text, job_desc, profile, api_key):
    client = anthropic.Anthropic(api_key=api_key)
    prompt = f"""You are a senior HR recruiter. Evaluate this candidate's eligibility for the job using their academic profile AND resume.

=== CANDIDATE PROFILE ===
Name: {profile['name']}
Address: {profile['address']}
School: {profile['school_name']} | Score: {profile['school_pct']}%
College: {profile['college_name']} | Score: {profile['college_pct']}%

=== JOB DESCRIPTION ===
{job_desc}

=== RESUME ===
{resume_text}

Return ONLY valid JSON, no markdown fences:
{{
  "overall_score": <0-100>,
  "eligible": <true|false>,
  "recommendation": "<Shortlist|Interview|Reject>",
  "eligibility_reason": "<1-2 sentences why eligible or not, referencing academics + experience>",
  "academic_assessment": "<1-2 sentences assessing school/college scores for this role>",
  "summary": "<2-3 sentence executive summary>",
  "strengths": ["...", "...", "..."],
  "gaps": ["...", "..."],
  "matched_skills": ["..."],
  "missing_skills": ["..."],
  "experience_score": <0-100>,
  "skills_score": <0-100>,
  "education_score": <0-100>,
  "culture_fit_score": <0-100>,
  "years_experience": <number|null>,
  "interview_questions": ["...", "...", "..."],
  "red_flags": ["..."],
  "positive_signals": ["..."]
}}"""
    msg = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=1800,
                                  messages=[{"role":"user","content":prompt}])
    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```[a-z]*\n?","",raw); raw = re.sub(r"\n?```$","",raw)
    return json.loads(raw)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<h2 style='font-family:Syne;margin-bottom:4px;'>🎯 ResumeAI</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#64748b;font-size:0.75rem;'>Powered by Claude · Eligibility Screener</p>", unsafe_allow_html=True)
    st.divider()
    st.markdown("**🔑 Anthropic API Key**")
    api_key = st.text_input("API Key", type="password", placeholder="sk-ant-...", label_visibility="collapsed")
    if api_key:
        st.markdown("<div style='color:#10b981;font-size:0.75rem;'>✅ Key set</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='color:#f59e0b;font-size:0.75rem;'>⚠️ Required to screen</div>", unsafe_allow_html=True)
    st.markdown("<a href='https://console.anthropic.com' target='_blank' style='color:#7c3aed;font-size:0.72rem;'>Get a free API key →</a>", unsafe_allow_html=True)
    st.divider()
    st.markdown("**⚙️ Thresholds**")
    shortlist_threshold = st.slider("Shortlist above", 50, 90, 70, 5)
    reject_threshold    = st.slider("Reject below",    20, 60, 40, 5)
    max_resumes         = st.number_input("Max resumes", 1, 20, 10)
    st.divider()
    st.markdown("""<small style='color:#64748b;line-height:1.9;'>① Fill candidate profile<br>② Paste job description<br>③ Upload resume(s)<br>④ Click <b>Check Eligibility</b></small>""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='padding:32px 0 14px;'>
  <div style='font-family:Syne;font-size:0.62rem;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:#06b6d4;'>AI · NLP · LLM-Powered</div>
  <h1 style='font-size:2.6rem;margin:4px 0;background:linear-gradient(135deg,#7c3aed,#06b6d4);-webkit-background-clip:text;-webkit-text-fill-color:transparent;'>Resume Screener</h1>
  <p style='color:#64748b;font-size:0.86rem;margin:0;'>Fill candidate profile → upload resume → get instant eligibility verdict</p>
</div>""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📋 Candidate & Screening", "📊 Results Dashboard", "📝 About"])

# ═══════════════════════ TAB 1 ═══════════════════════════════════════════════
with tab1:
    st.markdown("<div class='step-box'><div class='step-num'>Step 1 of 3</div><div class='step-name'>👤 Candidate Personal & Academic Details</div></div>", unsafe_allow_html=True)

    col_a, col_b = st.columns(2, gap="large")
    with col_a:
        st.markdown("**Personal Information**")
        cand_name    = st.text_input("Full Name *", placeholder="e.g. Priya Sharma")
        cand_address = st.text_area("Full Address *", placeholder="e.g. 123 MG Road, Ludhiana, Punjab – 141001", height=100)

    with col_b:
        st.markdown("**Academic Record**")
        school_name  = st.text_input("School Name *", placeholder="e.g. DAV Public School, Ludhiana")
        school_pct   = st.number_input("School Percentage / CGPA *", min_value=0.0, max_value=100.0, value=0.0, step=0.1, format="%.1f")
        college_name = st.text_input("College / University Name *", placeholder="e.g. PEC University of Technology")
        college_pct  = st.number_input("College Percentage / CGPA *", min_value=0.0, max_value=100.0, value=0.0, step=0.1, format="%.1f")

    profile_ok = all([cand_name.strip(), cand_address.strip(), school_name.strip(), school_pct>0, college_name.strip(), college_pct>0])

    if profile_ok:
        st.markdown("<div style='color:#10b981;font-size:0.82rem;margin:4px 0 8px;'>✅ Profile complete — preview below</div>", unsafe_allow_html=True)
        st.markdown(f"""<div class='profile-card'>
          <div style='font-family:Syne;font-size:0.62rem;letter-spacing:2px;text-transform:uppercase;color:#06b6d4;margin-bottom:10px;'>Profile Preview</div>
          <div class='prow'><span class='pkey'>Name</span><span class='pval'>{cand_name}</span></div>
          <div class='prow'><span class='pkey'>Address</span><span class='pval'>{cand_address}</span></div>
          <div class='prow'><span class='pkey'>School</span><span class='pval'>{school_name} &nbsp;<span class='{pct_cls(school_pct)}'>{school_pct}%</span></span></div>
          <div class='prow'><span class='pkey'>College</span><span class='pval'>{college_name} &nbsp;<span class='{pct_cls(college_pct)}'>{college_pct}%</span></span></div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("<div style='color:#f59e0b;font-size:0.8rem;margin:6px 0;'>⚠️ Fill all fields above to proceed</div>", unsafe_allow_html=True)

    st.divider()
    st.markdown("<div class='step-box'><div class='step-num'>Step 2 of 3</div><div class='step-name'>📄 Job Description</div></div>", unsafe_allow_html=True)

    col_jd, col_ex = st.columns([3,1], gap="large")
    with col_jd:
        job_desc = st.text_area("Job Description", height=220, placeholder="Paste the full job description here…", label_visibility="collapsed")
    with col_ex:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📋 Load Example JD", use_container_width=True):
            st.session_state["example_jd"] = True
            st.rerun()

    if st.session_state.get("example_jd"):
        job_desc = """Senior Data Scientist – Machine Learning Platform
Requirements:
• 4+ years Python (pandas, scikit-learn, PyTorch/TensorFlow)
• MLOps: MLflow, Kubeflow • Cloud: AWS or GCP • SQL
• 60%+ college marks preferred
Nice to have: LLMs/NLP, Docker/Kubernetes
Responsibilities: Build & deploy ML models, mentor junior scientists"""

    st.divider()
    st.markdown("<div class='step-box'><div class='step-num'>Step 3 of 3</div><div class='step-name'>📁 Upload Resume(s)</div></div>", unsafe_allow_html=True)

    uploaded_files = st.file_uploader("Drop PDF, DOCX, or TXT files", type=["pdf","docx","txt"], accept_multiple_files=True, label_visibility="collapsed")
    if uploaded_files:
        for f in uploaded_files:
            kb = max(1, f.size//1024)
            st.markdown(f"<div style='color:#94a3b8;font-size:0.78rem;padding:3px 0;'>📄 {f.name} · {kb} KB</div>", unsafe_allow_html=True)

    st.divider()
    col_btn, col_warn = st.columns([1,3])
    with col_btn:
        screen_btn = st.button("🚀 Check Eligibility", use_container_width=True)
    with col_warn:
        if not api_key:          st.warning("⚠️ Add your Anthropic API key in the sidebar.")
        elif not profile_ok:     st.warning("⚠️ Complete Step 1 — candidate details missing.")
        elif not job_desc:       st.warning("⚠️ Paste a job description in Step 2.")
        elif not uploaded_files: st.warning("⚠️ Upload at least one resume in Step 3.")

    if screen_btn and api_key and profile_ok and job_desc and uploaded_files:
        profile = {"name":cand_name,"address":cand_address,"school_name":school_name,
                   "school_pct":school_pct,"college_name":college_name,"college_pct":college_pct}
        results  = []
        progress = st.progress(0, text="Starting eligibility check…")
        status   = st.empty()
        batch    = uploaded_files[:max_resumes]
        for i,f in enumerate(batch):
            status.markdown(f"<div style='color:#7c3aed;font-size:0.85rem;'>🔍 Analysing <b>{f.name}</b>…</div>", unsafe_allow_html=True)
            if f.name.endswith(".pdf"):    text = read_pdf(f)
            elif f.name.endswith(".docx"): text = read_docx(f)
            else:                           text = f.read().decode("utf-8",errors="ignore")
            try:
                r = screen_resume(text, job_desc, profile, api_key)
                r.update({"filename":f.name,"candidate_name":cand_name,"address":cand_address,
                           "school_name":school_name,"school_pct":school_pct,
                           "college_name":college_name,"college_pct":college_pct})
                results.append(r)
            except Exception as e:
                st.error(f"Error processing {f.name}: {e}")
            progress.progress((i+1)/len(batch), text=f"Processed {i+1}/{len(batch)}")
            time.sleep(0.3)
        progress.empty(); status.empty()
        results.sort(key=lambda x:x.get("overall_score",0), reverse=True)
        st.session_state["results"] = results
        en = sum(1 for r in results if r.get("eligible",False))
        st.success(f"✅ Done! **{en}/{len(results)}** resume(s) marked Eligible. Switch to **Results Dashboard →**")

# ═══════════════════════ TAB 2 ═══════════════════════════════════════════════
with tab2:
    results = st.session_state.get("results",[])
    if not results:
        st.markdown("<div style='text-align:center;padding:80px 0;color:#64748b;'><div style='font-size:3rem;'>📊</div><div style='font-family:Syne;font-size:1.2rem;margin-top:12px;'>No results yet</div><div style='font-size:0.85rem;margin-top:8px;'>Complete all 3 steps and click <b>Check Eligibility</b>.</div></div>", unsafe_allow_html=True)
    else:
        el = [r for r in results if r.get("eligible",False)]
        sl = [r for r in results if r.get("overall_score",0)>=shortlist_threshold]
        rj = [r for r in results if r.get("overall_score",0)<reject_threshold]
        av = int(sum(r.get("overall_score",0) for r in results)/len(results))
        for col,val,label,color in zip(st.columns(5),
            [len(results),len(el),len(sl),len(rj),av],
            ["Screened","Eligible","Shortlisted","Rejected","Avg Score"],
            ["#06b6d4","#10b981","#7c3aed","#ef4444","#f59e0b"]):
            with col:
                st.markdown(f"<div class='metric-card'><div class='metric-value' style='color:{color};'>{val}</div><div class='metric-label'>{label}</div></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        for rank,r in enumerate(results,1):
            score=r.get("overall_score",0); color=score_color(score)
            is_e=r.get("eligible",False); ei="✅ ELIGIBLE" if is_e else "❌ NOT ELIGIBLE"; ec="#10b981" if is_e else "#ef4444"
            rec=r.get("recommendation","—"); spct=r.get("school_pct",0); cpct=r.get("college_pct",0)

            with st.expander(f"#{rank}  {r.get('candidate_name','—')}  ·  {ei}  ·  Score {score}/100  ·  {score_label(score)}", expanded=(rank==1)):
                st.markdown(f"""<div class='profile-card'>
                  <div style='font-family:Syne;font-size:0.62rem;letter-spacing:2px;text-transform:uppercase;color:#06b6d4;margin-bottom:8px;'>Candidate Profile</div>
                  <div class='prow'><span class='pkey'>Address</span><span class='pval'>{r.get('address','—')}</span></div>
                  <div class='prow'><span class='pkey'>School</span><span class='pval'>{r.get('school_name','—')} &nbsp;<span class='{pct_cls(spct)}'>{spct}%</span></span></div>
                  <div class='prow'><span class='pkey'>College</span><span class='pval'>{r.get('college_name','—')} &nbsp;<span class='{pct_cls(cpct)}'>{cpct}%</span></span></div>
                </div>""", unsafe_allow_html=True)

                left,right = st.columns([2,1])
                with left:
                    st.markdown("<div class='section-header'>Eligibility Verdict</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='color:{ec};font-weight:700;font-size:0.9rem;margin-bottom:4px;'>{ei}</div>", unsafe_allow_html=True)
                    st.markdown(f"<p style='font-size:0.83rem;color:#94a3b8;line-height:1.65;'>{r.get('eligibility_reason','—')}</p>", unsafe_allow_html=True)
                    st.markdown("<div class='section-header' style='margin-top:10px;'>Academic Assessment</div>", unsafe_allow_html=True)
                    st.markdown(f"<p style='font-size:0.83rem;color:#cbd5e1;line-height:1.65;'>{r.get('academic_assessment','—')}</p>", unsafe_allow_html=True)
                    st.markdown("<div class='section-header' style='margin-top:10px;'>Executive Summary</div>", unsafe_allow_html=True)
                    st.markdown(f"<p style='font-size:0.83rem;color:#cbd5e1;line-height:1.65;'>{r.get('summary','—')}</p>", unsafe_allow_html=True)
                    st.markdown("<div class='section-header' style='margin-top:14px;'>Score Breakdown</div>", unsafe_allow_html=True)
                    for dn,dv in [("Experience",r.get("experience_score",0)),("Skills Match",r.get("skills_score",0)),("Education",r.get("education_score",0)),("Culture Fit",r.get("culture_fit_score",0))]:
                        dc=score_color(dv)
                        st.markdown(f"<div style='display:flex;justify-content:space-between;font-size:0.78rem;color:#94a3b8;'><span>{dn}</span><span style='color:{dc};font-weight:700;'>{dv}%</span></div>", unsafe_allow_html=True)
                        st.markdown(gauge(dv,dc), unsafe_allow_html=True)
                    if r.get("matched_skills"):
                        st.markdown("<div class='section-header' style='margin-top:8px;'>Matched Skills</div>", unsafe_allow_html=True)
                        st.markdown(" ".join(f"<span class='tag'>{s}</span>" for s in r["matched_skills"]), unsafe_allow_html=True)
                    if r.get("missing_skills"):
                        st.markdown("<div class='section-header' style='margin-top:10px;'>Missing Skills</div>", unsafe_allow_html=True)
                        st.markdown(" ".join(f"<span class='tag tag-missing'>{s}</span>" for s in r["missing_skills"]), unsafe_allow_html=True)

                with right:
                    st.markdown(f"""<div class='metric-card' style='margin-bottom:14px;'>
                      <div class='metric-value' style='color:{color};font-size:2.8rem;'>{score}</div>
                      <div class='metric-label'>Overall Score</div>
                      <div style='margin-top:10px;'><span class='score-badge {badge_class(score)}'>{rec}</span></div>
                      <div style='margin-top:10px;font-size:0.82rem;font-weight:700;color:{ec};'>{ei}</div>
                    </div>""", unsafe_allow_html=True)
                    yoe=r.get("years_experience")
                    if yoe is not None:
                        st.markdown(f"<div style='font-size:0.8rem;color:#64748b;text-align:center;margin-bottom:12px;'>⏱ <b style='color:#e2e8f0;'>{yoe} yrs</b> experience</div>", unsafe_allow_html=True)
                    if r.get("strengths"):
                        st.markdown("<div class='section-header'>Strengths</div>", unsafe_allow_html=True)
                        for s in r["strengths"][:4]: st.markdown(f"<div style='font-size:0.78rem;color:#86efac;padding:2px 0;'>✓ {s}</div>", unsafe_allow_html=True)
                    if r.get("gaps"):
                        st.markdown("<div class='section-header' style='margin-top:10px;'>Gaps</div>", unsafe_allow_html=True)
                        for g in r["gaps"][:3]: st.markdown(f"<div style='font-size:0.78rem;color:#fca5a5;padding:2px 0;'>✗ {g}</div>", unsafe_allow_html=True)

                if r.get("interview_questions"):
                    st.markdown("<div class='section-header' style='margin-top:14px;'>Suggested Interview Questions</div>", unsafe_allow_html=True)
                    for q in r["interview_questions"]: st.markdown(f"<div style='font-size:0.82rem;color:#c4b5fd;border-left:2px solid #7c3aed;padding:4px 0 4px 10px;margin:4px 0;'>❓ {q}</div>", unsafe_allow_html=True)

                pos=r.get("positive_signals",[]); rfl=r.get("red_flags",[])
                if pos or rfl:
                    fl1,fl2=st.columns(2)
                    with fl1:
                        if pos:
                            st.markdown("<div class='section-header' style='margin-top:10px;'>Positive Signals</div>", unsafe_allow_html=True)
                            for p in pos[:3]: st.markdown(f"<div style='font-size:0.78rem;color:#6ee7b7;'>⚡ {p}</div>", unsafe_allow_html=True)
                    with fl2:
                        if rfl:
                            st.markdown("<div class='section-header' style='margin-top:10px;'>Red Flags</div>", unsafe_allow_html=True)
                            for rf in rfl[:3]: st.markdown(f"<div style='font-size:0.78rem;color:#fca5a5;'>⚠ {rf}</div>", unsafe_allow_html=True)

        st.divider()
        st.download_button("⬇️ Export Results as JSON", json.dumps(results,indent=2), "screening_results.json","application/json")

# ═══════════════════════ TAB 3 ═══════════════════════════════════════════════
with tab3:
    st.markdown("""
## About
**AI Resume Screener** evaluates candidates using both their academic profile and resume content.

| Technology | Role |
|---|---|
| **Streamlit** | Web UI |
| **Anthropic Claude** | LLM reasoning & scoring |
| **PyMuPDF** | PDF extraction |
| **python-docx** | DOCX extraction |

### What gets evaluated
- School & college scores vs role requirements
- Resume skills & experience vs job description
- Clear eligibility verdict with plain-English reasoning
- Auto-generated interview questions, red flags, positive signals

### Run locally
```bash
pip install streamlit anthropic pymupdf python-docx
export ANTHROPIC_API_KEY=sk-ant-...
streamlit run app.py
```
""")
