"""Japan: CL / JCS top lists and current-format City League lists. Archetypes, card usage vs international,
adoption of JP-only (not yet in English) cards, rotation exposure.
Usage: python3 -I jp_analysis.py DATADIR [INTL_WINDOW=CUR]
"""
import os, sys, json
import numpy as np, pandas as pd
D = sys.argv[1]; WIN = sys.argv[2] if len(sys.argv) > 2 else "CUR"
P, O = os.path.join(D, "processed"), os.path.join(D, "out")
jl = pd.read_csv(os.path.join(P, "jp_lists.csv"))
jc = pd.read_csv(os.path.join(P, "jp_list_cards.csv"), dtype={"number": str})
cm = pd.read_csv(os.path.join(P, "cards.csv"), dtype={"number": str}).set_index("card_key")
en_codes = set(json.load(open(os.path.join(D, "cards", "en_codes.json"))))
jc["jp_only"] = ~jc["set"].isin(en_codes)
jc["legal_post"] = jc["card_key"].map(cm["legal_post"]).fillna(1).astype(int)
BASIC_E = {"Grass Energy", "Fire Energy", "Water Energy", "Lightning Energy", "Psychic Energy", "Fighting Energy", "Darkness Energy", "Metal Energy", "Fairy Energy"}
jc.loc[jc["name"].isin(BASIC_E), "legal_post"] = 1
out = {}
for kind in ("cityleague", "major"):
    L = jl[jl["kind"] == kind]
    if L.empty: continue
    n = L["uid"].nunique()
    arch = L["deck"].fillna("?").value_counts()
    out[kind] = {"lists": int(n), "events": int(L["event"].nunique()),
                 "archetypes": {k: {"lists": int(v), "share": v / n} for k, v in arch.head(25).items()}}
    C = jc[jc["uid"].isin(L["uid"])]
    inc = C.groupby("name").agg(lists=("uid", "nunique"), copies=("count", "sum"))
    inc["inclusion"] = inc["lists"] / n; inc["avg_copies"] = inc["copies"] / inc["lists"]
    jp_only = C[C["jp_only"]].groupby(["name", "set"]).agg(lists=("uid", "nunique"), copies=("count", "sum")).reset_index()
    jp_only["inclusion"] = jp_only["lists"] / n; jp_only["avg_copies"] = jp_only["copies"] / jp_only["lists"]
    jp_only.sort_values("inclusion", ascending=False).to_csv(os.path.join(O, f"jp_{kind}_new_cards.csv"), index=False)
    out[kind]["new_jp_only_cards_top"] = jp_only.sort_values("inclusion", ascending=False).head(20)[["name", "set", "inclusion", "avg_copies"]].to_dict("records")
    rc = C[C["legal_post"] == 0].groupby("uid")["count"].sum().reindex(L["uid"]).fillna(0)
    out[kind]["avg_rotating_cards_per_list"] = float(rc.mean())
    # compare with international inclusion
    intl = pd.read_csv(os.path.join(O, f"card_inventory_{WIN}.csv")).groupby("name")["inclusion"].max()
    inc["intl_inclusion"] = inc.index.map(intl).fillna(0)
    inc["jp_minus_intl"] = inc["inclusion"] - inc["intl_inclusion"]
    inc.sort_values("lists", ascending=False).to_csv(os.path.join(O, f"jp_{kind}_card_inventory.csv"))
    out[kind]["biggest_jp_overindex"] = inc[inc["lists"] >= 5].sort_values("jp_minus_intl", ascending=False).head(15)[["inclusion", "intl_inclusion"]].round(3).reset_index().to_dict("records")
    out[kind]["biggest_jp_underindex"] = inc[inc["intl_inclusion"] >= 0.05].sort_values("jp_minus_intl").head(15)[["inclusion", "intl_inclusion"]].round(3).reset_index().to_dict("records")
    out[kind]["budew_inclusion"] = float(inc["inclusion"].get("Budew", 0))
json.dump(out, open(os.path.join(O, "jp_summary.json"), "w"), indent=1, ensure_ascii=False, default=float)
for k, v in out.items():
    print(k, v["lists"], "lists /", v["events"], "events; avg rotating cards", round(v["avg_rotating_cards_per_list"], 1), "budew", round(v["budew_inclusion"], 3))
    print("  archetypes:", list(v["archetypes"].items())[:12])
    print("  new JP-only cards:", [(r["name"], r["set"], round(r["inclusion"], 3)) for r in v["new_jp_only_cards_top"][:12]])
