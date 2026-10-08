"""Normalize scraped Labs + JP data into tidy CSV tables.
Usage: python3 -I build_dataset.py DATADIR
Outputs DATADIR/processed/{events,players,list_cards,matches,jp_lists,jp_list_cards,cards}.csv
"""
import csv, json, os, sys, glob, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from carddb import CardDB, BASIC_ENERGY
D = sys.argv[1]
P = os.path.join(D, "processed")
os.makedirs(P, exist_ok=True)
db = CardDB(D)

# set -> first legal date isn't published per event; we infer windows from card presence later.
def card_key(cat, name, setc, num, lang="en"):
    if cat != "pokemon":
        return name
    l = db.lim(setc, num, lang)
    prints = []
    if l:
        for p in l["prints"]["int"]:
            prints.append((p.get("set") or setc, p.get("number") or num) if not p.get("current") else (setc, num))
    if not prints:
        prints = [(setc, num)]
    s, n = sorted(prints)[0]
    return f"{name} [{s} {n}]"

card_meta = {}
def note_card(cat, name, setc, num, lang="en"):
    key = card_key(cat, name, setc, num, lang)
    if key not in card_meta:
        st = db.status(setc, num, name, lang)
        c = db.get(setc, num, lang)
        card_meta[key] = {"card_key": key, "name": name, "cat": cat, "set": setc, "number": num, "lang": lang,
                          "marks": "/".join(st["marks"]), "legal_post": int(st["legal_post"]),
                          "unknown_prints": ";".join(st["unknown"]),
                          "subtypes": ",".join((c or {}).get("subtypes") or []),
                          "supertype": (c or {}).get("supertype", ""),
                          "hp": (c or {}).get("hp", ""), "types": ",".join((c or {}).get("types") or []),
                          "retreat": (c or {}).get("convertedRetreatCost", ""),
                          "jp_prints": ";".join(sorted(set(db.jp_print_sets(setc, num, lang))))}
    return key

events, players, lcards, matches = [], [], [], []
for tdir in sorted(glob.glob(os.path.join(D, "labs", "0*"))):
    tid = os.path.basename(tdir)
    if not os.path.exists(os.path.join(tdir, "decklists.json")):
        continue
    meta = json.load(open(os.path.join(tdir, "tournament.json")))
    st = json.load(open(os.path.join(tdir, "standings.json")))
    decks = {d["identifier"]: d for d in json.load(open(os.path.join(tdir, "decks.json")))}
    lists = json.load(open(os.path.join(tdir, "decklists.json")))
    events.append({"tid": tid, "type": meta["type"], "city": meta["city"], "date": meta["date"],
                   "players": meta["players"], "rounds": meta.get("round"), "n_lists": sum(1 for v in lists.values() if v)})
    for p in st:
        dk = decks.get(p.get("deck_id") or "", {})
        dl = lists.get(str(p["tp_id"]))
        players.append({"tid": tid, "tp_id": p["tp_id"], "name": p["name"], "country": p.get("country"),
                        "placement": p["placement"], "wins": p["wins"], "losses": p["losses"], "ties": p["ties"],
                        "points": p["points"], "day2": p.get("day2") or 0, "topcut": p.get("topcut") or 0,
                        "dropped": p.get("dropped") or 0, "drop_round": p.get("drop_round"),
                        "deck_id": p.get("deck_id"), "deck_name": p.get("deck_name"),
                        "sup_id": dk.get("sup_identifier", p.get("deck_id")), "sup_name": dk.get("sup_name", p.get("deck_name")),
                        "has_list": int(bool(dl))})
        if dl:
            for cat in ("pokemon", "trainer", "energy"):
                for c in dl.get(cat, []):
                    key = note_card(cat, c["name"], c["set"], c["number"])
                    lcards.append({"tid": tid, "tp_id": p["tp_id"], "cat": cat, "card_key": key, "name": c["name"],
                                   "set": c["set"], "number": c["number"], "count": c["count"]})
    pr = json.load(open(os.path.join(tdir, "pairings.json")))
    for rnd, ms in pr.items():
        for m in ms:
            if not m.get("player2"):
                continue
            w = m.get("winner")
            res = "p1" if w == m["player1"] else "p2" if w == m["player2"] else ("tie" if w == 0 else ("dl" if w == -1 else str(w)))
            matches.append({"tid": tid, "round": int(rnd), "table": m.get("table"), "p1": m["player1"], "p2": m["player2"],
                            "p1_deck": m.get("p1_deck"), "p2_deck": m.get("p2_deck"), "result": res,
                            "p1_record": m.get("player1_record"), "p2_record": m.get("player2_record")})

def wcsv(name, rows):
    if not rows: return
    with open(os.path.join(P, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
wcsv("events.csv", events); wcsv("players.csv", players); wcsv("list_cards.csv", lcards); wcsv("matches.csv", matches)

# JP
jl, jc = [], []
for f in sorted(glob.glob(os.path.join(D, "jp", "major_*.json"))):
    d = json.load(open(f))
    for i, l in enumerate(d["lists"]):
        uid = f"major{d['id']}-{i}"
        jl.append({"uid": uid, "event": d["title"].replace(" - Decklists – Limitless", ""), "kind": "major", "date": "",
                   "placing": l["placing"], "player": l["player"], "deck": l["deck"]})
        for c in l["cards"]:
            key = note_card(c["cat"], c["name"], c["set"], c["number"], c["lang"])
            jc.append({"uid": uid, "cat": c["cat"], "card_key": key, "name": c["name"], "set": c["set"], "number": c["number"],
                       "lang": c["lang"], "count": c["count"]})
cl = {}
for f in ("cityleague_lists.json", "cityleague_lists_rev.json"):
    p = os.path.join(D, "jp", f)
    if os.path.exists(p):
        cl.update(json.load(open(p)))
for eid, ev in cl.items():
    for i, e in enumerate(ev["entries"]):
        if not e.get("cards"):
            continue
        uid = f"cl{eid}-{i}"
        jl.append({"uid": uid, "event": ev["title"], "kind": "cityleague", "date": ev["date"], "placing": e["placing"],
                   "player": e["player"], "deck": " ".join(e.get("icons") or []) or e.get("deck")})
        for c in e["cards"]:
            key = note_card(c["cat"], c["name"], c["set"], c["number"], c["lang"])
            jc.append({"uid": uid, "cat": c["cat"], "card_key": key, "name": c["name"], "set": c["set"], "number": c["number"],
                       "lang": c["lang"], "count": c["count"]})
wcsv("jp_lists.csv", jl); wcsv("jp_list_cards.csv", jc)
wcsv("cards.csv", sorted(card_meta.values(), key=lambda r: r["card_key"]))
print("events", len(events), "players", len(players), "list cards", len(lcards), "matches", len(matches),
      "jp lists", len(jl), "cards", len(card_meta))
