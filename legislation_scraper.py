import requests
import random
import time
from bs4 import BeautifulSoup

class EmploymentLawScraper:
    def __init__(self, base_url="https://www.legislation.gov.uk/uksi?theme=employment-law"):
        self.base_url = base_url
        self.xml_urls = []

    def fetch_page(self, url):
        """Fetch HTML content for a given page URL."""
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        else:
            raise Exception(f"Failed to fetch page: {response.status_code}")

    def extract_xml_urls(self, html):
        """Extract legislation URLs and append /data.xml."""
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a_tag in soup.select("a[href^='/uksi/']"):
            href = a_tag.get("href")
            if href and href.startswith("/uksi/"):
                # Remove '/contents' if it exists
                href = href.replace("/contents", "")
                full_url = "https://www.legislation.gov.uk" + href
                xml_url = full_url.rstrip("/") + "/data.xml"
                links.append(xml_url)
        return links

    def get_next_page(self, soup):
        next_link = soup.select_one("ul.pagination li.next a") or soup.select_one("a[rel='next']")
        if next_link:
            href = next_link.get("href")
            # If href is absolute, use it directly
            if href.startswith("http"):
                return href
            else:
                return "https://www.legislation.gov.uk" + href
        return None

    def run(self):
        """Scrape all pages and collect XML URLs."""
        current_page = self.base_url
        while current_page:
            html = self.fetch_page(current_page)
            soup = BeautifulSoup(html, "html.parser")
            page_links = self.extract_xml_urls(html)
            self.xml_urls.extend(page_links)
            current_page = self.get_next_page(soup)  # move to next page if exists
            time.sleep(random.uniform(1, 3))

        # Deduplicate
        self.xml_urls = list(set(self.xml_urls))
        print(f"Found {len(self.xml_urls)} legislation XML URLs.")
        return self.xml_urls

    def save_to_file(self, filename="employment_law_xml_urls.txt"):
        """Save the list of XML URLs to a file."""
        if not self.xml_urls:
            raise Exception("No URLs to save. Run .run() first.")
        with open(filename, "w") as f:
            for url in self.xml_urls:
                f.write(url + "\n")
        print(f"Saved {len(self.xml_urls)} URLs to {filename}")


# Usage
if __name__ == "__main__":
    scraper = EmploymentLawScraper()
    urls = scraper.run()
    scraper.save_to_file()