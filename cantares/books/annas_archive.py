import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin
import random
import time

class AnnasArchiveSearcher:
    # List of mirrors to rotate through. 
    # We prioritize LibGen mirrors as they are more stable for direct scraping than Anna's (Cloudflare).
    MIRRORS = [
        "https://libgen.li",
        "https://libgen.gl",
        "https://libgen.gs",
        "https://libgen.is",
        "https://libgen.rs",
        "https://libgen.st",
        "https://annas-archive.gs",
        "https://annas-archive.se"
    ]

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    ]
    
    def _get_headers(self):
        return {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

    def search(self, query: str):
        """
        Searches for books using fast mirror rotation (5s timeout).
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
        if "annas-archive" in base_url:
            search_url = f"{base_url}/search?q={quote_plus(query)}"
        elif "libgen.li" in base_url or "libgen.gl" in base_url or "libgen.gs" in base_url:
            search_url = f"{base_url}/index.php?req={quote_plus(query)}&columns%5B%5D=t&columns%5B%5D=a&topics%5B%5D=l&res=25"
        else:
            search_url = f"{base_url}/search.php?req={quote_plus(query)}&res=25&view=simple&phrase=1&column=def"
        
        response = requests.get(search_url, headers=self._get_headers(), timeout=6)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "lxml")
        results = []

        if "annas-archive" in base_url:
            # Parse Anna's Archive search links
            for a in soup.find_all("a", href=True):
                if "/md5/" in a["href"]:
                    title = a.get_text(strip=True)
                    if len(title) > 3:
                        results.append({
                            "title": title,
                            "author": "Annas Archive Candidate",
                            "year": "2024",
                            "extension": "pdf",
                            "link": urljoin(base_url, a["href"])
                        })
            return results[:10]

        # LibGen table parser
        table = soup.find("table", {"class": "c"})
        if not table:
            for t in soup.find_all("table"):
                if t.find("tr") and len(t.find_all("tr")) > 1:
                    table = t
                    break
        if not table:
            return []
            
        rows = table.find_all("tr")[1:]
        
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 7:
                continue
                
            author = cols[1].get_text(strip=True) if len(cols) > 1 else "Unknown"
            
            title_tag = cols[2].find("a") if len(cols) > 2 else None
            title = title_tag.get_text(strip=True) if title_tag else cols[2].get_text(strip=True)

            link = ""
            for i in range(min(7, len(cols)), len(cols)):
                a_tag = cols[i].find("a")
                if a_tag and a_tag.has_attr('href') and ('libgen' in a_tag['href'] or 'library.lol' in a_tag['href'] or 'get' in a_tag.get_text().lower()):
                    link = a_tag['href']
                    if not link.startswith("http"):
                        link = urljoin(base_url, link)
                    break
            
            if not link:
                for a_tag in row.find_all("a", href=True):
                    if "ads.php" in a_tag["href"] or "get.php" in a_tag["href"] or "library.lol" in a_tag["href"]:
                        link = a_tag["href"]
                        if not link.startswith("http"):
                            link = urljoin(base_url, link)
                        break

            if not link:
                continue

            year = cols[4].get_text(strip=True) if len(cols) > 4 else ""
            ext = "pdf"
            for col in cols:
                txt = col.get_text(strip=True).lower()
                if txt in ["pdf", "epub", "djvu", "mobi"]:
                    ext = txt
                    break
            
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
        Retries and normalizes relative URLs to absolute.
        """
        headers = self._get_headers()
        try:
            print(f"Resolving download link from: {link}")
            response = requests.get(link, headers=headers, timeout=12)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            
            resolved_url = None
            
            # Strategy 1: "GET" link (library.lol / libgen standard)
            get_link = soup.find("a", string=lambda s: s and "GET" in s.upper())
            if get_link and get_link.has_attr('href'):
                resolved_url = get_link['href']
            
            # Strategy 2: "Cloudflare" link
            if not resolved_url:
                cf_link = soup.find("a", string=lambda s: s and "CLOUDFLARE" in s.upper())
                if cf_link and cf_link.has_attr('href'):
                    resolved_url = cf_link['href']
                
            # Strategy 3: "IPFS.io" link
            if not resolved_url:
                ipfs_link = soup.find("a", string=lambda s: s and "IPFS" in s.upper())
                if ipfs_link and ipfs_link.has_attr('href'):
                    resolved_url = ipfs_link['href']

            # Strategy 4: Generic main download link in #download div
            if not resolved_url:
                download_div = soup.find("div", id="download")
                if download_div:
                    a_tag = download_div.find("a")
                    if a_tag and a_tag.has_attr('href'):
                        resolved_url = a_tag['href']

            # Strategy 5: Any anchor containing 'get.php' or 'key='
            if not resolved_url:
                for a in soup.find_all("a", href=True):
                    if "get.php" in a['href'] or "key=" in a['href']:
                        resolved_url = a['href']
                        break

            if resolved_url:
                if not resolved_url.startswith("http"):
                    resolved_url = urljoin(link, resolved_url)
                return resolved_url

            return None
            
        except Exception as e:
            print(f"Error resolving link: {e}")
            return None
