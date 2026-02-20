"""Selenium helper utilities for scraping JavaScript-rendered pages"""

import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)


def fetch_html_selenium(url: str, wait_time: int = 15) -> str:
    """
    Fetch HTML using Selenium for JavaScript-rendered pages.
    
    Args:
        url: URL to fetch
        wait_time: Initial wait time in seconds for page to load
        
    Returns:
        Page HTML source after JavaScript execution
    """
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
        logger.info(f"Fetching {url} with Selenium...")
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
        logger.info(f"Successfully fetched {url} ({len(html)} bytes)")
        return html
        
    finally:
        driver.quit()
