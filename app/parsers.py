import re
import io
from datetime import datetime
import Evtx.Evtx as evtx

TEXT_PATTERN = re.compile(r"========== Log entry (INFO|WARN|ERROR|FATAL)\s*:\s*(.*?)\s*==========(.*?)(?=(========== Log entry|\[Session end\]|\[Session start\]|\Z))", re.DOTALL)
LOCATION_PATTERN = re.compile(r"Location:\[(.*?)\]")
MESSAGE_PATTERN = re.compile(r"Message:\s*(.*)", re.DOTALL)
XML_PATTERN = re.compile(r'<log4j:event[^>]*timestamp="(\d+)"[^>]*level="([^"]+)"[^>]*>.*?<log4j:message>(.*?)</log4j:message>.*?class="([^"]*)".*?</log4j:event>', re.DOTALL)

def extract_labx_version(content: str):
    # Rozszerzona lista wzorców wersji
    patterns = [
        r'SystemX Version:\s*(\d+\.\d+\.\d+\.\d+)',
        r'ProductVersion\s*=\s*"?(\d+\.\d+\.\d+\.\d+)"?',
        r'Assembly Version:\s*(\d+\.\d+\.\d+\.\d+)',
        r'<version>(\d+\.\d+\.\d+\.\d+)</version>',
        r'SystemX\s+(\d+\.\d+\.\d+)'
    ]
    for p in patterns:
        match = re.search(p, content, re.IGNORECASE)
        if match: return match.group(1)
    return None

def parse_text_log(content: str):
    errors = []
    for match in TEXT_PATTERN.finditer(content):
        if match.group(1).strip() in ["ERROR", "FATAL"]:
            body = match.group(3).strip()
            loc = LOCATION_PATTERN.search(body)
            msg = MESSAGE_PATTERN.search(body)
            errors.append({
                "timestamp": match.group(2).strip(),
                "location": loc.group(1).strip() if loc else "Unknown",
                "message": msg.group(1).strip() if msg else body[:300],
                "source": "SystemX App Log"
            })
    return errors

def parse_yalv_log(content: str):
    errors = []
    for match in XML_PATTERN.finditer(content):
        if match.group(2).strip() in ["ERROR", "FATAL"]:
            try:
                dt = datetime.fromtimestamp(int(match.group(1)) / 1000.0)
                ts = dt.strftime('%Y-%m-%d %H:%M:%S')
            except: ts = "Unknown"
            errors.append({
                "timestamp": ts,
                "location": match.group(4).strip(),
                "message": match.group(3).strip(),
                "source": "SystemX Yalv Log"
            })
    return errors

def parse_sql_log(content: str):
    errors = []
    for line in content.splitlines():
        # Szukamy tylko linii zawierających realne kody błędów SQL (np. Error: 17054)
        if re.search(r"Error:\s*\d+", line, re.IGNORECASE) or "failed" in line.lower():
            errors.append({
                "timestamp": line[:20].strip(),
                "location": "SQL Server Engine",
                "message": line[20:].strip(),
                "source": "SQL ERRORLOG"
            })
        if len(errors) > 10: break
    return errors

def parse_windows_event_log(file_bytes):
    errors = []
    try:
        if not file_bytes.startswith(b'ElfFile'): return []
        with io.BytesIO(file_bytes) as f:
            with evtx.Evtx(f) as log:
                for record in log.records():
                    node = record.xml()
                    if '<Level>2</Level>' in node or '<Level>1</Level>' in node:
                        prov = re.search(r'Provider Name="([^"]+)"', node)
                        msg = re.search(r'<Data>(.*?)</Data>', node)
                        time = re.search(r'SystemTime="([^"]+)"', node)
                        errors.append({
                            "timestamp": time.group(1) if time else "Unknown",
                            "location": prov.group(1) if prov else "Windows",
                            "message": msg.group(1) if msg else "System Error",
                            "source": "Windows Log"
                        })
                        if len(errors) > 10: break
    except: pass
    return errors