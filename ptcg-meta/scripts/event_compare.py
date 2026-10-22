"""One event against the rest of its format window: who made Day 2 / top 64 / top cut, how a deck family's share
grew round by round, whether its result came from the field it faced or from how it played, pilot skill, and list changes.
Usage: python3 -I event_compare.py DATADIR [FOCUS_TID=latest|all] [FAMILY_SUP_ID=dragapult-ex]
Writes DATADIR/out/event_*.csv and event_compare.json for the latest (or given) event, and with "all" one folder
DATADIR/out/event/<tid>/ per event of the latest event's format window (the report's event selector).
"""
import os, sys, json
import numpy as np, pandas as pd
from scipy.stats import binomtest
D = sys.argv[1]
FOCUS = sys.argv[2] if len(sys.argv) > 2 else "latest"
FAM = sys.argv[3] if len(sys.argv) > 3 else "dragapult-ex"
O, P = os.path.join(D, "out"), os.path.join(D, "processed")
ev = pd.read_csv(os.path.join(O, "events_windows.csv"), dtype={"tid": str})
OUTD = O
if FOCUS == "all":
    import subprocess
    w = ev.loc[ev["tid"] == ev["tid"].max(), "window"].iloc[0]
    for t in ev.loc[ev["window"] == w, "tid"]:
        subprocess.run([sys.executable, "-I", os.path.abspath(__file__), D, t, FAM, "per-event"], check=True, stdout=subprocess.DEVNULL)
    FOCUS = "latest"
if len(sys.argv) > 4 and sys.argv[4] == "per-event":
    OUTD = os.path.join(O, "event", FOCUS)
    os.makedirs(OUTD, exist_ok=True)
if FOCUS == "latest":
    FOCUS = ev["tid"].max()
WIN = ev.loc[ev["tid"] == FOCUS, "window"].iloc[0]
TIDS = ev.loc[ev["window"] == WIN, "tid"].tolist()
city = dict(zip(ev["tid"], ev["city"]))
pl = pd.read_csv(os.path.join(P, "players.csv"), dtype={"tid": str})
pl["window"] = pl["tid"].map(dict(zip(ev["tid"], ev["window"])))
pl["n"] = pl[["wins", "losses", "ties"]].sum(axis=1)
pl["wr"] = (pl["wins"] + pl["ties"] / 3) / pl["n"].replace(0, np.nan)
pl["fam"] = pl["sup_id"] == FAM
names = pl.drop_duplicates("deck_id").set_index("deck_id")["deck_name"].to_dict()
names.update(pl.drop_duplicates("sup_id").set_index("sup_id")["sup_name"].to_dict())
pm = pd.read_csv(os.path.join(O, "player_matches_long.csv.gz"), dtype={"tid": str})
sup_of = pl.drop_duplicates("deck_id").set_index("deck_id")["sup_id"].to_dict()
W = pl[pl["tid"].isin(TIDS)].copy()
PH = [("field", lambda d: d.index == d.index), ("day2", lambda d: d["day2"] == 1), ("top64", lambda d: d["placement"] <= 64),
      ("top16", lambda d: d["placement"] <= 16), ("top8", lambda d: d["placement"] <= 8)]

# ---------- A. shares by phase, per event and for the rest of the window ----------
rows = []
for tid, g in list(W.groupby("tid")) + [("rest", W[W["tid"] != FOCUS])]:
    for ph, f in PH:
        sub = g[f(g)]
        for level, col in (("family", "sup_id"), ("archetype", "deck_id")):
            vc = sub[col].value_counts()
            for k, c in vc.items():
                rows.append({"tid": tid, "event": city.get(tid, "Other events"), "level": level, "key": k, "name": names.get(k, k),
                             "phase": ph, "count": int(c), "n_phase": int(len(sub)), "share": c / len(sub)})
SH = pd.DataFrame(rows)
SH.to_csv(os.path.join(OUTD, "event_phase_shares.csv"), index=False)

# ---------- B. the family at every event in the window ----------
fam_rows = []
for tid, g in W.groupby("tid"):
    f = g["fam"]; n = len(g); fs = f.mean()
    t64 = g[g["placement"] <= 64]; k64 = int(t64["fam"].sum())
    nm = pm[(pm["tid"] == tid) & (pm["deck"].map(sup_of) == FAM) & (pm["opp_deck"].map(sup_of) != FAM)]
    gw = nm[["w", "l", "t"]].sum()
    win = g.sort_values("placement").iloc[0]
    fam_rows.append({"tid": tid, "event": city[tid], "players": n, "fam_players": int(f.sum()), "field_share": fs,
                     "day2_share": g.loc[g["day2"] == 1, "fam"].mean(), "day2_rate": g.loc[f, "day2"].mean(), "field_day2_rate": g["day2"].mean(),
                     "top64": k64, "top64_expected": fs * 64, "top64_share": k64 / 64, "top64_p": binomtest(k64, 64, fs).pvalue,
                     "top16": int(g.loc[g["placement"] <= 16, "fam"].sum()), "top8": int(g.loc[g["placement"] <= 8, "fam"].sum()),
                     "wr_nonmirror": (gw["w"] + gw["t"] / 3) / gw.sum() if gw.sum() else np.nan, "games_nonmirror": int(gw.sum()),
                     "winner_deck": names.get(win["deck_id"], win["deck_id"]), "focus": int(tid == FOCUS)})
FB = pd.DataFrame(fam_rows)
r = FB[FB["focus"] == 0]
rest = {"top64": int(r["top64"].sum()), "top64_expected": float(r["top64_expected"].sum())}
f0 = FB[FB["focus"] == 1].iloc[0]
# Louisville's top-64 count vs what the other events' conversion (observed / expected) would predict
oe_rest = rest["top64"] / rest["top64_expected"]
FB.to_csv(os.path.join(OUTD, "event_family_by_event.csv"), index=False)

# ---------- C. conversion by archetype at the focus event vs the rest ----------
def conv(g, games):
    out = g.groupby("deck_id").agg(players=("tp_id", "size"), day2=("day2", "sum"), top64=("placement", lambda s: int((s <= 64).sum())),
                                    top16=("placement", lambda s: int((s <= 16).sum())))
    out["share"] = out["players"] / len(g)
    out["day2_rate"] = out["day2"] / out["players"]
    exp64 = pd.concat([e["deck_id"].value_counts() / len(e) * min(64, len(e)) for _, e in g.groupby("tid")]).groupby(level=0).sum()
    out["top64_expected"] = exp64.reindex(out.index).fillna(0)
    nm = games[games["deck"] != games["opp_deck"]].groupby("deck")[["w", "l", "t"]].sum()
    out["wr_nonmirror"] = ((nm["w"] + nm["t"] / 3) / nm.sum(axis=1)).reindex(out.index)
    out["games_nonmirror"] = nm.sum(axis=1).reindex(out.index)
    return out
cf = conv(W[W["tid"] == FOCUS], pm[pm["tid"] == FOCUS])
cr = conv(W[W["tid"] != FOCUS], pm[pm["tid"].isin(TIDS) & (pm["tid"] != FOCUS)])
CV = cf.join(cr, rsuffix="_rest", how="left")
CV["name"] = [names.get(k, k) for k in CV.index]
CV["family"] = [sup_of.get(k) == FAM for k in CV.index]
CV["top64_oe"] = CV["top64"] / CV["top64_expected"].replace(0, np.nan)
CV["top64_oe_rest"] = CV["top64_rest"] / CV["top64_expected_rest"].replace(0, np.nan)
CV["top64_p"] = [binomtest(int(k), 64, s).pvalue for k, s in zip(CV["top64"], CV["share"])]
CV = CV.sort_values("players", ascending=False)
CV.to_csv(os.path.join(OUTD, "event_conversion.csv"))

# ---------- D. round by round: family share among the top 64 by match points ----------
prog = []
for tid in TIDS:
    g = pm[pm["tid"] == tid].sort_values("round")
    if g.empty: continue
    pts = {}
    fam_of = dict(zip(W.loc[W["tid"] == tid, "tp_id"], W.loc[W["tid"] == tid, "fam"]))
    for rnd, gr in g.groupby("round"):
        for p, w, t in zip(gr["player"], gr["w"], gr["t"]):
            pts[p] = pts.get(p, 0) + 3 * w + t
        active = set(gr["player"])
        s = pd.Series(pts)
        s = s[s.index.isin(active)]
        if len(s) < 128: continue                     # top-cut rounds
        fm = np.array([fam_of.get(p, False) for p in s.index], float)
        cut = s.sort_values(ascending=False).iloc[63]
        above, tied = (s > cut).values, (s == cut).values
        # exactly 64 seats: everyone above the cut, plus the tied group pro rata (a random tiebreak on average)
        k = 64 - above.sum()
        fam64 = (fm[above].sum() + fm[tied].mean() * k) / 64
        prog.append({"tid": tid, "event": city[tid], "round": int(rnd), "active": len(s),
                     "share_active": float(fm.mean()), "share_top64": float(fam64), "cut_points": int(cut)})
PR = pd.DataFrame(prog)
PR.to_csv(os.path.join(OUTD, "event_round_progress.csv"), index=False)

# ---------- E. the family's matchups: field mix vs performance ----------
G = pm[pm["tid"].isin(TIDS)].copy()
G = G[(G["deck"].map(sup_of) == FAM) & (G["opp_deck"].map(sup_of) != FAM)]
G["focus"] = G["tid"] == FOCUS
mu = G.groupby(["focus", "opp_deck"])[["w", "l", "t"]].sum()
mu["games"] = mu.sum(axis=1); mu["wr"] = (mu["w"] + mu["t"] / 3) / mu["games"]
mf, mr = mu.loc[True], mu.loc[False]
overall_rest = (mr["w"].sum() + mr["t"].sum() / 3) / mr["games"].sum()
K = 30   # shrink each matchup toward the family's overall rest-of-window win rate
wr_rest_shr = (mr["wr"] * mr["games"] + overall_rest * K) / (mr["games"] + K)
MX = pd.DataFrame({"games_focus": mf["games"], "mix_focus": mf["games"] / mf["games"].sum(), "wr_focus": mf["wr"]}).join(
    pd.DataFrame({"games_rest": mr["games"], "mix_rest": mr["games"] / mr["games"].sum(), "wr_rest": mr["wr"], "wr_rest_shrunk": wr_rest_shr}), how="outer")
MX["wr_rest_shrunk"] = MX["wr_rest_shrunk"].fillna(overall_rest)
MX["name"] = [names.get(k, k) for k in MX.index]
actual_focus = (mf["w"].sum() + mf["t"].sum() / 3) / mf["games"].sum()
expected_focus = float((MX["mix_focus"].fillna(0) * MX["wr_rest_shrunk"]).sum())
MX.sort_values("games_focus", ascending=False).to_csv(os.path.join(OUTD, "event_family_matchups.csv"))

# ---------- F. pilot skill (results at OTHER events, all formats) ----------
pl["arch_mean"] = pl.groupby(["deck_id", "window"])["wr"].transform("mean")
pl["resid"] = pl["wr"] - pl["arch_mean"]
ok = pl["player_id"].notna() & pl["resid"].notna() & (pl["n"] >= 3)
tot = pl[ok].groupby("player_id")["resid"].agg(["sum", "count"])
pl = pl.join(tot, on="player_id")
own = np.where(ok, pl["resid"], 0.0)
pl["n_other"] = pl["count"].fillna(0) - ok.astype(int)
pl["skill"] = (pl["sum"].fillna(0) - own) / (pl["n_other"] + 2)
sk_rows = []
for tid in TIDS:
    g = pl[(pl["tid"] == tid) & (pl["n_other"] > 0)]
    a = pl[pl["tid"] == tid]
    for grp, sub in (("family", g[g["fam"]]), ("rest of field", g[~g["fam"]]), ("family, top 64", g[g["fam"] & (g["placement"] <= 64)]),
                     ("rest, top 64", g[~g["fam"] & (g["placement"] <= 64)])):
        sk_rows.append({"tid": tid, "event": city[tid], "group": grp, "with_history": len(sub),
                        "coverage": len(sub) / max(1, len(a[a["fam"]] if grp.startswith("family") else a[~a["fam"]])),
                        "mean_skill_pts": sub["skill"].mean() * 100, "se_pts": sub["skill"].std() / np.sqrt(max(len(sub), 1)) * 100})
SK = pd.DataFrame(sk_rows)
SK.to_csv(os.path.join(OUTD, "event_pilot_skill.csv"), index=False)

# ---------- G. list changes in the family's main archetype ----------
lc = pd.read_csv(os.path.join(P, "list_cards.csv"), dtype={"tid": str, "number": str})
lc = lc[lc["tid"].isin(TIDS)]
main = FAM
L = W[(W["deck_id"] == main) & (W["has_list"] == 1)][["tid", "tp_id", "placement", "day2"]]
x = lc.merge(L, on=["tid", "tp_id"])
cnt = x.groupby(["tid", "tp_id", "name"])["count"].sum().unstack(fill_value=0)
meta = L.set_index(["tid", "tp_id"]).reindex(cnt.index)
mt = pd.Series(cnt.index.get_level_values("tid"), index=cnt.index)
grp = {"focus": mt == FOCUS, "rest": mt != FOCUS,
       "focus_top64": (mt == FOCUS) & (meta["placement"] <= 64), "focus_other": (mt == FOCUS) & (meta["placement"] > 64)}
LC = pd.DataFrame({f"incl_{k}": (cnt[m.values] > 0).mean() for k, m in grp.items()} | {f"copies_{k}": cnt[m.values].mean() for k, m in grp.items()})
LC["n_focus"], LC["n_rest"], LC["n_focus_top64"] = int(grp["focus"].sum()), int(grp["rest"].sum()), int(grp["focus_top64"].sum())
LC["d_incl"] = LC["incl_focus"] - LC["incl_rest"]; LC["d_copies"] = LC["copies_focus"] - LC["copies_rest"]
LC["d_incl_top64"] = LC["incl_focus_top64"] - LC["incl_focus_other"]
LC = LC[(LC[["incl_focus", "incl_rest"]].max(axis=1) >= 0.05)]
LC.sort_values("d_copies", key=abs, ascending=False).to_csv(os.path.join(OUTD, "event_list_changes.csv"))

# ---------- summary ----------
fs = W[W["tid"] == FOCUS]
summary = {"focus": FOCUS, "event": city[FOCUS], "window": WIN, "family": FAM, "family_name": names.get(FAM, FAM),
           "players": int(len(fs)), "rounds": int(pm.loc[pm["tid"] == FOCUS, "round"].max()),
           "fam": {k: (float(v) if isinstance(v, (float, np.floating)) else int(v) if isinstance(v, (int, np.integer)) else v) for k, v in f0.items()},
           "rest_top64": rest["top64"], "rest_top64_expected": rest["top64_expected"], "rest_top64_oe": oe_rest,
           "focus_top64_oe": float(f0["top64"] / f0["top64_expected"]),
           "focus_top64_if_rest_conversion": float(f0["top64_expected"] * oe_rest),
           "matchups": {"actual_focus": actual_focus, "expected_focus_from_rest": expected_focus, "actual_rest": overall_rest,
                        "games_focus": int(mf["games"].sum()), "games_rest": int(mr["games"].sum())}}
# Day 1 vs Day 2 Swiss rounds (Day 1 = 9 rounds at 17+ round events, else 8; the last 3 rounds are top cut)
x = pm[pm["tid"].isin(TIDS)].copy()
mx = x.groupby("tid")["round"].transform("max")
x["phase"] = np.where(x["round"] <= np.where(mx >= 17, 9, 8), "day1", np.where(x["round"] <= mx - 3, "day2", "topcut"))
x = x[(x["deck"].map(sup_of) == FAM) & (x["opp_deck"].map(sup_of) != FAM) & (x["phase"] != "topcut")]
x["where"] = np.where(x["tid"] == FOCUS, "focus", "rest")
dd = x.groupby(["where", "phase"])[["w", "l", "t"]].sum()
summary["by_day"] = {f"{a}_{b}": {"wr": float((r.w + r.t / 3) / (r.w + r.l + r.t)), "games": int(r.w + r.l + r.t)} for (a, b), r in dd.iterrows()}
# is the focus event's observed/expected top-64 ratio different from the rest? (comparison of two Poisson rates,
# conditional on the total: O_focus ~ Binomial(O_focus + O_rest, E_focus / (E_focus + E_rest)))
O1, E1 = int(f0["top64"]), float(f0["top64_expected"])
summary["top64_ratio_p"] = float(binomtest(O1, O1 + rest["top64"], E1 / (E1 + rest["top64_expected"])).pvalue)
json.dump(summary, open(os.path.join(OUTD, "event_compare.json"), "w"), indent=1, default=float)
pd.set_option("display.width", 250)
print(json.dumps(summary, indent=1, default=float))
print(FB.round(3).to_string())
print(CV.head(25)[["name", "players", "share", "share_rest", "day2_rate", "day2_rate_rest", "top64", "top64_expected", "top64_oe", "top64_oe_rest", "wr_nonmirror", "wr_nonmirror_rest"]].round(3).to_string())
print(PR[PR["tid"] == FOCUS].round(3).to_string())
print(MX.sort_values("games_focus", ascending=False).head(15).round(3).to_string())
print(SK.round(2).to_string())
print(LC.sort_values("d_copies", key=abs, ascending=False).head(25).round(3).to_string())
