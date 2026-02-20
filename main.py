from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import requests

app = FastAPI(title="Job Scraper API")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; JobScraper/1.0; +http://example.com/bot)"
}

# --- Titan (JSON API) ---
TITAN_API = "https://jobs.crelate.com/portal/api/postings/titanplacementgroup"
JOB_KEYWORDS = ["nurse practitioner", "physician assistant", "midwife", "pmhnp"]

def fetch_json(url: str) -> dict:
    resp = requests.get(url, timeout=20, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()

def scrape_titan(limit: int = 20):
    """
    Scrape Titan jobs from their HTML page since the JSON API doesn't work.
    """
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    
    url = "https://jobs.crelate.com/portal/titanplacementgroup"
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    
    jobs = []
    
    for job_elem in soup.find_all('a', href=True):
        href = job_elem.get('href', '')
        if '/job/' in href:
            title = job_elem.get_text(strip=True)
            full_url = urljoin(url, href)
            
            # Filter by keywords
            if any(k in title.lower() for k in JOB_KEYWORDS):
                if full_url not in [j['url'] for j in jobs]:
                    jobs.append({
                        'title': title,
                        'url': full_url,
                        'location': None,
                        'job_number': None
                    })
                    
                    if len(jobs) >= limit:
                        break
    
    return jobs

@app.get("/jobs/titan")
def jobs_titan(limit: int = Query(20, ge=1, le=100)):
    try:
        jobs = scrape_titan(limit=limit)
        return {"source": "titanplacementgroup", "count": len(jobs), "jobs": jobs}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# --- NPNow ---
NP_NOW_URL = "https://www.npnow.com/current-openings/"
NP_KEYWORDS = ["nurse practitioner", "physician assistant", "midwife", "pmhnp"]

def fetch_html(url: str) -> str:
    resp = requests.get(url, timeout=20, headers=HEADERS)
    resp.raise_for_status()
    return resp.text

def scrape_npnow(limit: int = 20):
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    
    html = fetch_html(NP_NOW_URL)
    soup = BeautifulSoup(html, "html.parser")
    seen = set()
    jobs = []
    
    for a in soup.select("a[href]"):
        text = (a.get_text(" ", strip=True) or "").strip()
        href = (a.get("href") or "").strip()
        
        if not text or not href:
            continue
            
        url = urljoin(NP_NOW_URL, href)
        
        if "npnow.com" not in url:
            continue
            
        if url in seen:
            continue
            
        if any(x in url.lower() for x in [
            "/current-openings",
            "/contact",
            "/about",
            "/privacy",
            "/terms",
            "mailto:",
            "tel:",
        ]):
            continue
            
        seen.add(url)
        jobs.append({"title": text, "url": url})
        
        if len(jobs) >= max(100, limit * 5):
            break
    
    out = []
    for j in jobs:
        t = j["title"].lower()
        if any(k in t for k in NP_KEYWORDS):
            out.append(j)
        if len(out) >= limit:
            break
            
    return out

@app.get("/jobs/npnow")
def jobs_npnow(limit: int = Query(20, ge=1, le=100)):
    try:
        jobs = scrape_npnow(limit=limit)
        return {"source": "npnow", "count": len(jobs), "jobs": jobs}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
