"""
Job Scraper API

A modular FastAPI application for scraping job listings from multiple sources.
Supports optional detail page scraping for comprehensive job information.
"""

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from typing import List, Dict
import logging

from scrapers.titan import TitanScraper
from scrapers.npnow import NPNowScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(
    title="Job Scraper API",
    description="Scrape job listings from multiple healthcare recruiting sites with optional detail fetching",
    version="2.0.0"
)

# === API ENDPOINTS ===

@app.get("/")
def root():
    """API information and available endpoints"""
    return {
        "message": "Job Scraper API v2.0",
        "version": "2.0.0",
        "features": ["Multi-source scraping", "Optional detail fetching", "Modular architecture"],
        "endpoints": {
            "titan_jobs": "/jobs/titan",
            "npnow_jobs": "/jobs/npnow",
            "all_jobs": "/jobs/all",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/jobs/titan")
def jobs_titan(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of jobs to return"),
    details: bool = Query(False, description="Fetch full job details from detail pages (slower)")
):
    """
    Get job listings from Titan Placement Group.
    
    - **limit**: Maximum number of jobs (1-100)
    - **details**: Set to true to scrape full job descriptions, requirements, etc.
    """
    try:
        scraper = TitanScraper(fetch_details=details)
        jobs = scraper.scrape(limit=limit)
        return {
            "source": "titanplacementgroup",
            "count": len(jobs),
            "details_fetched": details,
            "jobs": jobs
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "source": "titanplacementgroup"}
        )


@app.get("/jobs/npnow")
def jobs_npnow(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of jobs to return")
):
    """
    Get job listings from NPNow.
    
    - **limit**: Maximum number of jobs (1-100)
    """
    try:
        scraper = NPNowScraper()
        jobs = scraper.scrape(limit=limit)
        return {"source": "npnow", "count": len(jobs), "jobs": jobs}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "source": "npnow"}
        )


@app.get("/jobs/all")
def jobs_all(
    limit: int = Query(20, ge=1, le=100, description="Maximum jobs per source"),
    details: bool = Query(False, description="Fetch full job details (applies to supported scrapers)")
):
    """
    Get job listings from ALL sources.
    
    - **limit**: Maximum jobs per source (1-100)
    - **details**: Fetch full details where supported (slower)
    """
    all_jobs = []
    sources = []
    
    # List of all scraper classes with detail support flags
    scrapers_config = [
        (TitanScraper, details),  # Titan supports details
        (NPNowScraper, False),    # NPNow doesn't need details
    ]
    
    for ScraperClass, fetch_details in scrapers_config:
        try:
            scraper = ScraperClass(fetch_details=fetch_details)
            jobs = scraper.scrape(limit=limit)
            all_jobs.extend(jobs)
            sources.append(scraper.name)
        except Exception as e:
            # Continue with other scrapers even if one fails
            all_jobs.append({
                "error": str(e),
                "source": ScraperClass.__name__
            })
    
    return {
        "sources": sources,
        "total_count": len(all_jobs),
        "details_fetched": details,
        "jobs": all_jobs
    }

@app.get("/debug/job-detail")
def debug_job_detail(url: str = Query(..., description="Job detail URL to inspect")):
    """Debug endpoint to see what HTML is on a job detail page"""
    from utils.selenium_helper import fetch_html_selenium
    from bs4 import BeautifulSoup
    
    try:
        html = fetch_html_selenium(url, wait_time=10)
        soup = BeautifulSoup(html, "html.parser")
        
        # Find all div, section, article elements with class or id attributes
        elements_with_classes = []
        for tag in soup.find_all(['div', 'section', 'article', 'span', 'p', 'h1', 'h2', 'h3']):
            if tag.get('class') or tag.get('id'):
                text_preview = tag.get_text(strip=True)[:100]
                if text_preview:  # Only include if there's text
                    elements_with_classes.append({
                        'tag': tag.name,
                        'class': ' '.join(tag.get('class', [])),
                        'id': tag.get('id'),
                        'text_preview': text_preview
                    })
        
        return {
            "url": url,
            "html_length": len(html),
            "page_title": soup.title.string if soup.title else None,
            "elements_count": len(elements_with_classes),
            "elements_with_classes": elements_with_classes[:100],  # First 100 elements
            "all_text_preview": soup.get_text(strip=True)[:2000]  # First 2000 chars of text
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "scrapers": ["titan", "npnow"],
        "features": {
            "detail_scraping": ["titan"]
        }
    }
```

4. **Commit changes**
5. **Wait for rebuild**
6. **Restart container**
7. **Try again:**
```
http://76.13.98.151:8000/debug/job-detail?url=https://jobs.crelate.com/portal/titanplacementgroup/job/95z7txbikcz3pk91o3bwet4xor
@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "scrapers": ["titan", "npnow"],
        "features": {
            "detail_scraping": ["titan"]
        }
    }
