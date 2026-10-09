"""Empirical copy-count effects within archetypes (diminishing returns).
For each (archetype, card) with >= 2 count levels of >= MIN lists: outcome ~ C(level) + C(tid) + skill + has_hist,
WR by WLS (weights = games), Day 2 by linear probability; SEs clustered by player; Benjamini-Hochberg q-values.
Usage: python3 -I cardcount.py DATADIR [MIN=40]
"""
import os, sys, warnings
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
warnings.filterwarnings("ignore")
D = sys.argv[1]; MIN = int(sys.argv[2]) if len(sys.argv) > 2 else 40
O, P = os.path.join(D, "out"), os.path.join(D, "processed")
F = pd.read_csv(os.path.join(O, "list_features.csv.gz"), dtype={"tid": str}, usecols=lambda c: not c.startswith(("eng_", "tr_", "uses::")))
F["n"] = F[["W", "L", "T"]].sum(axis=1)
F = F[F["n"] >= 3].copy()
F["wr"] = (F["W"] + F["T"] / 3) / F["n"]
F["arch_win"] = F["deck_id"].astype(str) + "|" + F["window"]
F["resid"] = F["wr"] - F.groupby("arch_win")["wr"].transform("mean")
tot = F.groupby("player_id")["resid"].agg(["sum", "count"])
F = F.join(tot, on="player_id"); F["skill"] = (F["sum"] - F["resid"]) / (F["count"] - 1 + 2); F["has_hist"] = (F["count"] > 1).astype(int)
lc = pd.read_csv(os.path.join(P, "list_cards.csv"), dtype={"tid": str, "number": str})
lc["uid"] = lc["tid"] + ":" + lc["tp_id"].astype(str)
lc = lc[lc["uid"].isin(set(F["uid"]))]
lc["cid"] = np.where(lc["cat"] == "pokemon", lc["card_key"], lc["name"])
BASIC_E = {"Grass Energy", "Fire Energy", "Water Energy", "Lightning Energy", "Psychic Energy", "Fighting Energy", "Darkness Energy", "Metal Energy", "Fairy Energy"}
names = pd.read_csv(os.path.join(O, "archetypes_post_G_rotation_all.csv")).set_index("deck_id")["name"].to_dict()
rows = []
for arch, fa in F.groupby("deck_id"):
    if len(fa) < 300: continue
    sub = lc[lc["uid"].isin(set(fa["uid"]))]
    cnt = sub.groupby(["uid", "cid"])["count"].sum().unstack(fill_value=0).reindex(fa["uid"]).fillna(0)
    for cid in cnt.columns:
        if cid in BASIC_E: continue
        lvl = cnt[cid].clip(upper=4).astype(int)
        vc = lvl.value_counts()
        ok = vc[vc >= MIN]
        if len(ok) < 2: continue
        d = fa.set_index("uid").assign(level=lvl)
        d = d[d["level"].isin(ok.index)]
        base = int(ok.idxmax())
        d["lv"] = pd.Categorical(d["level"], categories=[base] + [x for x in sorted(ok.index) if x != base])
        try:
            fe = " + C(tid)" if d["tid"].nunique() > 1 else ""
            m1 = smf.wls(f"wr ~ C(lv){fe} + skill + has_hist", data=d, weights=d["n"]).fit(cov_type="cluster", cov_kwds={"groups": d["player_id"].fillna(-1).astype(int)})
            m2 = smf.ols(f"day2 ~ C(lv){fe} + skill + has_hist", data=d).fit(cov_type="cluster", cov_kwds={"groups": d["player_id"].fillna(-1).astype(int)})
        except Exception as e:
            continue
        for L in sorted(ok.index):
            row = {"deck_id": arch, "archetype": names.get(arch, arch), "card": cid, "copies": int(L), "baseline_copies": base,
                   "lists": int(vc[L]), "share_of_archetype": float(vc[L] / len(fa)),
                   "raw_wr": float(d.loc[d["level"] == L, "wr"].mean()), "raw_day2": float(d.loc[d["level"] == L, "day2"].mean())}
            if L == base:
                row.update({"wr_effect": 0.0, "wr_se": 0.0, "wr_p": np.nan, "d2_effect": 0.0, "d2_se": 0.0, "d2_p": np.nan})
            else:
                k = f"C(lv)[T.{L}]"
                row.update({"wr_effect": m1.params.get(k, np.nan), "wr_se": m1.bse.get(k, np.nan), "wr_p": m1.pvalues.get(k, np.nan),
                            "d2_effect": m2.params.get(k, np.nan), "d2_se": m2.bse.get(k, np.nan), "d2_p": m2.pvalues.get(k, np.nan)})
            rows.append(row)
R = pd.DataFrame(rows)
def bh(p):
    p = p.copy(); mask = p.notna(); q = pd.Series(np.nan, index=p.index)
    ps = p[mask].sort_values(); n = len(ps)
    qs = (ps * n / np.arange(1, n + 1))[::-1].cummin()[::-1].clip(upper=1)
    q[qs.index] = qs; return q
R["wr_q"] = bh(R["wr_p"]); R["d2_q"] = bh(R["d2_p"])
R.to_csv(os.path.join(O, "card_count_effects.csv"), index=False)
sig = R[(R["wr_q"] < 0.10) | (R["d2_q"] < 0.10)].sort_values("wr_p")
print(len(R), "level rows;", R.groupby(["deck_id", "card"]).ngroups, "pairs;", len(sig), "significant at q<0.10")
print(sig[["archetype", "card", "copies", "baseline_copies", "lists", "wr_effect", "wr_se", "wr_q", "d2_effect", "d2_q"]].head(40).round(4).to_string())
