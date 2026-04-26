import os
import json
import hashlib
from google import genai
from google.genai import types

API_KEY = ":)"
client = genai.Client(api_key=API_KEY)
CACHE_FILE = "ai_cache.json"

def get_cache_hash(text):
    """Tworzy unikalny 'odcisk palca' dla zestawu błędów."""
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_to_cache(error_hash, analysis):
    cache = load_cache()
    cache[error_hash] = analysis
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=4)

def analyze_all_errors_together(top_issues_list, version="Unknown"):
    if not top_issues_list: return "No data."

    # Przygotowanie tekstu do analizy i do Hasha
    ctx = ""
    for i, issue in enumerate(top_issues_list, 1):
        ctx += f"#{i} [{issue['source']}]: {issue['message'][:600]}\n"
    
    error_hash = get_cache_hash(ctx + version)
    cache = load_cache()

    # Sprawdzenie czy mamy to w pamięci (OSZCZĘDNOŚĆ LIMITU)
    if error_hash in cache:
        print("--- [CACHE HIT] Pobrano analizę z pamięci lokalnej ---")
        return cache[error_hash]

    prompt = f"""[STRICT: NO INTROS. NO "AS AN ENGINEER". START DIRECTLY WITH POINTS.]
System: SystemX v{version}
Analyze these logs and provide a fix:
{ctx}

Output Format:
ROOT CAUSE: (One sentence)
FIX STEPS: (Numbered list)
COMMANDS: (Code block)"""

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=6000,
                temperature=0.7,
                safety_settings=[types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE")]
            )
        )
        
        if response.text:
            save_to_cache(error_hash, response.text) # Zapisujemy do cache
            return response.text
        return "Empty response from AI."

    except Exception as e:
        if "429" in str(e):
            return "⚠️ AI QUOTA EXCEEDED: Google's free tier limit reached (20 requests/day). Please wait 24h or use a paid/Azure key. The rest of the report is still available below."
        return f"AI Error: {str(e)}"