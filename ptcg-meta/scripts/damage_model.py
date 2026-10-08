"""Damage value of attackers vs the meta-weighted defender pool.
Usage: python3 -I damage_model.py DATADIR [WINDOW=CUR]
"""
import os, sys, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from carddb import CardDB
import model_config as C
D = sys.argv[1]; WIN = sys.argv[2] if len(sys.argv) > 2 else "CUR"
O, P = os.path.join(D, "out"), os.path.join(D, "processed")
db = CardDB(D)
ac = pd.read_csv(os.path.join(O, f"archetype_cards_{WIN}.csv"))
arch = pd.read_csv(os.path.join(O, f"archetypes_{WIN}.csv")).set_index("deck_id")
share = arch["share"]
# card facts by name (prefer the most recent legal print)
facts = {}
for (s, n), c in db.by_key.items():
    if c.get("supertype", "").startswith("Pok") and c.get("regulationMark") in ("H", "I", "J"):
        nm = c["name"]
        if nm in facts and facts[nm]["mark"] >= c["regulationMark"]:
            continue
        subs = c.get("subtypes") or []
        facts[nm] = {"hp": int(c["hp"]), "types": c.get("types") or [], "mark": c["regulationMark"],
                     "weak": [w["type"] for w in c.get("weaknesses") or []], "res": [r["type"] for r in c.get("resistances") or []],
                     "prizes": 3 if "MEGA" in subs else 2 if "ex" in subs else 1, "dragon": "Dragon" in (c.get("types") or [])}
import glob
icons = {}
for f in glob.glob(os.path.join(D, "labs", "*", "decks.json")):
    for dk in json.load(open(f)):
        icons[dk["identifier"]] = (dk.get("icons") or "").split()
def icon_match(name, ic):
    base = ic.replace("-mega", "").replace("-alola", "").replace("-galar", "").split("-")[0]
    return base in name.lower().replace("'", "")
# main defender of each archetype = its highest-usage ATTACKERS entry (fallback: highest HP Pokémon with >=2 copies)
defenders = []
for d, sh in share.items():
    x = ac[(ac["deck_id"] == d) & (ac["cat"] == "pokemon")]
    cand = x[x["name"].isin(C.ATTACKERS) & x["name"].isin(facts) & (x["avg_copies_per_list"] >= 1.0)].copy()
    ic = icons.get(d, [])
    if len(cand):
        cand["w"] = cand["avg_copies_per_list"] * cand["name"].map(lambda n: C.ATTACKERS[n]["cadence"])
        cand.loc[cand["name"].map(lambda n: any(icon_match(n, i) for i in ic[:1])), "w"] *= 2
        cand["w"] /= cand["w"].sum()
        for _, c in cand.iterrows():
            defenders.append({"deck_id": d, "defender": c["name"], "share": sh * c["w"], **facts[c["name"]]})
    else:
        x = x[x["name"].isin(facts) & (x["avg_copies_per_list"] >= 1.5)]
        if not len(x): continue
        nm = max(x["name"], key=lambda n: facts[n]["hp"])
        defenders.append({"deck_id": d, "defender": nm, "share": sh, **facts[nm]})
DF = pd.DataFrame(defenders)
DF["share"] = DF["share"] / DF["share"].sum()
hp_per_prize = float((DF["share"] * DF["hp"] / DF["prizes"]).sum())
DF.to_csv(os.path.join(O, f"defender_pool_{WIN}.csv"), index=False)

alive = np.array(C.P_ALIVE)
rows = []
for nm, a in C.ATTACKERS.items():
    if nm not in facts: continue
    eff, ohko, prog = [], [], []
    for _, d in DF.iterrows():
        dmg = a["dmg"]
        if a.get("vs_ex_only") and d["prizes"] == 1: dmg = 20
        mult = 1.0
        if not a.get("ignore_wr"):
            if a["type"] in d["weak"] or (a.get("fairy_zone") and d["dragon"]): mult = 2.0
        e = dmg * mult - (30 if (not a.get("ignore_wr") and a["type"] in d["res"]) else 0)
        if nm == "Crustle" and False: pass
        eff.append(e); ohko.append(float(e >= d["hp"])); prog.append(min(1.0, e / d["hp"]) * d["prizes"])
    w = DF["share"].values
    e_dmg = float(np.dot(w, eff)); p_ohko = float(np.dot(w, ohko)); prize_per_attack = float(np.dot(w, prog))
    prize_per_attack += a.get("spread", 0) / hp_per_prize * 0.65    # bench damage converts worse (overkill / unfinished targets)
    first = a["first"]
    turns = np.arange(1, 11)
    att = np.where(turns >= first, a["cadence"], 0.0); att[turns == np.ceil(first)] *= (np.ceil(first) - first + 0.5)
    attacks = float((alive * att).sum())
    rows.append({"attacker": nm, "type": a["type"], "hp": facts[nm]["hp"], "prize_liability": facts[nm]["prizes"],
                 "legal_post_rotation": int(facts[nm]["mark"] in ("I", "J", "K")), "base_assumption": a["note"],
                 "exp_damage_vs_meta": e_dmg, "p_OHKO_meta_defender": p_ohko, "spread_per_attack": a.get("spread", 0),
                 "prizes_per_attack": prize_per_attack, "first_attack_turn": first, "attacks_per_game": attacks,
                 "prizes_per_game": prize_per_attack * attacks,
                 "damage_value_ce_per_game": prize_per_attack * attacks * C.PRIZE_TO_CE,
                 "prize_efficiency": prize_per_attack / facts[nm]["prizes"]})
R = pd.DataFrame(rows)
inc = pd.read_csv(os.path.join(O, f"card_inventory_{WIN}.csv")).groupby("name")["inclusion"].max()
R["field_inclusion"] = R["attacker"].map(inc).fillna(0)
R.sort_values("prizes_per_attack", ascending=False).to_csv(os.path.join(O, f"damage_value_{WIN}.csv"), index=False)
json.dump({"hp_per_prize_meta": hp_per_prize}, open(os.path.join(O, f"damage_meta_{WIN}.json"), "w"))
print("meta HP per prize:", round(hp_per_prize, 1))
print(DF.sort_values("share", ascending=False).head(15)[["deck_id", "defender", "hp", "prizes", "weak", "share"]].to_string())
print(R.sort_values("prizes_per_attack", ascending=False).round(3)[["attacker", "exp_damage_vs_meta", "p_OHKO_meta_defender", "prizes_per_attack", "attacks_per_game", "prizes_per_game", "prize_efficiency", "legal_post_rotation"]].to_string())
