"""Rotation deep-dive: rotating staples, functional replacements in the I/J/K pool, archetype survivability.
Usage: python3 -I rotation_analysis.py DATADIR [WINDOW=CUR]
"""
import os, sys, re, json, glob
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from carddb import CardDB
D = sys.argv[1]; WIN = sys.argv[2] if len(sys.argv) > 2 else "CUR"
O = os.path.join(D, "out")
db = CardDB(D)
inv = pd.read_csv(os.path.join(O, f"card_inventory_{WIN}.csv"))
rot = pd.read_csv(os.path.join(O, f"rotation_by_archetype_{WIN}.csv"))
ac = pd.read_csv(os.path.join(O, f"archetype_cards_{WIN}.csv"))
arch = pd.read_csv(os.path.join(O, f"archetypes_{WIN}.csv"))

# functional tags from rules text
TAGS = [
    ("draw", r"\bdraw (\d+|a) card|draw cards until"),
    ("search_pokemon", r"search your deck for (up to \d+ )?(a |an )?(Basic |Evolution |Stage \d |)?(\w+ )?Pokémon"),
    ("bench_from_deck", r"put (them|it) onto your Bench"),
    ("search_trainer", r"search your deck for (a|an|up to \d) (Trainer|Item|Supporter|Stadium|Pokémon Tool)"),
    ("search_energy", r"search your deck for .*Energy"),
    ("recover", r"from your discard pile into your hand|from your discard pile .* into your deck"),
    ("gust", r"Switch in 1 of your opponent's Benched Pokémon"),
    ("switch", r"Switch your Active Pokémon with 1 of your Benched"),
    ("accel_discard", r"attach .*Energy.* from your discard pile"),
    ("accel_deck", r"search your deck for .*Energy.* attach|attach .*Energy.* from your deck"),
    ("heal", r"\bheal\b"),
    ("hand_disruption", r"shuffles? (their|his or her) hand|discards? cards from their hand|reveals their hand"),
    ("energy_removal", r"discard an Energy from|discard a Special Energy"),
    ("damage_boost", r"do \d+ more damage"),
    ("hp_boost", r"gets \+\d+ HP"),
    ("retreat", r"Retreat Cost"),
]
def tags_for(c):
    txt = " ".join((c.get("rules") or []) + [a.get("text", "") for a in (c.get("abilities") or []) + (c.get("attacks") or [])])
    return [t for t, pat in TAGS if re.search(pat, txt, re.I)]
# legal-after-rotation trainer pool (I/J marks) from the card database (+ anything legal_post in data)
pool = {}
for (s, n), c in db.by_key.items():
    if c.get("supertype") == "Trainer" and c.get("regulationMark") in ("I", "J", "K"):
        pool.setdefault(c["name"], {"name": c["name"], "subtypes": ",".join(c.get("subtypes") or []), "tags": tags_for(c),
                                    "text": " ".join(r for r in c.get("rules") or [] if not r.startswith("You may play"))[:220]})
usage = inv.groupby("name")["inclusion"].max()
rows = []
rot_tr = inv[(inv["legal_post"] == 0) & (inv["cat"] != "pokemon") & (inv["inclusion"] >= 0.01)]
for _, r in rot_tr.iterrows():
    c = db.get(r["set"], str(r["number"]))
    if not c: continue
    t = set(tags_for(c)); sub = set(c.get("subtypes") or [])
    cands = []
    for nm, p in pool.items():
        if nm == r["name"]: continue
        ov = len(t & set(p["tags"]))
        same_type = bool(sub & set(p["subtypes"].split(",")))
        if ov and same_type:
            cands.append((ov + 0.5 * same_type + 2 * usage.get(nm, 0), nm, usage.get(nm, 0)))
    cands.sort(reverse=True)
    rows.append({"rotating_card": r["name"], "type": ",".join(sorted(sub - {"Trainer"})), "inclusion_now": r["inclusion"],
                 "avg_copies": r["avg_copies"], "day2_inclusion": r["inclusion_day2"], "function_tags": ",".join(sorted(t)),
                 "legal_alternatives": "; ".join(f"{nm} ({u:.0%} now)" for _, nm, u in cands[:4]) or "none found in I/J pool"})
R = pd.DataFrame(rows).sort_values("inclusion_now", ascending=False)
R.to_csv(os.path.join(O, f"rotation_replacements_{WIN}.csv"), index=False)

# archetype survivability
icons = {}
for f in glob.glob(os.path.join(D, "labs", "*", "decks.json")):
    for dk in json.load(open(f)):
        icons[dk["identifier"]] = (dk.get("icons") or "").split()
def icon_match(name, ic):
    base = ic.replace("-mega", "").replace("-alola", "").split("-")[0]
    return base in name.lower().replace("'", "")
surv = []
for _, a in arch.iterrows():
    d = a["deck_id"]
    x = ac[(ac["deck_id"] == d) & (ac["cat"] == "pokemon")]
    ic = icons.get(d, [])
    mask = np.array([any(icon_match(n, i) for i in ic) for n in x["name"]], dtype=bool)
    named = x[mask].sort_values("avg_copies_per_list", ascending=False) if len(x) else x
    namesake = named.drop_duplicates("name").head(2)
    ns_rot = [r["name"] for _, r in namesake.iterrows() if r["legal_post"] == 0 and r["avg_copies_per_list"] >= 1]
    rr = rot[rot["deck_id"] == d]
    rc = float(rr["rot_copies"].iloc[0]) if len(rr) else np.nan
    core = rr["core_rotating"].iloc[0] if len(rr) and isinstance(rr["core_rotating"].iloc[0], str) else ""
    if ns_rot and len(ns_rot) == len(namesake):
        tier = "Dies (namesake rotates)"
    elif ns_rot:
        tier = "Loses a partner (" + ", ".join(ns_rot) + ")"
    elif rc >= 15:
        tier = "Gutted (15+ cards rotate)"
    elif rc >= 8:
        tier = "Wounded (8-15 cards)"
    else:
        tier = "Intact (<8 cards)"
    surv.append({"deck_id": d, "name": a["name"], "share": a["share"], "players": a["players"], "day2_lift": a["day2_lift"],
                 "wr_nonmirror": a["wr_nonmirror"], "namesake": ", ".join(namesake["name"]), "namesake_rotating": ", ".join(ns_rot),
                 "avg_rotating_cards": rc, "tier": tier, "core_rotating_cards": core})
S = pd.DataFrame(surv)
S.to_csv(os.path.join(O, f"archetype_survivability_{WIN}.csv"), index=False)
# naive projected share among survivors (current share x performance), JP signal added separately
alive = S[~S["tier"].str.startswith("Dies")].copy()
alive["perf"] = alive["day2_lift"].fillna(1).clip(0.3, 2.5)
alive["proj_share_naive"] = alive["share"] * alive["perf"] / (alive["share"] * alive["perf"]).sum()
alive.sort_values("proj_share_naive", ascending=False).to_csv(os.path.join(O, f"post_rotation_naive_projection_{WIN}.csv"), index=False)
summ = S.groupby(S["tier"].str.split(" ").str[0]).agg(archetypes=("deck_id", "size"), share=("share", "sum"))
print(summ.to_string())
print(R.head(30).to_string())
