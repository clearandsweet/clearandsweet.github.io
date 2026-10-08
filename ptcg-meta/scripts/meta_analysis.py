"""Metagame, card inventory and rotation analysis.
Usage: python3 -I meta_analysis.py DATADIR
Writes DATADIR/out/*.csv and DATADIR/out/summary.json
"""
import json, os, sys
import numpy as np, pandas as pd
D = sys.argv[1]
P, O = os.path.join(D, "processed"), os.path.join(D, "out")
os.makedirs(O, exist_ok=True)
rd = lambda f, **k: pd.read_csv(os.path.join(P, f), **k)
events = rd("events.csv", dtype={"tid": str})
players = rd("players.csv", dtype={"tid": str})
lc = rd("list_cards.csv", dtype={"tid": str, "number": str})
cm = rd("cards.csv", dtype={"number": str}).set_index("card_key")
matches = rd("matches.csv", dtype={"tid": str})
BASIC_E = {"Grass Energy", "Fire Energy", "Water Energy", "Lightning Energy", "Psychic Energy", "Fighting Energy",
           "Darkness Energy", "Metal Energy", "Fairy Energy"}

# ---------- format windows (newest set with real presence) ----------
SET_ORDER = ["POR", "CRI", "PBL", "30C"]
lists_per_event = lc.groupby("tid")["tp_id"].nunique()
pres = lc.drop_duplicates(["tid", "tp_id", "set"]).groupby(["tid", "set"]).size().unstack(fill_value=0)
pres = pres.div(lists_per_event, axis=0)
def window(tid):
    t = int(tid)
    if t >= 72: return "CUR"        # 2027-season Regionals (Pitch Black on; 30th Celebration from Brisbane)
    if t == 71: return "WORLDS"     # World Championship 2026
    if t >= 69: return "CRI"        # Chaos Rising legal (Turin, NAIC)
    return "POR"                    # Perfect Order format after the G rotation (Prague -> Indianapolis)
events["window"] = events["tid"].map(window)
events["set_presence"] = events["tid"].map(lambda t: {s: round(float(pres.loc[t, s]), 3) for s in SET_ORDER if s in pres.columns})
players = players.merge(events[["tid", "window"]], on="tid")
lc = lc.merge(events[["tid", "window"]], on="tid")
WIN_LABEL = {"CUR": "Current format: 2027-season Regionals", "WORLDS": "World Championship 2026", "CRI": "Chaos Rising (Turin, NAIC)", "POR": "Perfect Order (post-G rotation)"}
events.to_csv(os.path.join(O, "events_windows.csv"), index=False)

# ---------- archetype table ----------
def wr(w, l, t):
    n = w + l + t
    return (w + t / 3) / n if n else np.nan
sw = matches.copy()
# swiss-only results per player-deck: use matches for record (drop byes already excluded)
rows = []
for side, opp in (("p1", "p2"), ("p2", "p1")):
    x = sw[["tid", "round", side, opp, f"{side}_deck", f"{opp}_deck", "result"]].copy()
    x.columns = ["tid", "round", "player", "opp", "deck", "opp_deck", "result"]
    x["w"] = (x["result"] == side).astype(int)
    x["l"] = ((x["result"] == opp) | (x["result"] == "dl")).astype(int)
    x["t"] = (x["result"] == "tie").astype(int)
    rows.append(x)
games = pd.concat(rows, ignore_index=True)
games = games.merge(events[["tid", "window"]], on="tid")
games.to_csv(os.path.join(O, "player_matches_long.csv.gz"), index=False, compression="gzip")

def wilson(k, n, z=1.96):
    if n == 0: return (np.nan, np.nan)
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)
def arche_table(pl, gm, key="deck_id", name="deck_name"):
    n_all = len(pl)
    g = pl.groupby(key).agg(name=(name, "first"), players=("tp_id", "size"), day2=("day2", "sum"),
                            topcut=("topcut", "sum"), events=("tid", "nunique"))
    g["share"] = g["players"] / n_all
    g["day2_rate"] = g["day2"] / g["players"]
    g["day2_share"] = g["day2"] / max(pl["day2"].sum(), 1)
    g["topcut_rate"] = g["topcut"] / g["players"]
    g["topcut_share"] = g["topcut"] / max(pl["topcut"].sum(), 1)
    base_d2 = pl["day2"].mean()
    g["day2_lift"] = g["day2_rate"] / base_d2 if base_d2 else np.nan
    base_tc = pl["topcut"].mean()
    g["topcut_lift"] = g["topcut_rate"] / base_tc if base_tc else np.nan
    gm2 = gm.copy()
    if key == "sup_id":
        m = pl.drop_duplicates(["deck_id"]).set_index("deck_id")["sup_id"]
        gm2["deck"] = gm2["deck"].map(m).fillna(gm2["deck"]); gm2["opp_deck"] = gm2["opp_deck"].map(m).fillna(gm2["opp_deck"])
    nm = gm2[gm2["deck"] != gm2["opp_deck"]].groupby("deck")[["w", "l", "t"]].sum()
    al = gm2.groupby("deck")[["w", "l", "t"]].sum()
    g["W"], g["L"], g["T"] = al["w"], al["l"], al["t"]
    g["wr_all"] = [wr(*al.loc[i]) if i in al.index else np.nan for i in g.index]
    g["wr_nonmirror"] = [wr(*nm.loc[i]) if i in nm.index else np.nan for i in g.index]
    g["games_nonmirror"] = [int(nm.loc[i].sum()) if i in nm.index else 0 for i in g.index]
    ci = [wilson(a, b) for a, b in zip(g["day2"], g["players"])]
    g["day2_rate_lo"], g["day2_rate_hi"] = [c[0] for c in ci], [c[1] for c in ci]
    K = 30  # pseudo-players of shrinkage toward the field Day 2 rate
    g["day2_lift_shrunk"] = ((g["day2"] + K * base_d2) / (g["players"] + K)) / base_d2 if base_d2 else np.nan
    n = g["games_nonmirror"].replace(0, np.nan)
    g["wr_nonmirror_se"] = np.sqrt(g["wr_nonmirror"] * (1 - g["wr_nonmirror"]) / n)
    g = g.sort_values("players", ascending=False)
    g["rank"] = np.arange(1, len(g) + 1)
    return g

summary = {"windows": {}}
for win in ["CUR", "WORLDS", "CRI", "POR"]:
    pl = players[players["window"] == win]
    if pl.empty:
        continue
    gm = games[games["window"] == win]
    t = arche_table(pl, gm)
    t.to_csv(os.path.join(O, f"archetypes_{win}.csv"))
    arche_table(pl, gm, "sup_id", "sup_name").to_csv(os.path.join(O, f"superarchetypes_{win}.csv"))
    summary["windows"][win] = {"label": WIN_LABEL.get(win, win), "events": events[events["window"] == win][["tid", "city", "date", "players"]].to_dict("records"),
                               "players": int(len(pl)), "day2": int(pl["day2"].sum()), "topcut": int(pl["topcut"].sum()),
                               "archetypes": int(pl["deck_id"].nunique())}

pl_all = players[players["window"].isin(["POR", "CRI", "WORLDS", "CUR"])]
arche_table(pl_all, games[games["window"].isin(["POR", "CRI", "WORLDS", "CUR"])]).to_csv(os.path.join(O, "archetypes_post_G_rotation_all.csv"))
# per-event share for trend lines
trend = players.groupby(["tid", "deck_id"]).size().unstack(fill_value=0)
trend = trend.div(trend.sum(axis=1), axis=0)
trend.T.to_csv(os.path.join(O, "archetype_share_by_event.csv"))

# ---------- matchup matrix (current window, top archetypes) ----------
for win in ["CUR", "WORLDS"]:
    gm = games[(games["window"] == win)]
    top = players[players["window"] == win]["deck_id"].value_counts().head(30).index
    mm = gm[gm["deck"].isin(top) & gm["opp_deck"].isin(top)].groupby(["deck", "opp_deck"])[["w", "l", "t"]].sum()
    mm["n"] = mm.sum(axis=1)
    mm["wr"] = (mm["w"] + mm["t"] / 3) / mm["n"]
    mm.reset_index().to_csv(os.path.join(O, f"matchups_{win}.csv"), index=False)

# ---------- card inventory ----------
lc["is_basic_energy"] = lc["name"].isin(BASIC_E)
lc["legal_post"] = lc["card_key"].map(cm["legal_post"]).fillna(1).astype(int)
lc.loc[lc["is_basic_energy"], "legal_post"] = 1
pl_idx = players.set_index(["tid", "tp_id"])
lc = lc.join(pl_idx[["day2", "topcut", "deck_id", "deck_name", "sup_id"]], on=["tid", "tp_id"])
def inventory(df, nlists, nday2, ntop):
    per = df.groupby(["card_key", "tid", "tp_id"]).agg(count=("count", "sum"), day2=("day2", "first"), topcut=("topcut", "first")).reset_index()
    g = per.groupby("card_key").agg(lists=("count", "size"), copies=("count", "sum"), lists_day2=("day2", "sum"), lists_topcut=("topcut", "sum"))
    g["inclusion"] = g["lists"] / nlists
    g["avg_copies"] = g["copies"] / g["lists"]
    g["inclusion_day2"] = g["lists_day2"] / max(nday2, 1)
    g["inclusion_topcut"] = g["lists_topcut"] / max(ntop, 1)
    g["day2_lift"] = g["inclusion_day2"] / g["inclusion"]
    g = g.join(cm[["name", "cat", "set", "number", "marks", "legal_post", "subtypes", "jp_prints"]])
    return g.sort_values("lists", ascending=False)
for win in ["CUR", "WORLDS", "CRI", "POR"]:
    sub = lc[lc["window"] == win]
    if sub.empty: continue
    pls = players[(players["window"] == win) & (players["has_list"] == 1)]
    inv = inventory(sub, len(pls), pls["day2"].sum(), pls["topcut"].sum())
    inv.to_csv(os.path.join(O, f"card_inventory_{win}.csv"))

pls_all = players[players["has_list"] == 1]
inv_all = inventory(lc, len(pls_all), pls_all["day2"].sum(), pls_all["topcut"].sum())
by_win = lc.drop_duplicates(["card_key", "tid", "tp_id"]).groupby(["card_key", "window"]).size().unstack(fill_value=0)
nl_win = pls_all.groupby("window").size()
for w in by_win.columns:
    inv_all[f"inclusion_{w}"] = (by_win[w] / nl_win.get(w, np.nan)).reindex(inv_all.index)
inv_all.to_csv(os.path.join(O, "card_inventory_all_events.csv"))

# ---------- per-archetype card usage + rotation exposure (current window) ----------
win = "CUR"
sub = lc[lc["window"] == win]
pls = players[(players["window"] == win) & (players["has_list"] == 1)]
per_list = sub.groupby(["tid", "tp_id"]).apply(lambda d: pd.Series({
    "rot_copies": int(d.loc[(d["legal_post"] == 0), "count"].sum()),
    "rot_unique": int(d.loc[(d["legal_post"] == 0), "card_key"].nunique()),
    "rot_pokemon": int(d.loc[(d["legal_post"] == 0) & (d["cat"] == "pokemon"), "count"].sum()),
    "rot_trainer": int(d.loc[(d["legal_post"] == 0) & (d["cat"] == "trainer"), "count"].sum()),
    "rot_energy": int(d.loc[(d["legal_post"] == 0) & (d["cat"] == "energy"), "count"].sum()),
}), include_groups=False).reset_index()
per_list = per_list.merge(pls[["tid", "tp_id", "deck_id", "deck_name", "day2", "topcut"]], on=["tid", "tp_id"])
per_list.to_csv(os.path.join(O, f"rotation_per_list_{win}.csv"), index=False)
arch_cards = sub.groupby(["deck_id", "card_key"]).agg(lists=("tp_id", "nunique"), copies=("count", "sum")).reset_index()
nl = pls.groupby("deck_id").size()
arch_cards["n_lists"] = arch_cards["deck_id"].map(nl)
arch_cards["inclusion"] = arch_cards["lists"] / arch_cards["n_lists"]
arch_cards["avg_copies_when_played"] = arch_cards["copies"] / arch_cards["lists"]
arch_cards["avg_copies_per_list"] = arch_cards["copies"] / arch_cards["n_lists"]
arch_cards = arch_cards.join(cm[["name", "cat", "legal_post", "marks"]], on="card_key")
arch_cards.loc[arch_cards["name"].isin(BASIC_E), "legal_post"] = 1
arch_cards.to_csv(os.path.join(O, f"archetype_cards_{win}.csv"), index=False)
rot = per_list.groupby("deck_id").agg(deck_name=("deck_name", "first"), lists=("tp_id", "size"),
                                      rot_copies=("rot_copies", "mean"), rot_unique=("rot_unique", "mean"),
                                      rot_pokemon=("rot_pokemon", "mean"), rot_trainer=("rot_trainer", "mean"), rot_energy=("rot_energy", "mean"))
core = arch_cards[(arch_cards["inclusion"] >= 0.75) & (arch_cards["legal_post"] == 0)]
rot["core_rotating"] = core.groupby("deck_id").apply(
    lambda d: "; ".join(f'{r["name"]} ({r["avg_copies_when_played"]:.1f})' for _, r in d.sort_values("avg_copies_per_list", ascending=False).iterrows()), include_groups=False)
rot["core_rotating_copies"] = core.groupby("deck_id")["avg_copies_per_list"].sum()
rot = rot.sort_values("lists", ascending=False)
rot.to_csv(os.path.join(O, f"rotation_by_archetype_{win}.csv"))
summary["field_rotating_copies_avg"] = float(per_list["rot_copies"].mean())
json.dump(summary, open(os.path.join(O, "summary.json"), "w"), indent=1, default=str)
print(events[["tid", "city", "window", "set_presence"]].to_string())
print("lists", len(per_list), "avg rotating copies", per_list["rot_copies"].mean())
