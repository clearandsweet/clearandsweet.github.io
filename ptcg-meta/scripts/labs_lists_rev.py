"""Fetch decklists for one Labs event in reverse standings order into decklists_rev.json (helper worker)."""
import json, os, sys, time, threading, urllib.request
from concurrent.futures import ThreadPoolExecutor
D, TID = sys.argv[1], sys.argv[2]
API = "https://mew.limitlesstcg.com/labs/data/tcg/"
def get(path, tries=5):
    for i in range(tries):
        try:
            req = urllib.request.Request(API + path, headers={"User-Agent": "ptcg-meta-research (personal analysis)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read())
            return d["message"] if d.get("ok") else None
        except Exception:
            time.sleep(1.5 * (2 ** i))
    return None
d = os.path.join(D, TID)
st = json.load(open(os.path.join(d, "standings.json")))
out_p = os.path.join(d, "decklists_rev.json")
lists = json.load(open(out_p)) if os.path.exists(out_p) else {}
lock = threading.Lock()
todo = [p for p in reversed(st) if p.get("decklist") and str(p["tp_id"]) not in lists]
def work(p):
    m = get(f"decklist?tournamentId={TID}&playerId={p['tp_id']}")
    time.sleep(0.25)
    with lock:
        lists[str(p["tp_id"])] = m
with ThreadPoolExecutor(4) as ex:
    for i, _ in enumerate(ex.map(work, todo)):
        if i % 100 == 99:
            with lock:
                json.dump(lists, open(out_p + ".tmp", "w")); os.replace(out_p + ".tmp", out_p)
            print(i + 1, flush=True)
json.dump(lists, open(out_p, "w"))
print("done", len(lists))
