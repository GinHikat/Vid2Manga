import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Get absolute path to chromedriver.exe relative to this script
script_dir = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DRIVER_PATH = os.path.join(script_dir, 'chromedriver.exe')

class YoutubeCrawler:
    """Class for crawling Youtube content using Selenium."""
    def __init__(self, driver_path=DEFAULT_DRIVER_PATH):
        self.service = Service(executable_path=driver_path)
        self.driver = None

    def start(self):
        self.driver = webdriver.Chrome(service=self.service)

    def search_and_click(self, query, aria_label_contains=None):
        """Searches for a query and clicks the first matching video."""
        if not self.driver: self.start()
        self.driver.get('https://www.youtube.com')
        
        wait = WebDriverWait(self.driver, 15)
        search_box = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "ytSearchboxComponentInput")))
        search_box.clear()
        search_box.send_keys(query + Keys.ENTER)

        xpath = "//a[@id='video-title']"
        if aria_label_contains:
            xpath += f"[contains(@aria-label, '{aria_label_contains}')]"
            
        video = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        video.click()
        time.sleep(5)

    def close(self):
        if self.driver:
            self.driver.quit()

if __name__ == "__main__":
    crawler = YoutubeCrawler()
    try:
        crawler.search_and_click('Lamoon', 'LAMOON')
    finally:
        crawler.close()
