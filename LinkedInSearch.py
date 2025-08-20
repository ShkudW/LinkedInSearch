import os, re, json, argparse, time
from typing import Iterable, List, Dict, Set, Tuple
import requests

SERPER_ENDPOINT = "https://google.serper.dev/search"

LINKEDIN_PROFILE_RX = re.compile(r"https?://([\w\-]+\.)?linkedin\.com/(in|pub)/", re.I)

NON_NAME_TOKENS = set("""
ltd limited inc corporation corp gmbh srl bv spa plc llc co company
technologies technology software systems labs group holdings
""".split())

LETTER_RX = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ'\-]+$")


def build_queries(query: str) -> List[str]:

    q = query.strip().strip('"').strip("'")
    is_domain = "." in q and " " not in q

    if is_domain:
        base = q.lower()

        return [
            f'site:linkedin.com/in ("{base}" OR @{base}) -jobs -hiring',
            f'site:linkedin.com/in "{base}" ("security" OR "engineer" OR "researcher" OR "developer" OR "sales" OR "marketing") -jobs -hiring',
            f'site:linkedin.com/pub "{base}" -jobs -hiring',
        ]
    else:
        company = q
        return [
            f'site:linkedin.com/in "{company}" -jobs -hiring',
            f'site:linkedin.com/in "{company}" ("security" OR "engineer" OR "researcher" OR "developer" OR "sales" OR "marketing") -jobs -hiring',
            f'"{company}" site:linkedin.com/in ("our team" OR "leadership" OR "product" OR "design" OR "operations") -jobs -hiring',
            f'site:linkedin.com/pub "{company}" -jobs -hiring',
        ]


def serper_search(api_key: str, q: str, page: int = 1, num: int = 10, gl: str = None, hl: str = "en") -> Dict:
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": q, "page": page, "num": num}
    if gl: payload["gl"] = gl.lower()
    if hl: payload["hl"] = hl
    r = requests.post(SERPER_ENDPOINT, headers=headers, data=json.dumps(payload), timeout=30)
    r.raise_for_status()
    return r.json()


def clean_name_candidate(text: str) -> List[str]:

    if not text:
        return []

    t = text.split(" | ")[0]
    t = t.split("—")[0]
    t = t.split(" - ")[0]
    t = t.strip()


    t = t.replace(",", " ")

    tokens = [tok for tok in t.split() if tok]

    name_like = [tok for tok in tokens if LETTER_RX.match(tok) and tok.lower() not in NON_NAME_TOKENS]


    name_like = [tok for tok in name_like if not (len(tok) >= 2 and tok.isupper())]


    common_roles = {"engineer","developer","researcher","manager","director","head","lead","vp","intern",
                    "student","consultant","owner","founder","co-founder","cto","ceo","cfo","ciso",
                    "marketing","sales","product","design","security","analyst","administrator"}
    if name_like and name_like[0].lower() in common_roles and len(name_like) >= 3:
        name_like = name_like[1:]

    return name_like[:3]


def extract_first_last(title: str) -> Tuple[str, str]:
    toks = clean_name_candidate(title)
    if len(toks) >= 2:
        first = toks[0].capitalize()
        last  = toks[-1].capitalize()
        if 2 <= len(first) <= 30 and 2 <= len(last) <= 40:
            return first, last
    return ("", "")


def gather_names_from_serp(serp: Dict) -> Iterable[Tuple[str, str]]:
    for it in serp.get("organic", []):
        link = (it.get("link") or "").strip()
        title = (it.get("title") or "").strip()

        if not link or not title:
            continue
        if not LINKEDIN_PROFILE_RX.search(link):
            continue

        first, last = extract_first_last(title)
        if first and last:
            yield (first, last)


def run(query: str, pages: int, per_page: int, gl: str, hl: str, delay: float) -> List[Tuple[str, str]]:
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        raise SystemExit("[-] SERPER_API_KEY not in env")

    qlist = build_queries(query)
    seen: Set[Tuple[str, str]] = set()
    results: List[Tuple[str, str]] = []

    for q in qlist:
        for page in range(1, pages + 1):
            try:
                data = serper_search(api_key, q=q, page=page, num=per_page, gl=gl, hl=hl)
            except requests.HTTPError as e:
                code = getattr(e.response, "status_code", "?")
                print(f"[!] HTTP {code} on query='{q}' page={page}")
                break 
            except Exception as e:
                print(f"[!] Error on query='{q}' page={page}: {e}")
                break

            names = list(gather_names_from_serp(data))
            if not names:
           
                break

            for pair in names:
                if pair not in seen:
                    seen.add(pair)
                    results.append(pair)

            time.sleep(delay)

    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-q", "--query", required=True, help="Domain Name")
    ap.add_argument("--pages", type=int, default=5, help="Number of Pages")
    ap.add_argument("--per-page", type=int, default=20, help="Number of results")
    ap.add_argument("--gl", default="", help="Country")
    ap.add_argument("--hl", default="en", help="Lang")
    ap.add_argument("--delay", type=float, default=0.7, help="Delay")
    args = ap.parse_args()

    names = run(args.query, args.pages, args.per_page, args.gl, args.hl, args.delay)


    print(f"\[+]{len(names)} unique names found for '{args.query}':\n")
    for first, last in sorted(names, key=lambda x: (x[1].lower(), x[0].lower())):
        print(f"{first} {last}")


if __name__ == "__main__":
    main()
