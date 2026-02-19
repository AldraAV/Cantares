import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin
import random
import time

class AnnasArchiveSearcher:
    # List of mirrors to rotate through. 
    # We prioritize LibGen mirrors as they are more stable for direct scraping than Anna's (Cloudflare).
    MIRRORS = [
        "https://libgen.is",
        "https://libgen.rs",
        "https://libgen.st",
        "https://libgen.li", 
        # "https://annas-archive.org" # Kept as last resort due to Cloudflare
    ]

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
    ]
    
    def _get_headers(self):
        return {
            "User-Agent": random.choice(self.USER_AGENTS)
        }

    def search(self, query: str):
        """
        Searches for books using mirror rotation.
        Returns a list of dictionaries with metadata.
        """
        for mirror in self.MIRRORS:
            print(f"Trying mirror: {mirror}...")
            try:
                results = self._search_mirror(mirror, query)
                if results:
                    return results
            except Exception as e:
                print(f"Mirror {mirror} failed: {e}")
                continue
        
        print("All mirrors failed.")
        return []

    def _search_mirror(self, base_url: str, query: str):
        # LibGen Scraping logic (Standardized for .is/.rs/.st)
        search_url = f"{base_url}/search.php?req={quote_plus(query)}&res=25&view=simple&phrase=1&column=def"
        
        response = requests.get(search_url, headers=self._get_headers(), timeout=15)
        response.raise_for_status()
        
        # Check if we got a valid response or a block/captcha
        if "To download the file please" in response.text:
             # Direct download page? Unlikely for search.
             pass

        soup = BeautifulSoup(response.text, "lxml")
        
        results = []
        # LibGen generic table parser
        table = soup.find("table", {"class": "c"})
        if not table:
            # Maybe it's libgen.li which has a slightly different layout sometimes?
            # Or just no results.
            return []
            
        rows = table.find_all("tr")[1:] # Skip header
        
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 9:
                continue
                
            # Parsers for LibGen columns
            # Col 0: ID
            # Col 1: Authors
            author = cols[1].get_text(strip=True)
            
            # Col 2: Title (links to md5 or details)
            title_tag = cols[2].find("a")
            if not title_tag:
                 # sometimes title is just text or inside font tag
                 title = cols[2].get_text(strip=True)
                 # We need a link to the details page at least
                 # Usually the [1] link in mirrors column is the download page
            else:
                title = title_tag.get_text(strip=True)

            # Col 9+: Mirrors. usually [1] is library.lol or similar
            # We want the first valid mirror link.
            # LibGen columns for mirrors start at index 9.
            # 9: Mirror 1 (usually libgen.lc or library.lol)
            # 10: Mirror 2 (usually libgen.li)
            # 11: Mirror 3 (usually z-lib/b-ok - often dead or auth wall)
            
            link = ""
            for i in range(9, min(14, len(cols))):
                a_tag = cols[i].find("a")
                if a_tag and a_tag.has_attr('href'):
                    link = a_tag['href']
                    break
            
            if not link:
                continue

            # Col 4: Year
            year = cols[4].get_text(strip=True)
            # Col 8: Extension
            ext = cols[8].get_text(strip=True)
            
            results.append({
                "title": title,
                "author": author,
                "year": year,
                "extension": ext,
                "link": link 
            })
            
        return results

    def get_download_link(self, link: str) -> str:
        """
        Resolves the final direct download link from the gateway page.
        Retries if necessary.
        """
        headers = self._get_headers()
        try:
            print(f"Resolving download link from: {link}")
            response = requests.get(link, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            
            # Strategy 1: "GET" link (library.lol standard)
            get_link = soup.find("a", string="GET")
            if get_link:
                return get_link['href']
            
            # Strategy 2: "Cloudflare" link
            cf_link = soup.find("a", string="Cloudflare")
            if cf_link:
                return cf_link['href']
                
            # Strategy 3: "IPFS.io" link
            ipfs_link = soup.find("a", string="IPFS.io")
            if ipfs_link:
                return ipfs_link['href']

            # Strategy 4: Generic main download link in #download div
            download_div = soup.find("div", id="download")
            if download_div:
                a_tag = download_div.find("a")
                if a_tag:
                    return a_tag['href']

            return None
            
        except Exception as e:
            print(f"Error resolving link: {e}")
            return None
