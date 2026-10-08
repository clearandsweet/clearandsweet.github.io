"""Resumable, throttled scraper for Limitless Labs tournament data.
Usage: python3 -I labs_scrape.py OUTDIR TID [TID ...]
Writes OUTDIR/<tid>/{standings,decks,pairings,decklists}.json
"""
import json, os, sys, time, threading, urllib.request
from concurrent.futures import ThreadPoolExecutor
API = "https://mew.limitlesstcg.com/labs/data/tcg/"
OUT = sys.argv[1]
TIDS = sys.argv[2:]
lock = threading.Lock()

def get(path, tries=5):
    for i in range(tries):
        try:
            req = urllib.request.Request(API + path, headers={"User-Agent": "ptcg-meta-research (personal analysis)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read())
            if d.get("ok"):
                return d["message"]
            return None
        except Exception as e:
            time.sleep(1.5 * (2 ** i))
    return None

def save(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f)
    os.replace(tmp, path)

for tid in TIDS:
    d = os.path.join(OUT, tid)
    os.makedirs(d, exist_ok=True)
    meta = get(f"tournament?id={tid}&division=MA")
    save(os.path.join(d, "tournament.json"), meta)
    sp = os.path.join(d, "standings.json")
    if not os.path.exists(sp):
        save(sp, get(f"standings?tournamentId={tid}&division=MA"))
    standings = json.load(open(sp))
    dp = os.path.join(d, "decks.json")
    if not os.path.exists(dp):
        save(dp, get(f"decks?tournamentId={tid}&division=MA"))
    pp = os.path.join(d, "pairings.json")
    if not os.path.exists(pp):
        rounds = {}
        for rnd in range(1, (meta.get("round") or 18) + 3):
            m = get(f"pairings?tournamentId={tid}&division=MA&round={rnd}", tries=2)
            if not m:
                if rnd > (meta.get("round") or 0):
                    break
                continue
            rounds[rnd] = m
            time.sleep(0.15)
        save(pp, rounds)
    lp = os.path.join(d, "decklists.json")
    lists = json.load(open(lp)) if os.path.exists(lp) else {}
    todo = [p for p in standings if p.get("decklist") and str(p["tp_id"]) not in lists]
    print(f"{tid}: {len(standings)} players, {len(todo)} lists to fetch", flush=True)
    def work(p):
        m = get(f"decklist?tournamentId={tid}&playerId={p['tp_id']}")
        time.sleep(0.25)
        with lock:
            lists[str(p["tp_id"])] = m
    done = 0
    with ThreadPoolExecutor(4) as ex:
        for i, _ in enumerate(ex.map(work, todo)):
            if i % 200 == 199:
                with lock:
                    save(lp, lists)
                print(f"  {tid}: {i+1}/{len(todo)}", flush=True)
    save(lp, lists)
    print(f"{tid}: done ({len(lists)} lists)", flush=True)
