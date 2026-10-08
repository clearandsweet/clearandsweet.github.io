"""For every card flagged as rotating (legal_post=0), fetch marks of its JP prints in Mega-era sets
to see whether Japan already has an I/J/K reprint (=> international reprint likely).
Usage: python3 -I jp_reprint_marks.py DATADIR
"""
import csv, json, os, re, sys, time, urllib.request
D = sys.argv[1]
cache_p = os.path.join(D, "cards", "jp_print_marks.json")
cache = json.load(open(cache_p)) if os.path.exists(cache_p) else {}
lc = json.load(open(os.path.join(D, "cards", "limitless_cache.json")))
rows = list(csv.DictReader(open(os.path.join(D, "processed", "cards.csv"))))
MEGA = re.compile(r"^(M\d|M\d[a-zA-Z]|MA|MBD|MBG|MC|MEE|MEM|MEZ|MF|MP|MP1|M\d+[a-z]?)$")
todo = set()
for r in rows:
    if r["legal_post"] == "1":
        continue
    l = lc.get(f'{"en" if r["lang"]=="en" else "jp"}|{r["set"]}|{r["number"]}')
    if not l:
        continue
    for p in l["prints"]["jp"]:
        if p.get("set") and MEGA.match(p["set"]) and f'{p["set"]}|{p["number"]}' not in cache:
            todo.add((p["set"], p["number"]))
print(len(todo), "jp prints to check", flush=True)
for i, (s, n) in enumerate(sorted(todo)):
    for k in range(4):
        try:
            req = urllib.request.Request(f"https://limitlesstcg.com/cards/jp/{s}/{n}", headers={"User-Agent": "Mozilla/5.0 (ptcg-meta-research)"})
            html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
            m = re.search(r"([A-Z]) Regulation Mark", html)
            cache[f"{s}|{n}"] = m.group(1) if m else None
            break
        except Exception:
            time.sleep(2 ** k)
    time.sleep(0.4)
    if i % 40 == 39:
        json.dump(cache, open(cache_p, "w")); print(i + 1, flush=True)
json.dump(cache, open(cache_p, "w"))
from collections import Counter
print(Counter(cache.values()))
