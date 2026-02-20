"""Titan Placement Group scraper with detail page support"""

from typing import List, Dict
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging

from .base_scraper import BaseScraper
from utils.selenium_helper import fetch_html_selenium

logger = logging.getLogger(__name__)


class TitanScraper(BaseScraper):
    """Scraper for Titan Placement Group jobs"""
    
    def __init__(self, fetch_details: bool = False):
        super().__init__(
            name="titanplacementgroup",
            base_url="https://jobs.crelate.com/portal/titanplacementgroup",
            fetch_details=fetch_details
        )
    
    def scrape(self, limit: int = 20) -> List[Dict]:
        """
        Scrape Titan jobs using Selenium for JavaScript-rendered content.
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of job dictionaries, optionally enriched with details
        """
        try:
            html = fetch_html_selenium(self.base_url, wait_time=15)
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
                    
                full_url = urljoin(self.base_url, href)
                
                if full_url not in seen_urls:
                    seen_urls.add(full_url)
                    
                    # Extract job number from URL
                    job_number = None
                    if '/job/' in href:
                        job_number = href.split('/job/')[-1].split('?')[0].split('#')[0]
                    
                    jobs.append(self.format_job(
                        title=title,
                        url=full_url,
                        location=None,
                        job_number=job_number
                    ))
                    
                    if len(jobs) >= limit:
                        break
            
            # Strategy 2: If no jobs found, look for context-based matches
            if len(jobs) == 0:
                for elem in soup.find_all(['div', 'article', 'section']):
                    text = elem.get_text(strip=True)
                    if any(keyword in text.lower() for keyword in [
                        'practitioner', 'physician', 'nurse', 'therapist', 
                        'dentist', 'hygienist', 'medical', 'doctor'
                    ]):
                        links = elem.find_all('a', href=True)
                        for link in links:
                            href = link.get('href', '')
                            if '/job/' in href or '/portal/' in href:
                                title = link.get_text(strip=True)
                                if title and len(title) >= 5:
                                    full_url = urljoin(self.base_url, href)
                                    if full_url not in seen_urls:
                                        seen_urls.add(full_url)
                                        jobs.append(self.format_job(
                                            title=title,
                                            url=full_url
                                        ))
                                        if len(jobs) >= limit:
                                            break
            
            # Enrich with details if requested
            if self.fetch_details:
                logger.info(f"Fetching details for {len(jobs)} Titan jobs...")
                jobs = self.enrich_with_details(jobs)
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error scraping Titan: {e}")
            return [{
                "error": str(e),
                "error_type": type(e).__name__,
                "source": self.name
            }]
    
    def scrape_job_details(self, job_url: str) -> Dict:
        """
        Scrape additional details from a Titan job detail page.
        
        Args:
            job_url: URL of the job detail page
            
        Returns:
            Dictionary with description, requirements, salary, etc.
        """
        try:
            html = fetch_html_selenium(job_url, wait_time=10)
            soup = BeautifulSoup(html, "html.parser")
            
            details = {}
            
            # Extract job description
            # Common selectors for job descriptions
            description_selectors = [
                {'class': 'job-description'},
                {'class': 'description'},
                {'id': 'job-description'},
                {'class': 'job-details'},
            ]
            
            for selector in description_selectors:
                desc_elem = soup.find('div', selector)
                if desc_elem:
                    details['description'] = desc_elem.get_text(strip=True)
                    break
            
            # Extract location if available on detail page
            location_elem = soup.find('span', class_='location') or soup.find('div', class_='job-location')
            if location_elem:
                details['location'] = location_elem.get_text(strip=True)
            
            # Extract salary if available
            salary_elem = soup.find('span', class_='salary') or soup.find('div', class_='compensation')
            if salary_elem:
                details['salary'] = salary_elem.get_text(strip=True)
            
            # Extract requirements/qualifications
            requirements_elem = soup.find('div', class_='requirements') or soup.find('div', class_='qualifications')
            if requirements_elem:
                details['requirements'] = requirements_elem.get_text(strip=True)
            
            # Extract company info
            company_elem = soup.find('div', class_='company-info')
            if company_elem:
                details['company_info'] = company_elem.get_text(strip=True)
            
            logger.info(f"Successfully scraped details from {job_url}")
            return details
            
        except Exception as e:
            logger.error(f"Error scraping details from {job_url}: {e}")
            return {'details_error': str(e)}
