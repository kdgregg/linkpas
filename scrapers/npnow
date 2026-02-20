"""NPNow scraper (no detail page scraping needed)"""

from typing import List, Dict
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging

from .base_scraper import BaseScraper
from utils.web_helper import fetch_html

logger = logging.getLogger(__name__)


class NPNowScraper(BaseScraper):
    """Scraper for NPNow jobs"""
    
    def __init__(self, fetch_details: bool = False):
        super().__init__(
            name="npnow",
            base_url="https://www.npnow.com/current-openings/",
            fetch_details=fetch_details
        )
    
    def scrape(self, limit: int = 20) -> List[Dict]:
        """
        Scrape NPNow jobs using standard HTTP requests.
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of job dictionaries
        """
        try:
            html = fetch_html(self.base_url)
            soup = BeautifulSoup(html, "html.parser")
            seen = set()
            jobs = []
            
            for a in soup.select("a[href]"):
                text = (a.get_text(" ", strip=True) or "").strip()
                href = (a.get("href") or "").strip()
                
                if not text or not href:
                    continue
                    
                url = urljoin(self.base_url, href)
                
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
                jobs.append(self.format_job(title=text, url=url))
                
                if len(jobs) >= limit:
                    break
            
            # NPNow doesn't need detail scraping (info already on listing page)
            # But if requested, could be implemented here
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error scraping NPNow: {e}")
            return [{
                "error": str(e),
                "error_type": type(e).__name__,
                "source": self.name
            }]
