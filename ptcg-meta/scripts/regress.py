"""Fit CE weights from results.
A) list-level: outcome ~ resource groups + skill + archetype-window FE + event FE  (WR: WLS by games; Day 2: logit)
B) card-level: outcome ~ copies of each common card + same controls -> per-copy value; then
   stage 2: per-copy value ~ per-copy resource components (WLS by 1/se^2) -> component weights.
Usage: python3 -I regress.py DATADIR
"""
import os, sys, json, warnings
import numpy as np, pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model_config as MC
from cardattrs import load_attrs
D = sys.argv[1]; O = os.path.join(D, "out"); P = os.path.join(D, "processed")
F = pd.read_csv(os.path.join(O, "list_features.csv.gz"), dtype={"tid": str})
G = list(MC.COMPONENT_GROUPS)
F["n"] = F[["W", "L", "T"]].sum(axis=1)
F = F[F["n"] >= 3].copy()
F["wr"] = (F["W"] + F["T"] / 3) / F["n"]
F["arch_win"] = F["deck_id"].astype(str) + "|" + F["window"]
# ---- skill: leave-one-event-out residual performance, shrunk ----
F["resid"] = F["wr"] - F.groupby("arch_win")["wr"].transform("mean")
tot = F.groupby("player_id")["resid"].agg(["sum", "count"])
F = F.join(tot, on="player_id")
F["n_other"] = F["count"] - 1
F["skill"] = (F["sum"] - F["resid"]) / (F["n_other"] + 2)
F["has_hist"] = (F["n_other"] > 0).astype(int)
F = F.drop(columns=["sum", "count"])
big = F["arch_win"].map(F["arch_win"].value_counts()) >= 30
F = F[big].copy()
# standardize resource groups within the sample for numerical stability, keep raw scale for weights
fmla_rhs = " + ".join(G) + " + skill + has_hist + C(arch_win) + C(tid)"
out = {"n_lists": int(len(F)), "n_archetype_windows": int(F["arch_win"].nunique()),
       "skill_coverage": float(F["has_hist"].mean())}
res = {}
m_wr = smf.wls("wr ~ " + fmla_rhs, data=F, weights=F["n"]).fit(cov_type="cluster", cov_kwds={"groups": F["player_id"].fillna(-1).astype(int)})
m_d2 = smf.logit("day2 ~ " + fmla_rhs, data=F).fit(disp=0, maxiter=200, cov_type="cluster", cov_kwds={"groups": F["player_id"].fillna(-1).astype(int)})
def ratios(m, base="draw"):
    b, V = m.params, m.cov_params()
    rows = []
    for g in G:
        r = b[g] / b[base]
        # delta method
        gvec = pd.Series(0.0, index=b.index); gvec[g] = 1 / b[base]; gvec[base] = -b[g] / b[base] ** 2
        se = float(np.sqrt(gvec @ V @ gvec)) if g != base else 0.0
        rows.append({"group": g, "coef": b[g], "coef_se": m.bse[g], "p": m.pvalues[g], "ce_weight": r, "ce_weight_se": se})
    return pd.DataFrame(rows)
A_wr, A_d2 = ratios(m_wr), ratios(m_d2)
out["skill_coef_wr"] = float(m_wr.params["skill"]); out["skill_coef_d2"] = float(m_d2.params["skill"])
out["draw_coef_wr"] = float(m_wr.params["draw"]); out["draw_coef_wr_se"] = float(m_wr.bse["draw"])
out["draw_coef_d2"] = float(m_d2.params["draw"]); out["draw_coef_d2_se"] = float(m_d2.bse["draw"])
A = A_wr.merge(A_d2, on="group", suffixes=("_wr", "_d2"))
A["hand_weight"] = A["group"].map(MC.HAND_WEIGHTS)
A["mean_per_game"] = A["group"].map(F[G].mean())
A["sd_within_arch"] = A["group"].map(F.groupby("arch_win")[G].transform(lambda x: x - x.mean()).std())
A.to_csv(os.path.join(O, "ce_fit_listlevel.csv"), index=False)
print(A.round(4).to_string())

# ---- B) card-level per-copy values ----
lc = pd.read_csv(os.path.join(P, "list_cards.csv"), dtype={"tid": str, "number": str})
lc["uid"] = lc["tid"] + ":" + lc["tp_id"].astype(str)
lc = lc[lc["uid"].isin(F["uid"])]
attrs = load_attrs(D)
# functional identity: trainers by name, Pokémon by card_key; keep cards in >= 150 lists that are not basic energy
lc["cid"] = np.where(lc["cat"] == "pokemon", lc["card_key"], lc["name"])
cnt = lc.groupby(["uid", "cid"])["count"].sum().unstack(fill_value=0)
BASIC_E = {"Grass Energy", "Fire Energy", "Water Energy", "Lightning Energy", "Psychic Energy", "Fighting Energy", "Darkness Energy", "Metal Energy", "Fairy Energy"}
keep = [c for c in cnt.columns if (cnt[c] > 0).sum() >= 150 and c not in BASIC_E]
X = cnt[keep].reindex(F["uid"]).fillna(0)
# collapse evolution lines / always-paired cards: drop a column that is ~a copy of another (r > 0.92), keeping the higher stage
stage = {c: (attrs.get(c, {}).get("stage") if attrs.get(c, {}).get("is_pokemon") else 9) for c in keep}
corr = X.corr()
drop, merged = set(), {}
for i, a in enumerate(keep):
    for b in keep[i + 1:]:
        if a in drop or b in drop: continue
        if corr.loc[a, b] > 0.92:
            lo, hi = (a, b) if (stage.get(a) or 0) < (stage.get(b) or 0) else (b, a)
            drop.add(lo); merged.setdefault(hi, []).append(lo)
keep = [c for c in keep if c not in drop]
X = X[keep]
X.columns = [f"c{i}" for i in range(len(keep))]
cmap = dict(zip(X.columns, keep))
FX = pd.concat([F.set_index("uid")[["wr", "n", "day2", "skill", "has_hist", "arch_win", "tid", "player_id"]], X], axis=1)
# within-archetype: absorb arch_win & tid by including dummies; cards that never vary within archetype get absorbed (NaN se)
rhs = " + ".join(X.columns) + " + skill + has_hist + C(arch_win) + C(tid)"
mB = smf.wls("wr ~ " + rhs, data=FX, weights=FX["n"]).fit(cov_type="cluster", cov_kwds={"groups": FX["player_id"].fillna(-1).astype(int)})
mBd = smf.ols("day2 ~ " + rhs, data=FX).fit(cov_type="cluster", cov_kwds={"groups": FX["player_id"].fillna(-1).astype(int)})
# per-copy resource components for stage 2 (per game, per copy)
eng_uses = F.set_index("uid")[[c for c in F.columns if c.startswith("uses::")]]
card_rows = []
for col, cid in cmap.items():
    lists_with = (FX[col] > 0)
    within_sd = FX.groupby("arch_win")[col].transform(lambda x: x - x.mean()).std()
    a = attrs.get(cid) or next((v for k, v in attrs.items() if v.get("name") == cid), {})
    name = a.get("name", cid)
    comp = {}
    if name in MC.TRAINER_COMPONENTS:
        sup = a.get("is_supporter", False)
        for k, x in MC.TRAINER_COMPONENTS[name].items():
            comp[k] = comp.get(k, 0) + x * 0.68 * (0.8 if sup else 1.0)
    elif name in MC.ENGINES and f"uses::{name}" in eng_uses.columns:
        # average uses per game per copy among lists that run it
        u = eng_uses.loc[lists_with[lists_with].index, f"uses::{name}"]
        per_copy = float((u / FX.loc[u.index, col]).mean()) if len(u) else 0
        for k, x in MC.ENGINES[name]["value"].items():
            comp[k] = comp.get(k, 0) + x * per_copy
    card_rows.append({"card": cid, "name": name, "merged_with": "; ".join(merged.get(cid, [])), "lists": int(lists_with.sum()), "avg_copies": float(FX.loc[lists_with, col].mean()),
                      "within_arch_sd": float(within_sd),
                      "wr_per_copy": mB.params.get(col, np.nan), "wr_per_copy_se": mB.bse.get(col, np.nan), "wr_p": mB.pvalues.get(col, np.nan),
                      "d2_pp_per_copy": mBd.params.get(col, np.nan), "d2_se": mBd.bse.get(col, np.nan), "d2_p": mBd.pvalues.get(col, np.nan),
                      "legal_post": a.get("legal_post"), "components": json.dumps({k: round(v, 3) for k, v in comp.items()})})
CB = pd.DataFrame(card_rows).sort_values("wr_per_copy", ascending=False)
CB.to_csv(os.path.join(O, "card_value_per_copy.csv"), index=False)
# stage 2 (marginal): per-copy value ~ what ONE MORE copy adds.
RAW2G = {raw: g for g, raws in MC.COMPONENT_GROUPS.items() for raw in raws}
def to_groups(comp):
    v = {g: 0.0 for g in G}
    for k, x in comp.items():
        g = RAW2G.get(k)
        if g is None: continue
        if g == "cost": x = abs(x)
        if g in ("damage_100hp", "heal_100hp"): x = x / 100
        v[g] += x
    return v
# average Supporter component vector, weighted by copies played across all lists (the displaced alternative)
sup_tot, sup_n = {g: 0.0 for g in G}, 0.0
for nm, comp in MC.TRAINER_COMPONENTS.items():
    a_ = next((v for v in attrs.values() if v.get("name") == nm), {})
    if not a_.get("is_supporter"): continue
    copies = float(lc.loc[lc["name"] == nm, "count"].sum())
    if copies <= 0: continue
    for g, x in to_groups(comp).items(): sup_tot[g] += x * copies
    sup_n += copies
AVG_SUP = {g: sup_tot[g] / sup_n for g in G}
U_DISPLACE = 0.85
curves_p = os.path.join(O, "engine_copy_curves.csv")
curves = pd.read_csv(curves_p) if os.path.exists(curves_p) else pd.DataFrame(columns=["card", "copies", "marginal_uses"])
def marginal_vec(name, a_, n):
    """Resource groups added by one more copy at a typical count n (per game)."""
    if name in MC.TRAINER_COMPONENTS:
        comp = to_groups(MC.TRAINER_COMPONENTS[name])
        if a_.get("is_supporter"):
            return {g: 0.68 * (comp[g] - U_DISPLACE * AVG_SUP[g]) for g in G}
        r = max(0.3, 1 - 0.1 * (n - 1))
        return {g: 0.68 * r * comp[g] for g in G}
    if name in MC.ENGINES:
        k = int(min(4, max(1, round(n))))
        cc = curves[(curves["card"] == name) & (curves["copies"] == k)]
        mu = float(cc["marginal_uses"].mean()) if len(cc) else np.nan
        if not np.isfinite(mu):
            mu = float(F.loc[F["uid"].isin(FX.index[FX[col_of[name]] > 0]), f"uses::{name}"].mean() / max(n, 1)) if name in col_of and f"uses::{name}" in F.columns else 0.0
        comp = to_groups(MC.ENGINES[name]["value"])
        return {g: mu * comp[g] for g in G}
    return None
col_of = {cmap[c].split(" [")[0] if False else (attrs.get(cmap[c], {}).get("name") or cmap[c]): c for c in cmap}
HW = np.array([MC.HAND_WEIGHTS[g] for g in G])
G2 = G + ["ace"]
fits = {}
marg_rows = []
for _, r in CB.iterrows():
    a_ = attrs.get(r["card"]) or next((v for v in attrs.values() if v.get("name") == r["name"]), {})
    mv = marginal_vec(r["name"], a_, r["avg_copies"])
    if mv is None: continue
    mv["ace"] = 1.0 if "ACE SPEC" in (a_.get("subtypes") or []) else 0.0
    marg_rows.append({"card": r["card"], "name": r["name"], **mv})
MV = pd.DataFrame(marg_rows).set_index("card")
MV.to_csv(os.path.join(O, "card_marginal_components.csv"))
ANCHOR, ANCHOR_CE, TAU = "tutor", 1.5, 1.0
for ycol, secol, tag in (("wr_per_copy", "wr_per_copy_se", "wr"), ("d2_pp_per_copy", "d2_se", "d2")):
    d = CB.set_index("card").join(MV[G2], how="inner")
    d = d[np.isfinite(d[ycol]) & np.isfinite(d[secol]) & (d[secol] > 0)]
    Xi = sm.add_constant(d[G2].values); y = d[ycol].values; w = 1 / d[secol].values ** 2
    m0 = sm.WLS(y, Xi, weights=w).fit()                    # data only, outcome units per resource unit
    theta, V = m0.params, m0.cov_params()
    s_ = theta[1 + G2.index(ANCHOR)] / ANCHOR_CE            # outcome units per CE, anchored on search = 1.5 CE
    # Bayesian update: prior theta_g ~ N(s*hand_g, (s*tau)^2) for every component except the intercept and ACE flag
    prior_mu = np.concatenate([[theta[0]], [s_ * MC.HAND_WEIGHTS[g] for g in G], [theta[-1]]])
    prior_var = np.concatenate([[1e6], np.full(len(G), (s_ * TAU) ** 2), [1e6]])
    Vinv = np.linalg.inv(V)
    Pinv = np.diag(1 / prior_var)
    post_cov = np.linalg.inv(Vinv + Pinv)
    post = post_cov @ (Vinv @ theta + Pinv @ prior_mu)
    df = pd.DataFrame({"group": G2, "hand_weight": [MC.HAND_WEIGHTS.get(g, np.nan) for g in G2],
                       "outcome_per_unit": theta[1:], "outcome_per_unit_se": np.sqrt(np.diag(V))[1:],
                       "data_only_weight": theta[1:] / s_, "fitted_weight": post[1:] / s_, "fitted_se": np.sqrt(np.diag(post_cov))[1:] / abs(s_),
                       "n_cards_with_component": [int((d[g] != 0).sum()) for g in G2]})
    ce_hand = d[G].values @ np.array([MC.HAND_WEIGHTS[g] for g in G])
    pred_hand = np.column_stack([np.ones(len(y)), ce_hand, d["ace"].values])
    hb = np.linalg.lstsq(pred_hand * np.sqrt(w)[:, None], y * np.sqrt(w), rcond=None)[0]
    def wcorr(a, b):
        am, bm = np.average(a, weights=w), np.average(b, weights=w)
        return float(np.sum(w * (a - am) * (b - bm)) / np.sqrt(np.sum(w * (a - am) ** 2) * np.sum(w * (b - bm) ** 2)))
    pred = pd.DataFrame({"card": d.index, f"measured_{tag}": y, f"predicted_{tag}": Xi @ post})
    pred[f"residual_{tag}"] = pred[f"measured_{tag}"] - pred[f"predicted_{tag}"]
    fits[tag + "_pred"] = pred
    fits[tag] = {"scale_outcome_per_ce": float(s_), "n_cards": int(len(d)), "table": df,
                 "corr_hand": wcorr(pred_hand @ hb, y), "corr_fit": wcorr(Xi @ post, y), "corr_data": wcorr(Xi @ theta, y)}
    df.to_csv(os.path.join(O, f"ce_fit_cardlevel_{tag}.csv"), index=False)
    print(tag, "outcome per CE (search-anchored):", round(s_, 5), "n cards", len(d), "corr hand/fit/data:",
          round(fits[tag]["corr_hand"], 3), round(fits[tag]["corr_fit"], 3), round(fits[tag]["corr_data"], 3))
    print(df.round(4).to_string())
fits["wr_pred"].merge(fits["d2_pred"], on="card", how="outer").merge(CB[["card", "name"]], on="card").to_csv(os.path.join(O, "card_value_fit.csv"), index=False)
cw = fits["wr"]["table"][["group", "hand_weight"]].copy()
v1, v2 = fits["wr"]["table"]["fitted_se"] ** 2, fits["d2"]["table"]["fitted_se"] ** 2
cw["fitted_weight"] = (fits["wr"]["table"]["fitted_weight"] / v1 + fits["d2"]["table"]["fitted_weight"] / v2) / (1 / v1 + 1 / v2)
cw["fitted_se"] = np.sqrt(1 / (1 / v1 + 1 / v2))
cw["fitted_wr"] = fits["wr"]["table"]["fitted_weight"]; cw["fitted_d2"] = fits["d2"]["table"]["fitted_weight"]
cw["data_only_wr"] = fits["wr"]["table"]["data_only_weight"]; cw["data_only_d2"] = fits["d2"]["table"]["data_only_weight"]
cw["wr_points_per_unit"] = fits["wr"]["table"]["outcome_per_unit"] * 100; cw["wr_points_per_unit_se"] = fits["wr"]["table"]["outcome_per_unit_se"] * 100
cw["d2_points_per_unit"] = fits["d2"]["table"]["outcome_per_unit"] * 100; cw["d2_points_per_unit_se"] = fits["d2"]["table"]["outcome_per_unit_se"] * 100
cw.to_csv(os.path.join(O, "ce_weights_fitted.csv"), index=False)
out["avg_supporter_components"] = {k: round(v, 3) for k, v in AVG_SUP.items() if v}
out["corr_hand_wr"], out["corr_fit_wr"] = fits["wr"]["corr_hand"], fits["wr"]["corr_fit"]
out["corr_hand_d2"], out["corr_fit_d2"] = fits["d2"]["corr_hand"], fits["d2"]["corr_fit"]
out["corr_data_wr"], out["corr_data_d2"] = fits["wr"]["corr_data"], fits["d2"]["corr_data"]
out["anchor"] = f"{ANCHOR} = {ANCHOR_CE} CE"; out["prior_tau_ce"] = TAU
out["wr_points_per_ce_per_game"] = fits["wr"]["scale_outcome_per_ce"]   # outcome units (fraction) per CE per game
out["day2_points_per_ce_per_game"] = fits["d2"]["scale_outcome_per_ce"]
out["stage2_n_cards"] = fits["wr"]["n_cards"]
json.dump(out, open(os.path.join(O, "ce_fit_meta.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
print(cw.round(3).to_string())
show = CB[CB["within_arch_sd"] > 0.15].copy()
print(show.head(25)[["card", "lists", "avg_copies", "wr_per_copy", "wr_per_copy_se", "d2_pp_per_copy", "d2_se"]].round(4).to_string())
print(show.tail(15)[["card", "lists", "avg_copies", "wr_per_copy", "wr_per_copy_se", "d2_pp_per_copy", "d2_se"]].round(4).to_string())
