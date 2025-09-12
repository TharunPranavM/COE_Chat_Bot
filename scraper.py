from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

def scrape_websites(urls):
    options = Options()
    options.headless = True
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    texts = []
    for url in urls:
        try:
            driver.get(url)
            time.sleep(2)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            text = ' '.join([p.text for p in soup.find_all('p')])
            texts.append(text)
        except Exception as e:
            print(f"Error scraping {url}: {e}")
    
    driver.quit()
    return texts