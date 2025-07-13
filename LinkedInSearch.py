import httpx
import re
import sys
import brotli
import json
import argparse
from urllib.parse import quote_plus, unquote


parser = argparse.ArgumentParser(description="Search LinkedIn profiles by company name")
parser.add_argument("-Name", required=True, help="The company name to search for")
args = parser.parse_args()

company = args.Name.strip()
query = f"site:linkedin.com/in {company}"



HEADERS1 = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

HEADERS2 = {
    "Host": "links.duckduckgo.com",
    "User-Agent": HEADERS1["User-Agent"],
    "Accept": "*/*",
    "Accept-Language": HEADERS1["Accept-Language"],
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://duckduckgo.com/",
    "Sec-Ch-Ua": '"Chromium";v="137", "Not/A)Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Site": "same-site",
    "Sec-Fetch-Mode": "no-cors",
    "Sec-Fetch-Dest": "script",
    "Priority": "u=1",
}

def extract_profiles(js_text):
    names = set()
    urls = set()
    next_page = None

    
    m1 = re.search(
        r"DDG\.inject\('DDG\.Data\.languages\.resultLanguages',\s*(\{.+?\})\);",
        js_text
    )
    if m1:
        try:
            data = json.loads(m1.group(1))
            for u in data.get("en", []):
                if "linkedin.com/in/" in u:
                    urls.add(u)
        except Exception:
            pass

    
    for u, t in re.findall(
        r'"u":"(https?://[^\"]+?)".+?"t":"(.*?)"', 
        js_text
    ):
        if "linkedin.com/in/" in u:
            urls.add(u)
            name = unquote(t.split(" -")[0])
            names.add(name)

    
    m3 = re.search(r'"n"\s*:\s*"([^"]+)"', js_text)
    if m3:
        next_page = "https://links.duckduckgo.com" + m3.group(1)
        

    return names, urls, next_page

def fetch_deep_script(client, deep_url):
    r = client.get(deep_url, headers=HEADERS2)
    r.raise_for_status()
    content = r.content
    try:
        return brotli.decompress(content).decode('utf-8')
    except brotli.error:
        return content.decode(r.encoding or 'utf-8', errors='ignore')

def main():
    encoded_q = quote_plus(query)
    url1 = f"https://duckduckgo.com/?t=h_&q={encoded_q}"

    all_names = set()
    all_urls = set()
    deep_url = None

    with httpx.Client(http2=True, timeout=20) as client:
     
        r1 = client.get(url1, headers=HEADERS1)
        r1.raise_for_status()
        m = re.search(
            r'<link\s+id="deep_preload_link"[^>]*href="([^"]+)"',
            r1.text
        )
        if not m:
            print("Not Found deep_preload_link", file=sys.stderr)
            sys.exit(1)
        deep_url = m.group(1)


        while deep_url:
            
            js = fetch_deep_script(client, deep_url)
            names, urls, next_page = extract_profiles(js)

            all_names.update(names)
            all_urls.update(urls)

            if not next_page or (not names and not urls):
                break
            deep_url = next_page

    print("\n===== Profiles found =====")
    for name, url in zip(sorted(all_names), sorted(all_urls)):
        print(f"{name}: {url}")

if __name__ == "__main__":
    main()
