"""Job scrapers module"""

from .base_scraper import BaseScraper
from .titan import TitanScraper
from .npnow import NPNowScraper

__all__ = ['BaseScraper', 'TitanScraper', 'NPNowScraper']
