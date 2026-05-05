> 💡 **Portfolio Note:** *This tool was originally developed internally in Q1 2026. It has been cleaned of sensitive data, API keys, and internal business logic, and published here as a showcase of my technical stack.*


# SystemX AI Log Analyzer

**An automated diagnostic tool that parses enterprise software logs, extracts critical errors, and uses AI (Google Gemini) to determine root causes and provide actionable fix steps.**

---

### 🚨 The Problem
Enterprise software generates massive amounts of logs across different formats (Text logs, XML/Yalv logs, Windows Event Viewer, SQL Server logs). When a system crashes, support engineers spend hours manually correlating timestamps and reading stack traces to figure out what went wrong.

### 💡 The Solution
An automated FastAPI backend that:
1. Accepts a `.zip` archive containing system logs.
2. Parsers multiple log formats simultaneously to extract the top critical errors.
3. Automatically detects the software version.
4. Sends the correlated error context to an LLM (Google Gemini 3.1 Flash) with strict prompt engineering to force a structured output: **Root Cause, Fix Steps, and CLI Commands**.
5. Caches AI responses locally to eliminate redundant API costs.
6. Generates a downloadable PDF diagnostic report.

### 🛠️ Tech Stack & Architecture
- **Backend:** FastAPI (Python), `uvicorn`, `python-multipart` (file uploads)
- **Log Parsers:** `python-evtx` (Windows Event Log), `zipfile`, custom Regex parsers for YALV/XML/Text/SQL
- **AI Integration:** `google-genai` SDK (Gemini models via Vertex AI / Google Cloud)
- **PDF Generation:** `fpdf2` library
- **Performance Optimization:** MD5 hashing for query caching (drastically reduces token usage and API costs).
- **Frontend:** Vanilla HTML/JS with asynchronous polling for the diagnostic report.

### 📈 Business Impact
- **Eliminates Manual Work:** Turns a 2-hour manual log review into a 10-second automated pipeline.
- **Cost Efficiency:** Local caching prevents the AI from re-analyzing known errors.
- **Scalability:** Easily adaptable to other enterprise software by simply adding new Regex parsers in `parsers.py`.

---

### 🚀 How to Run

1. Clone the repository.
2. Install dependencies: `pip install fastapi uvicorn google-genai fpdf2 python-evtx python-multipart`
3. Add your Gemini API Key as an environment variable or inside `app/ai_service.py`.
4. Run the server: `uvicorn app.main:app --reload`
5. Open `http://localhost:8000` and upload your log archive.

*(Note: Sensitive company data and hardcoded API keys have been removed/anonymized from this repository).*
