"""Per-list resource features (per game) for the CE regression, across every event.
Usage: python3 -I features.py DATADIR [N_SIMS=300]
Writes DATADIR/out/list_features.csv.gz
"""
import os, sys, time
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cardattrs import load_attrs
from engine_model import sim_list_rows, engine_uses
import model_config as C
D = sys.argv[1]; NS = int(sys.argv[2]) if len(sys.argv) > 2 else 300
P, O = os.path.join(D, "processed"), os.path.join(D, "out")
attrs = load_attrs(D)
ev = pd.read_csv(os.path.join(O, "events_windows.csv"), dtype={"tid": str})
win = dict(zip(ev["tid"], ev["window"]))
pl = pd.read_csv(os.path.join(P, "players.csv"), dtype={"tid": str})
pl = pl[pl["has_list"] == 1].copy()
pl["window"] = pl["tid"].map(win)
pl["uid"] = pl["tid"] + ":" + pl["tp_id"].astype(str)
lc = pd.read_csv(os.path.join(P, "list_cards.csv"), dtype={"tid": str, "number": str})
lc["uid"] = lc["tid"] + ":" + lc["tp_id"].astype(str)
lists = {u: g for u, g in lc.groupby("uid")}
gm = pd.read_csv(os.path.join(O, "player_matches_long.csv.gz"), dtype={"tid": str})
rec = gm.groupby(["tid", "player"])[["w", "l", "t"]].sum()
GROUPS = C.COMPONENT_GROUPS
RAW2G = {raw: g for g, raws in GROUPS.items() for raw in raws}
def add(vec, comp, mult, prefix):
    for k, x in comp.items():
        g = RAW2G.get(k)
        if g is None: continue
        val = x * mult
        if g == "cost": val = abs(val)
        if g in ("damage_100hp", "heal_100hp"): val = val / 100
        vec[f"{prefix}{g}"] = vec.get(f"{prefix}{g}", 0) + val
# opponent context per window (for matchup-dependent triggers)
DRAGON = {"Dragapult ex", "Dreepy", "Drakloak", "N's Zekrom", "N's Reshiram", "Raging Bolt ex", "Kyurem", "Mega Dragonite ex"}
opp = {}
for w, g in pl.groupby("window"):
    us = g["uid"]
    names = {u: set(lists[u]["name"]) for u in us if u in lists}
    def frac(S): return float(np.mean([bool(names[u] & S) for u in names]))
    opp[w] = {"dragon_deck": frac({"Dragapult ex", "N's Zekrom", "Raging Bolt ex"}), "cursed_blast": frac(C.CURSED_BLAST),
              "munkidori": frac(C.COUNTER_MOVERS), "ex_attackers": 0.7}
rng = np.random.default_rng(11)
ENG = set(C.ENGINES)
rows = []
t0 = time.time()
for i, p in enumerate(pl.itertuples()):
    g = lists.get(p.uid)
    if g is None: continue
    vec = {}
    for r in sim_list_rows(g, attrs, rng, ENG, n=NS):
        eng = C.ENGINES[r["name"]]
        u = engine_uses(eng, r, opp[p.window])
        add(vec, eng["value"], u, "eng_")
        vec[f"uses::{r['name']}"] = u
    tr = g[g["cat"] == "trainer"]
    sup_cnt = sum(c for k, c in zip(tr["card_key"], tr["count"]) if attrs.get(k, {}).get("is_supporter"))
    sup_scale = min(1.0, 6.5 / max(sup_cnt * 0.68, 1e-9))
    for k, nm, c in zip(tr["card_key"], tr["name"], tr["count"]):
        comp = C.TRAINER_COMPONENTS.get(nm)
        if not comp: continue
        plays = c * 0.68 * (sup_scale if attrs.get(k, {}).get("is_supporter") else 1.0)
        add(vec, comp, plays, "tr_")
    w, l, t = rec.loc[(p.tid, p.tp_id)] if (p.tid, p.tp_id) in rec.index else (np.nan, np.nan, np.nan)
    rows.append({"uid": p.uid, "tid": p.tid, "tp_id": p.tp_id, "player_id": p.player_id, "deck_id": p.deck_id, "sup_id": p.sup_id,
                 "window": p.window, "day2": p.day2, "topcut": p.topcut, "W": w, "L": l, "T": t, **vec})
    if i % 2000 == 1999:
        print(i + 1, "lists", round(time.time() - t0), "s", flush=True)
F = pd.DataFrame(rows).fillna({c: 0 for c in set().union(*[r.keys() for r in rows]) if c.startswith(("eng_", "tr_", "uses::"))})
for g in GROUPS:
    F[g] = F.get(f"eng_{g}", 0) + F.get(f"tr_{g}", 0)
F.to_csv(os.path.join(O, "list_features.csv.gz"), index=False, compression="gzip")
print("wrote", len(F), "rows;", F[list(GROUPS)].describe().T[["mean", "std"]].round(2).to_string())
