# src/automation/browser_manager.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from src.core.config import Config

class BrowserManager:
    """Gerenciador de navegador com suporte a contexto (with statement)."""
    def __enter__(self):
        options = webdriver.ChromeOptions()
        if Config.CHROME_HEADLESS:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1200,800")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        return self.driver

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, 'driver'):
            self.driver.quit()
