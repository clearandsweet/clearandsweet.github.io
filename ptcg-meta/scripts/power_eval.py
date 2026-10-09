"""Card Power / Deck Power tables and validation against results.
Validation is BETWEEN archetypes (the CE weights were fitted WITHIN archetypes, so this is out of sample for them):
archetype x window means vs non-mirror win rate and Day 2 rate, window means removed, leave-one-archetype-out CV.
Usage: python3 -I power_eval.py DATADIR [WINDOW=CUR]
"""
import os, sys, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model_config as C
D = sys.argv[1]; WIN = sys.argv[2] if len(sys.argv) > 2 else "CUR"
O, P = os.path.join(D, "out"), os.path.join(D, "processed")
CP = pd.read_csv(os.path.join(O, "power_cards_all.csv.gz"))
DL = pd.read_csv(os.path.join(O, "power_lists.csv.gz")).set_index("uid")
WS = ["hand", "fitted", "data"]
names = pd.read_csv(os.path.join(O, f"archetypes_{WIN}.csv")).set_index("deck_id")["name"].to_dict()
for w in ("CRI", "POR", "WORLDS"):
    p = os.path.join(O, f"archetypes_{w}.csv")
    if os.path.exists(p):
        for k, v in pd.read_csv(p).set_index("deck_id")["name"].items(): names.setdefault(k, v)

# ---------- outcomes per archetype x window ----------
pm = pd.read_csv(os.path.join(O, "player_matches_long.csv.gz"), dtype={"tid": str})
nm = pm[pm["deck"] != pm["opp_deck"]]
wr = nm.groupby(["window", "deck"])[["w", "l", "t"]].sum()
wr["games"] = wr.sum(axis=1); wr["wr"] = (wr["w"] + wr["t"] / 3) / wr["games"]
wr.index.names = ["window", "deck_id"]
DL["prize_race"] = DL["offense_prizes"] - DL["liability_prizes"]
cols = [f"effect_{w}" for w in WS] + [f"power_{w}" for w in WS] + [f"power_H_{w}" for w in WS] + ["offense_prizes", "liability_prizes", "prize_race", "offense_H", "dmgheal_units"]
AW = DL.groupby(["window", "deck_id"]).agg(lists=("day2", "size"), day2_rate=("day2", "mean"), **{c: (c, "mean") for c in cols})
AW = AW.join(wr[["wr", "games"]])
AW["name"] = [names.get(d, d) for d in AW.index.get_level_values("deck_id")]
AW.to_csv(os.path.join(O, "power_archetypes_all.csv"))

# ---------- validation ----------
from scipy.stats import spearmanr
V = AW[(AW["lists"] >= 30) & (AW["games"] >= 300)].copy().reset_index()
X10 = C.POWER_CE_PER_PRIZE
V["effect_hand_base"] = V["effect_hand"] - 100 / C.HP_PER_PRIZE * X10 * V["dmgheal_units"]
for c in cols + ["wr", "day2_rate", "effect_hand_base", "dmgheal_units"]:
    V[c + "_dm"] = V[c] - V.groupby("window")[c].transform("mean")
def wls(X, y, w):
    Wh = np.sqrt(w); b, *_ = np.linalg.lstsq(X * Wh[:, None], y * Wh, rcond=None); return b
def skill(x, ycol, cap):
    """Leave-one-archetype-out (all of its windows): 1 - MSE(model) / MSE(mean of the other archetypes)."""
    w = np.minimum(V["games"].values, cap); y = V[ycol].values; pred = np.zeros(len(V)); pn = np.zeros(len(V))
    X = np.column_stack([np.ones(len(V)), x])
    for d in V["deck_id"].unique():
        te = (V["deck_id"] == d).values
        b = wls(X[~te], y[~te], w[~te]); pred[te] = X[te] @ b; pn[te] = np.average(y[~te], weights=w[~te])
    return 1 - np.average((y - pred) ** 2, weights=w) / np.average((y - pn) ** 2, weights=w)
def hand_power(X):
    if X == "inf": return V["prize_race_dm"].values
    return (V["effect_hand_base_dm"] + 100 / C.HP_PER_PRIZE * X * V["dmgheal_units_dm"] + X * V["prize_race_dm"]).values
models = [("Power, hand-set weights", V["power_hand_dm"].values), ("Power, fitted weights", V["power_fitted_dm"].values),
          ("Power, data-only weights", V["power_data_dm"].values), ("Effect only (hand-set)", V["effect_hand_dm"].values),
          ("Prize race only", V["prize_race_dm"].values)]
models += [(f"Hand-set, {x} CE per Prize", hand_power(x)) for x in (0, 3, 6, 10, 15, 20)]
res = []
for label, x in models:
    r = {"model": label, "spearman_wr": float(spearmanr(x, V["wr_dm"])[0]), "spearman_day2": float(spearmanr(x, V["day2_rate_dm"])[0])}
    for ycol, tag in (("wr_dm", "wr"), ("day2_rate_dm", "day2")):
        for cap, ct in ((1e9, "games"), (2000, "cap2000"), (500, "cap500")):
            r[f"skill_{tag}_{ct}"] = skill(x, ycol, cap)
    res.append(r)
VR = pd.DataFrame(res)
VR.to_csv(os.path.join(O, "power_validation.csv"), index=False)
print("units", len(V), "archetypes", V["deck_id"].nunique())
print(VR.round(3).to_string())
w2 = np.minimum(V["games"].values, 2000)
b1 = wls(np.column_stack([np.ones(len(V)), V["power_hand_dm"]]), V["wr_dm"].values, w2)
b2 = wls(np.column_stack([np.ones(len(V)), V["power_hand_dm"]]), V["day2_rate_dm"].values, w2)
cal = {"wr_per_power_ce": float(b1[1]), "day2_per_power_ce": float(b2[1]), "n_units": int(len(V)), "n_archetypes": int(V["deck_id"].nunique()),
       "ce_per_prize": X10, "prizes_taken_per_game": C.PRIZES_TAKEN_PER_GAME}
json.dump(cal, open(os.path.join(O, "power_calibration.json"), "w"), indent=1)
V[["window", "deck_id", "name", "lists", "games", "wr", "day2_rate", "power_hand", "power_fitted", "power_data", "effect_hand",
   "offense_prizes", "liability_prizes"]].to_csv(os.path.join(O, "power_validation_units.csv"), index=False)
print(json.dumps(cal, indent=1))

# ---------- current-window tables ----------
c = CP[CP["window"] == WIN]
n_lists = c["uid"].nunique()
CT = c.groupby(["cat", "name"]).agg(lists=("uid", "nunique"), copies=("copies", "mean"), legal_post=("legal_post", "min"),
                                    hp=("hp", "mean"), prizes=("prizes", "mean"), q_board=("q_board", "mean"),
                                    effect_hand=("effect_hand", "mean"), effect_fitted=("effect_fitted", "mean"),
                                    offense=("offense_prizes", "mean"), liability=("liability_prizes", "mean"),
                                    lia_active=("lia_active_raw", "mean"), lia_gust=("lia_gust_raw", "mean"), lia_spread=("lia_spread_raw", "mean"),
                                    power_hand=("power_hand", "mean"), power_fitted=("power_fitted", "mean")).reset_index()
CT["inclusion"] = CT["lists"] / n_lists
CT["power_per_copy"] = CT["power_hand"] / CT["copies"]
CT["prize_race"] = CT["offense"] - CT["liability"]
top_arch = c.groupby(["name", "deck_id"])["uid"].nunique().reset_index().sort_values("uid", ascending=False).drop_duplicates("name").set_index("name")["deck_id"]
CT["top_archetype"] = CT["name"].map(top_arch).map(lambda d: names.get(d, d))
CT.sort_values("power_hand", ascending=False).to_csv(os.path.join(O, f"power_cards_{WIN}.csv"), index=False)
A = AW.loc[WIN].reset_index()
A = A[A["lists"] >= 15].copy()
A["H_share_of_power"] = A["power_H_hand"] / A["power_hand"]
A["power_after_rotation"] = A["power_hand"] - A["power_H_hand"]
ok = A["wr"].notna()
A["pred_wr"] = (np.average(A.loc[ok, "wr"], weights=A.loc[ok, "games"]) +
                cal["wr_per_power_ce"] * (A["power_hand"] - np.average(A.loc[ok, "power_hand"], weights=A.loc[ok, "games"])))
A["wr_vs_pred"] = A["wr"] - A["pred_wr"]
A.sort_values("power_hand", ascending=False).to_csv(os.path.join(O, f"power_archetypes_{WIN}.csv"), index=False)
pd.set_option("display.width", 250)
print(CT.sort_values("power_hand", ascending=False).head(30)[["cat", "name", "lists", "copies", "effect_hand", "offense", "liability", "power_hand", "power_fitted"]].round(2).to_string())
print(A.sort_values("power_hand", ascending=False)[["name", "lists", "effect_hand", "offense_prizes", "liability_prizes", "power_hand", "power_fitted", "H_share_of_power", "wr", "day2_rate"]].round(3).head(40).to_string())
