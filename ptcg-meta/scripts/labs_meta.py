import json, os, sys, time, urllib.request
OUT = sys.argv[1]
API = "https://mew.limitlesstcg.com/labs/data/tcg/"
def get(path):
    for i in range(4):
        try:
            with urllib.request.urlopen(API + path, timeout=60) as r:
                return json.loads(r.read())
        except Exception as e:
            time.sleep(2 ** i)
    return None
res = {}
for n in range(1, 80):
    tid = f"{n:04d}"
    d = get(f"tournament?id={tid}&division=MA")
    if not d or not d.get("ok"):
        continue
    res[tid] = d["message"]
    time.sleep(0.2)
json.dump(res, open(os.path.join(OUT, "tournaments.json"), "w"), indent=1)
for tid, m in res.items():
    print(tid, m.get("type"), m.get("city"), m.get("date"), m.get("players"), "decklists=", m.get("decklists"))
