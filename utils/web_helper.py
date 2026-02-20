"""HTTP request helper utilities for standard web scraping"""

import requests
import logging

logger = logging.getLogger(__name__)


HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; JobScraper/1.0; +http://example.com/bot)"
}


def fetch_html(url: str, timeout: int = 20) -> str:
    """
    Fetch HTML using standard HTTP request.
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        
    Returns:
        Page HTML content
    """
    logger.info(f"Fetching {url} with HTTP request...")
    resp = requests.get(url, timeout=timeout, headers=HEADERS)
    resp.raise_for_status()
    logger.info(f"Successfully fetched {url} ({len(resp.text)} bytes)")
    return resp.text
