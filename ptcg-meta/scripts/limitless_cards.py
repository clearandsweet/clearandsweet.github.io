"""Fetch Limitless card pages for every (set, number) seen in scraped lists; cache prints + mark.
Usage: python3 -I limitless_cards.py DATADIR
"""
import json, os, re, sys, time, html, glob, urllib.request
D = sys.argv[1]
CACHE = os.path.join(D, "cards", "limitless_cache.json")
cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
def get(path):
    for i in range(5):
        try:
            req = urllib.request.Request("https://limitlesstcg.com" + path, headers={"User-Agent": "Mozilla/5.0 (ptcg-meta-research)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            time.sleep(2 * (2 ** i))
    return ""
def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()
def parse(s):
    out = {}
    m = re.search(r"([A-Z]) Regulation Mark", s)
    out["mark"] = m.group(1) if m else None
    m = re.search(r'<span class="card-text-name">(.*?)</span>', s, re.S)
    out["name"] = text(m.group(1)) if m else None
    m = re.search(r'<p class="card-text-type">(.*?)</p>', s, re.S)
    out["type_line"] = text(m.group(1)) if m else None
    sec = re.findall(r'<div class="card-text-section">(.*?)</div>\s*(?=<div class="card-text-section">|</div>)', s, re.S)
    out["text"] = [text(x) for x in sec]
    prints = {"int": [], "jp": []}
    m = re.search(r'<table class="card-prints-versions">(.*?)</table>', s, re.S)
    kind = "int"
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", m.group(1) if m else "", re.S):
        if "JP. Prints" in row:
            kind = "jp"; continue
        if "<th" in row or "jp-print-toggle" in row:
            continue
        href = re.search(r'href="/cards/(?:jp/)?([^/"]+)/([^"/]+)"', row)
        if href:
            prints[kind].append({"set": href.group(1), "number": href.group(2)})
        else:
            num = re.search(r'#(\S+?)<', row)
            prints[kind].append({"current": True, "setname": text(row.split("<span")[0]), "number": num.group(1) if num else None})
    out["prints"] = prints
    return out
def seen_cards():
    keys = set()
    for f in glob.glob(os.path.join(D, "labs", "*", "decklists.json")):
        for dl in json.load(open(f)).values():
            if not dl: continue
            for cat in ("pokemon", "trainer", "energy"):
                for c in dl.get(cat, []):
                    keys.add(("en", c["set"], c["number"]))
    for f in glob.glob(os.path.join(D, "jp", "major_*.json")):
        for l in json.load(open(f))["lists"]:
            for c in l["cards"]:
                keys.add((c["lang"], c["set"], c["number"]))
    f = os.path.join(D, "jp", "cityleague_lists.json")
    if os.path.exists(f):
        for ev in json.load(open(f)).values():
            for e in ev["entries"]:
                for c in e.get("cards", []):
                    keys.add((c["lang"], c["set"], c["number"]))
    return keys
EN_CODES = set(json.load(open(os.path.join(D, "cards", "en_codes.json"))))
keys = sorted(("en" if st in EN_CODES else "jp", st, num) for _, st, num in seen_cards())
todo = [k for k in keys if "|".join(k) not in cache]
print(len(keys), "cards seen;", len(todo), "to fetch", flush=True)
import threading
from concurrent.futures import ThreadPoolExecutor
lock = threading.Lock()
def work(k):
    lang, st, num = k
    path = f"/cards/{st}/{num}" if lang == "en" else f"/cards/jp/{st}/{num}?translate=en"
    s = get(path)
    with lock:
        cache["|".join(k)] = parse(s) if s else None
    time.sleep(0.4)
with ThreadPoolExecutor(3) as ex:
    for i, _ in enumerate(ex.map(work, todo)):
        if i % 50 == 49:
            with lock:
                json.dump(cache, open(CACHE, "w"))
            print(i + 1, flush=True)
json.dump(cache, open(CACHE, "w"))
print("done", len(cache))
