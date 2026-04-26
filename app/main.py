from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, Response
import zipfile, io, os
from collections import Counter
from app.parsers import parse_text_log, parse_yalv_log, parse_windows_event_log, parse_sql_log, extract_labx_version
from app.ai_service import analyze_all_errors_together
from app.pdf_service import create_pdf_report

app = FastAPI()
report_store = {"analysis": "", "issues": [], "version": ""}

@app.get("/")
async def get_frontend():
    with open("index.html", "r", encoding="utf-8") as f: return HTMLResponse(content=f.read())

@app.get("/logo")
async def get_logo():
    for path in [":).png", ":) logo.png"]:
        if os.path.exists(path): return FileResponse(path)
    return {"error": "Logo missing"}

@app.post("/analyze-zip")
async def analyze_zip(file: UploadFile = File(...)):
    app_err, win_err, sql_err = [], [], []
    detected_v = "Unknown"
    
    try:
        content = await file.read()
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            # Pierwszy przebieg: Szukamy wersji we WSZYSTKICH plikach
            for f_info in z.infolist():
                if detected_v != "Unknown": break
                if not f_info.is_dir() and f_info.file_size > 0:
                    with z.open(f_info) as f:
                        try:
                            sample = f.read(5000).decode('utf-8', errors='ignore')
                            v = extract_labx_version(sample)
                            if v: detected_v = v
                        except: pass

            # Drugi przebieg: Parsowanie błędów
            for f_info in z.infolist():
                fname = f_info.filename.lower()
                if f_info.is_dir() or f_info.file_size == 0: continue
                with z.open(f_info) as f:
                    raw = f.read()
                    if "eventlog" in fname:
                        win_err.extend(parse_windows_event_log(raw))
                    elif "sqlerrorlog" in fname:
                        try: txt = raw.decode('utf-16')
                        except: txt = raw.decode('utf-8', errors='ignore')
                        sql_err.extend(parse_sql_log(txt))
                    elif "log" in fname or "yalv" in fname:
                        txt = raw.decode('utf-8', errors='ignore')
                        if "yalv" in fname: app_err.extend(parse_yalv_log(txt))
                        else: app_err.extend(parse_text_log(txt))

        def safe_top(err_list, src):
            if not err_list: return []
            counts = Counter([e["message"] for e in err_list if len(e["message"]) > 10])
            res = []
            for msg, count in counts.most_common(3):
                sample = [e for e in err_list if e["message"] == msg][0]
                res.append({"message": msg, "occurrences": count, "location": sample["location"], "source": src})
            return res

        all_top = safe_top(app_err, "SystemX App") + safe_top(win_err, "Windows") + safe_top(sql_err, "SQL Server")
        analysis = analyze_all_errors_together(all_top, detected_v)

        global report_store
        report_store = {"analysis": analysis, "issues": all_top, "version": detected_v}
        return {"status": "success", "version": detected_v, "total_errors": len(app_err), "top_issues": all_top, "analysis": analysis}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.get("/download-pdf")
async def download_pdf():
    pdf_bytes = create_pdf_report(report_store["analysis"], report_store["issues"], report_store["version"])
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=SystemX_Report.pdf"})