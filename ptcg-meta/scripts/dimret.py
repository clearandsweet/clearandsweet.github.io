"""Diminishing returns by simulation: expected uses per game of an engine at 1..4 copies, in real lists.
Usage: python3 -I dimret.py DATADIR [LISTS_PER_CARD=40] [N_SIMS=500]
Writes out/engine_copy_curves.csv (card, archetype, copies, uses_per_game, marginal_uses)
"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cardattrs import load_attrs
from engine_model import sim_list_rows, engine_uses
import model_config as C
D = sys.argv[1]; K = int(sys.argv[2]) if len(sys.argv) > 2 else 40; NS = int(sys.argv[3]) if len(sys.argv) > 3 else 500
O, P = os.path.join(D, "out"), os.path.join(D, "processed")
attrs = load_attrs(D)
F = pd.read_csv(os.path.join(O, "list_features.csv.gz"), dtype={"tid": str})
lc = pd.read_csv(os.path.join(P, "list_cards.csv"), dtype={"tid": str, "number": str})
lc["uid"] = lc["tid"] + ":" + lc["tp_id"].astype(str)
lc = lc[lc["uid"].isin(set(F["uid"]))]
LISTS = {u: g[["card_key", "name", "count", "cat"]].reset_index(drop=True) for u, g in lc.groupby("uid")}
deck = F.set_index("uid")["deck_id"]
users = lc.groupby("name")["uid"].unique()
win = dict(zip(F["uid"], F["window"]))
DR = {"Dragapult ex", "N's Zekrom", "Raging Bolt ex"}
opp = {"dragon_deck": 0.3, "cursed_blast": 0.12, "munkidori": 0.4, "ex_attackers": 0.7}
rng = np.random.default_rng(5)
from access_sim import SEARCHERS
PROTECT = set(SEARCHERS) | {"Lillie's Determination", "Judge", "Rare Candy", "Pokégear 3.0", "Boss's Orders"}
rows = []
for name, eng in C.ENGINES.items():
    if name not in users.index or len(users[name]) < 60: continue
    have_u = users[name]
    arch_counts = deck.loc[have_u].value_counts()
    for arch in arch_counts.index[:2]:
        if arch_counts[arch] < 40: continue
        uids = [u for u in have_u if deck.get(u) == arch][:K]
        for k in range(1, 5):
            vals = []
            for u in uids:
                g = LISTS[u].copy()
                key = g.loc[g["name"] == name, "card_key"].iloc[0]
                cur = int(g.loc[g["name"] == name, "count"].sum())
                g = g[g["name"] != name]
                g = pd.concat([g, pd.DataFrame([{"card_key": key, "name": name, "count": k, "cat": "pokemon"}])])
                diff = cur - k
                if diff > 0:
                    g = pd.concat([g, pd.DataFrame([{"card_key": "__filler__", "name": "__filler__", "count": diff, "cat": "trainer"}])])
                elif diff < 0:  # cut copies of the most-played non-search, non-draw Trainer(s) to keep 60
                    need = -diff
                    tr = g[(g["cat"] == "trainer") & ~g["name"].isin(PROTECT)].sort_values("count", ascending=False)
                    for idx in tr.index:
                        take = min(need, int(g.loc[idx, "count"]))
                        g.loc[idx, "count"] -= take; need -= take
                        if need == 0: break
                sims = sim_list_rows(g, attrs, rng, {name}, n=NS)
                r = next((x for x in sims if x["name"] == name), None)
                vals.append(engine_uses(eng, r, opp) if r else 0.0)
            rows.append({"card": name, "archetype": arch, "lists": len(uids), "copies": k, "uses_per_game": float(np.mean(vals))})
    print(name, flush=True)
R = pd.DataFrame(rows)
R["marginal_uses"] = R.groupby(["card", "archetype"])["uses_per_game"].diff().fillna(R["uses_per_game"])
R["uses_per_copy_avg"] = R["uses_per_game"] / R["copies"]
R.to_csv(os.path.join(O, "engine_copy_curves.csv"), index=False)
print(R[R["card"].isin(["Teal Mask Ogerpon ex", "Latias ex", "Drakloak", "Budew", "Munkidori", "Fezandipiti ex"])].round(2).to_string())
