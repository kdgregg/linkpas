"""Base scraper class that all scrapers inherit from"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Base class for all job scrapers.
    
    All scrapers must implement the scrape() method.
    Optionally implement scrape_job_details() for detail page scraping.
    """
    
    def __init__(self, name: str, base_url: str, fetch_details: bool = False):
        """
        Initialize the scraper.
        
        Args:
            name: Scraper identifier (e.g., 'titan', 'npnow')
            base_url: Base URL for the job listings
            fetch_details: Whether to scrape detail pages for each job
        """
        self.name = name
        self.base_url = base_url
        self.fetch_details = fetch_details
    
    @abstractmethod
    def scrape(self, limit: int = 20) -> List[Dict]:
        """
        Scrape jobs from the source.
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of job dictionaries
        """
        pass
    
    def scrape_job_details(self, job_url: str) -> Dict:
        """
        Scrape additional details from a job detail page.
        
        Override this method in scrapers that support detail scraping.
        
        Args:
            job_url: URL of the job detail page
            
        Returns:
            Dictionary with additional job fields (description, salary, etc.)
            Empty dict by default if not implemented.
        """
        logger.warning(f"{self.name} does not implement detail scraping")
        return {}
    
    def format_job(
        self,
        title: str,
        url: str,
        location: Optional[str] = None,
        job_number: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        Standardize job format across all scrapers.
        
        Args:
            title: Job title
            url: Job posting URL
            location: Job location (optional)
            job_number: Job ID/number (optional)
            **kwargs: Additional fields
            
        Returns:
            Standardized job dictionary
        """
        job = {
            'title': title,
            'url': url,
            'source': self.name,
            'location': location,
            'job_number': job_number
        }
        
        # Add any additional fields
        job.update(kwargs)
        
        return job
    
    def enrich_with_details(self, jobs: List[Dict]) -> List[Dict]:
        """
        Enrich job listings with details from individual job pages.
        
        Args:
            jobs: List of basic job listings
            
        Returns:
            List of jobs enriched with details
        """
        if not self.fetch_details:
            return jobs
        
        enriched_jobs = []
        for job in jobs:
            try:
                details = self.scrape_job_details(job['url'])
                job.update(details)
                enriched_jobs.append(job)
            except Exception as e:
                logger.error(f"Error fetching details for {job['url']}: {e}")
                job['details_error'] = str(e)
                enriched_jobs.append(job)
        
        return enriched_jobs
