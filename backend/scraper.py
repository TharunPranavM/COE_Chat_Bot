# scraper.py
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

class KprietScraper:
    def __init__(self, base_url="https://www.kpriet.ac.in", max_pages=50, headless=True):
        self.base_url = base_url.rstrip("/")
        self.visited = set()
        self.to_visit = [self.base_url]
        self.max_pages = max_pages

        options = Options()
        if headless:
            options.add_argument("--headless=new")  # Chrome 109+
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def _get_links(self, soup):
        links = []
        domain = urlparse(self.base_url).netloc
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            full_url = urljoin(self.base_url, href).split("#")[0]  # remove anchors
            if urlparse(full_url).netloc != domain:
                continue
            if full_url not in self.visited and full_url not in self.to_visit:
                links.append(full_url)
        return links

    def _extract_text(self, soup):
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.decompose()
        texts = []
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "p", "li", "td", "th", "span", "div"]):
            txt = tag.get_text(separator=" ", strip=True)
            if txt and len(txt) > 10:  # skip tiny fragments
                texts.append(txt)
        return " ".join(texts)

    def scrape(self):
        all_text = ""
        page_count = 0
        print(f"[CRAWLER] Starting crawl from {self.base_url} (max {self.max_pages} pages)")

        while self.to_visit and page_count < self.max_pages:
            url = self.to_visit.pop(0)
            if url in self.visited:
                continue

            try:
                self.driver.get(url)
                time.sleep(2)
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                page_text = self._extract_text(soup)

                if page_text.strip():
                    all_text += page_text + "\n\n"
                    page_count += 1

                self.visited.add(url)
                new_links = self._get_links(soup)
                self.to_visit.extend(new_links[:20])  # limit branching
                print(f"  Scraped: {url} ({page_count}/{self.max_pages})")

            except Exception as e:
                print(f"  Error: {url} → {e}")
                continue

        self.driver.quit()
        print(f"[CRAWLER] Done. Scraped {page_count} pages from {self.base_url}")
        return all_text


# COMPATIBILITY WRAPPER — REQUIRED BY app.py & initializer.py
def scrape_websites(urls):
    """
    Crawl multiple base URLs (from SCRAPE_LINKS) and return list of full texts.
    """
    all_texts = []
    for url in [u.strip() for u in urls if u.strip()]:
        print(f"\nStarting crawl for: {url}")
        try:
            crawler = KprietScraper(base_url=url, max_pages=40, headless=True)
            text = crawler.scrape()
            if text.strip():
                all_texts.append(text)
        except Exception as e:
            print(f"Failed to crawl {url}: {e}")
    return all_texts