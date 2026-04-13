# 🎯 AI Resume Screener

> An open-source, LLM-powered resume screening tool built with Python, Streamlit, and Claude AI.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-red?style=flat-square&logo=streamlit)
![Anthropic](https://img.shields.io/badge/Claude-Sonnet-purple?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## 🚀 Live Demo

👉 [https://ai-resume-screener.streamlit.app](https://ai-resume-screener.streamlit.app)

---

## ✨ Features

| Feature | Description |
|---|---|
| 📄 Multi-format | Accepts PDF, DOCX, and TXT resumes |
| 🤖 LLM Analysis | Claude evaluates context, tone, and fit — not just keywords |
| 📊 Scoring Engine | Experience · Skills · Education · Culture Fit |
| 💬 Interview Questions | Auto-generated per candidate |
| 🚩 Red Flag Detection | Identifies risks, gaps, and inconsistencies |
| 📤 JSON Export | Ready for ATS integration |
| ⚙️ Configurable | Adjust shortlist/reject thresholds |

---

## 🏗️ Architecture

```
User → Streamlit UI
          ↓
      File Upload (PDF / DOCX / TXT)
          ↓
      Document Parser
      ├── PyMuPDF    (PDF)
      ├── python-docx (DOCX)
      └── plain text  (TXT)
          ↓
      Claude API (claude-sonnet-4)
      Prompt → structured JSON analysis
          ↓
      Scoring Engine
      ├── overall_score (0-100)
      ├── experience_score
      ├── skills_score
      ├── education_score
      └── culture_fit_score
          ↓
      Results Dashboard + Export
```

---

## 🛠️ Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/ai-resume-screener.git
cd ai-resume-screener
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set your Anthropic API key

```bash
# macOS / Linux
export ANTHROPIC_API_KEY=sk-ant-...

# Windows PowerShell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

Get your key at [console.anthropic.com](https://console.anthropic.com).

### 5. Run the app

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🌐 Deploy to Streamlit Cloud (Free)

1. Push your repository to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and click **New app**.
3. Select your repo, set `app.py` as the main file.
4. Under **Advanced settings → Secrets**, add:
   ```
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
5. Click **Deploy**. Done!

> For secrets, update `app.py` to use `st.secrets["ANTHROPIC_API_KEY"]` and pass it to the `anthropic.Anthropic(api_key=...)` constructor.

---

## 📂 Project Structure

```
ai-resume-screener/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
├── README.md           # This file
├── .gitignore
└── sample_resumes/     # (optional) test resumes
    ├── alice_ml.pdf
    └── bob_backend.pdf
```

---

## 🤖 How the AI Prompt Works

The core of the project is a structured LLM prompt sent to Claude:

```python
prompt = f"""You are an expert technical recruiter. Analyse the resume against
the job description and return a JSON object only.

JOB DESCRIPTION: {job_description}
CANDIDATE NAME:  {candidate_name}
RESUME:          {resume_text}

Return this schema:
{{
  "overall_score": <0-100>,
  "recommendation": "<Shortlist | Interview | Reject>",
  "summary": "...",
  "strengths": [...],
  "gaps": [...],
  "matched_skills": [...],
  "missing_skills": [...],
  "experience_score": <0-100>,
  "skills_score": <0-100>,
  "education_score": <0-100>,
  "culture_fit_score": <0-100>,
  "years_experience": <number>,
  "interview_questions": [...],
  "red_flags": [...],
  "positive_signals": [...]
}}"""
```

Claude returns a structured JSON object which is parsed and rendered in the dashboard.

---

## 📝 Medium / Dev.to Article Outline

The published article walks through:

1. **The Problem** — Manual CV screening is slow and biased
2. **Solution Architecture** — Streamlit + Claude API
3. **Building the File Parser** — PyMuPDF, python-docx
4. **Prompt Engineering** — Getting structured JSON from Claude
5. **Scoring Logic** — Multi-dimensional, configurable thresholds
6. **Deploying to Streamlit Cloud** — Free hosting in 5 minutes
7. **What's Next** — ATS integration, batch processing, bias detection

---

## 🤝 Contributing

PRs welcome! Please open an issue first to discuss major changes.

---

## 📄 License

MIT © 2024 Your Name
