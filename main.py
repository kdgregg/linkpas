from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

app = FastAPI(title="Job Scraper API")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; JobScraper/1.0; +http://example.com/bot)"
}

JOB_KEYWORDS = ["nurse practitioner", "physician assistant", "midwife", "pmhnp"]

# === HELPER FUNCTIONS ===

def fetch_html(url: str) -> str:
    resp = requests.get(url, timeout=20, headers=HEADERS)
    resp.raise_for_status()
    return resp.text

def fetch_html_selenium(url: str) -> str:
    """Fetch HTML using Selenium for JavaScript-rendered pages"""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time
    
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        driver.get(url)
        
        # Wait longer for content to load
        time.sleep(10)
        
        # Try to wait for specific elements
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "a"))
            )
        except:
            pass  # Continue even if wait times out
        
        html = driver.page_source
        
        # Also check if there are iframes
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        iframe_contents = []
        
        for iframe in iframes:
            try:
                driver.switch_to.frame(iframe)
                iframe_contents.append(driver.page_source)
                driver.switch_to.default_content()
            except:
                pass
        
        # Combine main page HTML with iframe contents
        full_html = html + "\n".join(iframe_contents)
        
        return full_html
        
    finally:
        driver.quit()
# === TITAN SCRAPER ===

def scrape_titan(limit: int = 20):
    """
    Scrape Titan jobs using Selenium (JavaScript-rendered page)
    """
    try:
        url = "https://jobs.crelate.com/portal/titanplacementgroup"
        html = fetch_html_selenium(url)
        soup = BeautifulSoup(html, "html.parser")
        
        jobs = []
        seen_urls = set()
        
        # Look for all links on the page
        for a_tag in soup.find_all('a', href=True):
            href = a_tag.get('href', '').strip()
            title = a_tag.get_text(strip=True)
            
            if not href or href in seen_urls:
                continue
                
            # Job links contain /job/
            if '/job/' in href:
                if title and len(title) >= 5:
                    full_url = urljoin(url, href)
                    
                    if full_url not in seen_urls:
                        seen_urls.add(full_url)
                        jobs.append({
                            'title': title,
                            'url': full_url,
                            'location': None,
                            'job_number': None
                        })
                        
                        if len(jobs) >= limit:
                            break
        
        return jobs
        
    except Exception as e:
        return [{"error": str(e), "error_type": type(e).__name__}]

@app.get("/jobs/titan")
def jobs_titan(limit: int = Query(20, ge=1, le=100)):
    try:
        jobs = scrape_titan(limit=limit)
        return {"source": "titanplacementgroup", "count": len(jobs), "jobs": jobs}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# === NPNOW SCRAPER ===

NP_NOW_URL = "https://www.npnow.com/current-openings/"
NP_KEYWORDS = ["nurse practitioner", "physician assistant", "midwife", "pmhnp"]

def scrape_npnow(limit: int = 20):
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

@app.get("/debug/titan")
def debug_titan():
    try:
        url = "https://jobs.crelate.com/portal/titanplacementgroup"
        html = fetch_html_selenium(url)
        soup = BeautifulSoup(html, "html.parser")
        
        all_links = soup.find_all('a', href=True)
        
        # Look for any text that might be job titles
        all_text = soup.get_text()
        has_fnp = "family nurse practitioner" in all_text.lower()
        has_job_keywords = any(keyword in all_text.lower() for keyword in ["practitioner", "physician", "nurse"])
        
        link_samples = []
        for a in all_links[:30]:
            href = a.get('href', '')
            text = a.get_text(strip=True)
            link_samples.append({
                'href': href[:150],
                'text': text[:100],
                'has_job_in_href': '/job/' in href
            })
        
        return {
            "html_length": len(html),
            "total_links_found": len(all_links),
            "links_with_job": len([a for a in all_links if '/job/' in a.get('href', '')]),
            "has_job_keywords_in_text": has_job_keywords,
            "has_fnp_in_text": has_fnp,
            "sample_links": link_samples,
            "html_preview": html[:500]  # First 500 chars of HTML
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }
