# Build an AI-Powered Resume Screener with Python, Streamlit & Claude

> Automate candidate shortlisting in under 200 lines of Python — with live scoring, gap analysis, and auto-generated interview questions.

---

## The Problem

Every hiring manager knows the drill: 200 applications, one open role, one afternoon. Manual screening is slow, error-prone, and riddled with unconscious bias. Keyword search misses great candidates and promotes keyword-stuffers.

What if you could give every resume the same thorough 60-second read from a world-class recruiter?

That's exactly what we're building.

---

## What We're Building

An AI Resume Screener that:

- Accepts **PDF, DOCX, and TXT** resumes via drag-and-drop
- Evaluates each resume against a pasted **Job Description**
- Returns a **0–100 match score** across four dimensions (Experience, Skills, Education, Culture Fit)
- Generates **interview questions** and flags **red flags** per candidate
- Renders an interactive **ranking dashboard** with export to JSON

Stack: **Python · Streamlit · Anthropic Claude · PyMuPDF · python-docx**

---

## Architecture Overview

```
User uploads resumes + pastes JD
        ↓
Document Parser  (PDF → PyMuPDF, DOCX → python-docx, TXT → utf-8)
        ↓
Claude API  (claude-sonnet — structured JSON response)
        ↓
Scoring Engine
        ↓
Streamlit Dashboard
```

The key insight: instead of writing NLP rules, we describe the scoring criteria in plain English and let Claude reason about the candidate holistically.

---

## Step 1 — Project Setup

```bash
mkdir ai-resume-screener && cd ai-resume-screener
python -m venv venv && source venv/bin/activate
pip install streamlit anthropic pymupdf python-docx
export ANTHROPIC_API_KEY=sk-ant-...
```

---

## Step 2 — Parsing Resumes

Different formats need different parsers:

```python
def extract_text_from_pdf(file) -> str:
    import fitz  # PyMuPDF
    pdf = fitz.open(stream=file.read(), filetype="pdf")
    return "".join(page.get_text() for page in pdf)

def extract_text_from_docx(file) -> str:
    from docx import Document
    import io
    doc = Document(io.BytesIO(file.read()))
    return "\n".join(p.text for p in doc.paragraphs)
```

For TXT files, a simple `file.read().decode("utf-8")` does the job.

---

## Step 3 — The Prompt (The Heart of the Project)

Prompt engineering is where the magic lives. We ask Claude to act as an expert recruiter and return a strict JSON schema:

```python
def screen_resume(resume_text, job_description, candidate_name):
    client = anthropic.Anthropic()
    prompt = f"""You are an expert technical recruiter.
Analyse the resume against the job description.
Return ONLY a JSON object with this schema:

{{
  "overall_score": <0-100>,
  "recommendation": "<Shortlist | Interview | Reject>",
  "summary": "<2-3 sentence executive summary>",
  "strengths": ["..."],
  "gaps": ["..."],
  "matched_skills": ["..."],
  "missing_skills": ["..."],
  "experience_score": <0-100>,
  "skills_score": <0-100>,
  "education_score": <0-100>,
  "culture_fit_score": <0-100>,
  "years_experience": <number or null>,
  "interview_questions": ["...", "...", "..."],
  "red_flags": ["..."],
  "positive_signals": ["..."]
}}

JOB DESCRIPTION:
{job_description}

CANDIDATE: {candidate_name}

RESUME:
{resume_text}"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return json.loads(message.content[0].text)
```

**Key prompt engineering choices:**
- "Return ONLY a JSON object" — prevents markdown fences and preamble
- Explicit schema — Claude follows it reliably
- Role prompt ("expert technical recruiter") — improves reasoning quality
- Both JD and resume in the same context — enables true comparison, not keyword matching

---

## Step 4 — The Streamlit UI

Streamlit lets us build a professional multi-tab interface without JavaScript:

```python
st.set_page_config(page_title="AI Resume Screener", layout="wide")

tab1, tab2 = st.tabs(["📥 Screen Resumes", "📊 Dashboard"])

with tab1:
    job_desc = st.text_area("Job Description", height=300)
    files = st.file_uploader("Upload Resumes", accept_multiple_files=True,
                              type=["pdf","docx","txt"])
    if st.button("🚀 Screen"):
        results = []
        for f in files:
            text = parse(f)
            result = screen_resume(text, job_desc, f.name)
            results.append(result)
        results.sort(key=lambda x: x["overall_score"], reverse=True)
        st.session_state["results"] = results
```

---

## Step 5 — Score Visualisation

We render dynamic gauge bars and score badges using inline HTML:

```python
def gauge_html(value, color):
    return f"""
    <div style='background:#1e1e2e;border-radius:8px;height:8px;overflow:hidden;'>
      <div style='width:{value}%;height:100%;background:{color};border-radius:8px;'></div>
    </div>"""
```

No external charting library needed — just CSS.

---

## Step 6 — Deploy to Streamlit Cloud (Free)

1. Push to GitHub
2. Sign in at [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Select your repo → `app.py`
4. **Advanced → Secrets**:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
5. Hit **Deploy** — live in ~90 seconds.

Update the client in `app.py`:
```python
client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
```

---

## Results

For a batch of 5 resumes against a Senior Data Scientist JD, the screener correctly:

- Ranked the ML engineer with PyTorch + MLflow experience #1 (score 88)
- Flagged a 3-month employment gap as a red flag
- Generated targeted interview questions on model deployment for the top candidate
- Recommended rejection for a resume with only 1 year of experience

Total processing time: ~12 seconds for 5 resumes.

---

## What's Next

- **Bias detection** — prompt Claude to flag potentially biased language in the JD
- **ATS export** — push results to Greenhouse or Lever via API
- **Batch processing** — screen 100+ resumes with async API calls
- **Custom scoring weights** — let the hiring manager adjust dimension weights
- **Cover letter analysis** — extend the parser to handle cover letters

---

## The Code

Full source on GitHub: [github.com/your-username/ai-resume-screener](https://github.com/your-username/ai-resume-screener)

Live demo: [ai-resume-screener.streamlit.app](https://ai-resume-screener.streamlit.app)

---

*If this was useful, drop a ⭐ on GitHub and share with your team.*
