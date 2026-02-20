from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

app = FastAPI(title="Job Scraper API")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; JobScraper/1.0; +http://example.com/bot)"
}

# === HELPER FUNCTIONS ===

def fetch_html(url: str) -> str:
    resp = requests.get(url, timeout=20, headers=HEADERS)
    resp.raise_for_status()
    return resp.text

def fetch_html_selenium(url: str, wait_time: int = 15) -> str:
    """Fetch HTML using Selenium for JavaScript-rendered pages"""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    
    try:
        driver.get(url)
        
        # Wait for page to load
        time.sleep(wait_time)
        
        # Try multiple wait strategies
        try:
            # Wait for any anchor tags to appear
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/job/']"))
            )
        except:
            # If specific wait fails, try waiting for general content
            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "main"))
                )
            except:
                pass  # Continue anyway
        
        # Additional wait for dynamic content
        time.sleep(5)
        
        # Scroll to load lazy-loaded content
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
        html = driver.page_source
        return html
        
    finally:
        driver.quit()

# === TITAN SCRAPER ===

def scrape_titan(limit: int = 20):
    """
    Scrape Titan jobs using Selenium
    """
    try:
        url = "https://jobs.crelate.com/portal/titanplacementgroup"
        html = fetch_html_selenium(url, wait_time=15)
        soup = BeautifulSoup(html, "html.parser")
        
        jobs = []
        seen_urls = set()
        
        # Strategy 1: Look for links with /job/ in href
        job_links = soup.find_all('a', href=lambda x: x and '/job/' in x)
        
        for a_tag in job_links:
            href = a_tag.get('href', '').strip()
            title = a_tag.get_text(strip=True)
            
            if not href or href in seen_urls:
                continue
            
            # Skip navigation links
            if len(title) < 5 or title.lower() in ['home', 'about', 'contact', 'apply', 'back']:
                continue
                
            full_url = urljoin(url, href)
            
            if full_url not in seen_urls:
                seen_urls.add(full_url)
                
                # Try to extract job number from URL
                job_number = None
                if '/job/' in href:
                    job_number = href.split('/job/')[-1].split('?')[0].split('#')[0]
                
                jobs.append({
                    'title': title,
                    'url': full_url,
                    'location': None,
                    'job_number': job_number
                })
                
                if len(jobs) >= limit:
                    break
        
        # Strategy 2: If no jobs found, look for any text that might be job titles
        if len(jobs) == 0:
            # Look for divs or sections that might contain job listings
            for elem in soup.find_all(['div', 'article', 'section']):
                text = elem.get_text(strip=True)
                # Look for healthcare job titles
                if any(keyword in text.lower() for keyword in [
                    'practitioner', 'physician', 'nurse', 'therapist', 
                    'dentist', 'hygienist', 'medical', 'doctor'
                ]):
                    # Find links within this element
                    links = elem.find_all('a', href=True)
                    for link in links:
                        href = link.get('href', '')
                        if '/job/' in href or '/portal/' in href:
                            title = link.get_text(strip=True)
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
        
        if len(jobs) >= limit:
            break
    
    return jobs

@app.get("/jobs/npnow")
def jobs_npnow(limit: int = Query(20, ge=1, le=100)):
    try:
        jobs = scrape_npnow(limit=limit)
        return {"source": "npnow", "count": len(jobs), "jobs": jobs}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# === DEBUG ENDPOINT ===

@app.get("/debug/titan")
def debug_titan():
    try:
        url = "https://jobs.crelate.com/portal/titanplacementgroup"
        html = fetch_html_selenium(url, wait_time=15)
        soup = BeautifulSoup(html, "html.parser")
        
        all_links = soup.find_all('a', href=True)
        job_links = [a for a in all_links if '/job/' in a.get('href', '')]
        
        # Sample links
        link_samples = []
        for a in all_links[:50]:
            href = a.get('href', '')
            text = a.get_text(strip=True)
            link_samples.append({
                'href': href[:150],
                'text': text[:100],
                'has_job_in_href': '/job/' in href
            })
        
        # Check for job-related text
        full_text = soup.get_text()
        has_healthcare_keywords = any(kw in full_text.lower() for kw in [
            'practitioner', 'physician', 'nurse', 'dentist', 'therapist'
        ])
        
        return {
            "html_length": len(html),
            "total_links_found": len(all_links),
            "links_with_job": len(job_links),
            "has_healthcare_keywords": has_healthcare_keywords,
            "sample_links": link_samples,
            "page_title": soup.title.string if soup.title else "No title",
            "html_snippet": html[1000:2000] if len(html) > 2000 else html
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }

@app.get("/")
def root():
    return {
        "message": "Job Scraper API",
        "endpoints": {
            "titan_jobs": "/jobs/titan",
            "npnow_jobs": "/jobs/npnow",
            "debug_titan": "/debug/titan",
            "docs": "/docs"
        }
    }
