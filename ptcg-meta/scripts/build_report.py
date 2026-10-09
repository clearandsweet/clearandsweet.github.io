"""Assemble out/*.csv|json into a single JSON payload and inject it into the report template.
Usage: python3 -I build_report.py DATADIR TEMPLATE OUTPUT_HTML
"""
import json, os, sys, math
import numpy as np, pandas as pd
D, TPL, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
O = os.path.join(D, "out")
def rd(f, **k):
    p = os.path.join(O, f)
    return pd.read_csv(p, **k) if os.path.exists(p) else pd.DataFrame()
def recs(df, cols=None, n=None, rnd=4):
    if df.empty: return []
    if cols: df = df[[c for c in cols if c in df.columns]]
    if n: df = df.head(n)
    df = df.replace([np.inf, -np.inf], np.nan)
    out = []
    for r in df.to_dict("records"):
        out.append({k: (None if (isinstance(v, float) and math.isnan(v)) else (round(v, rnd) if isinstance(v, float) else v)) for k, v in r.items()})
    return out
summary = json.load(open(os.path.join(O, "summary.json")))
ev = rd("events_windows.csv", dtype={"tid": str})
P = {}
P["generated"] = "2026-10-08"
P["windows"] = summary["windows"]
P["events"] = recs(ev, ["tid", "type", "city", "date", "players", "n_lists", "window"])
arch = rd("archetypes_CUR.csv")
surv = rd("archetype_survivability_CUR.csv")
if not surv.empty:
    arch = arch.merge(surv[["deck_id", "tier", "avg_rotating_cards", "namesake", "namesake_rotating", "core_rotating_cards"]], on="deck_id", how="left")
P["archetypes"] = recs(arch, ["rank", "deck_id", "name", "players", "share", "day2", "day2_rate", "day2_rate_lo", "day2_rate_hi", "day2_lift", "day2_lift_shrunk",
                              "topcut", "topcut_rate", "wr_all", "wr_nonmirror", "wr_nonmirror_se", "games_nonmirror", "tier", "avg_rotating_cards",
                              "namesake", "namesake_rotating", "core_rotating_cards"], n=100)
P["archetypes_worlds"] = recs(rd("archetypes_WORLDS.csv"), ["deck_id", "name", "players", "share", "day2", "day2_rate", "day2_lift", "topcut", "wr_nonmirror"], n=40)
P["superarchetypes"] = recs(rd("superarchetypes_CUR.csv"), ["sup_id", "name", "players", "share", "day2_rate", "day2_lift", "wr_nonmirror"], n=40)
P["archetypes_post_g_all"] = recs(rd("archetypes_post_G_rotation_all.csv"), ["deck_id", "name", "players", "share", "day2_lift", "wr_nonmirror"], n=60)
inv = rd("card_inventory_CUR.csv")
_top = inv.sort_values("lists", ascending=False).drop_duplicates("name").set_index("name")["marks"].to_dict()
P["marks_by_name"] = {k: (v if isinstance(v, str) else "") for k, v in _top.items()}
P["cards"] = recs(inv, ["card_key", "name", "cat", "lists", "inclusion", "avg_copies", "inclusion_day2", "inclusion_topcut", "day2_lift", "marks", "legal_post"], n=400)
P["n_cards_seen"] = int(len(inv))
P["replacements"] = recs(rd("rotation_replacements_CUR.csv"), n=60)
tiers = surv.groupby(surv["tier"].str.split(" ").str[0]).agg(archetypes=("deck_id", "size"), share=("share", "sum")).reset_index() if not surv.empty else pd.DataFrame()
P["tiers"] = recs(tiers)
P["projection"] = recs(rd("post_rotation_naive_projection_CUR.csv"), ["deck_id", "name", "share", "day2_lift", "tier", "avg_rotating_cards", "proj_share_naive"], n=25)
for tag in ("CUR", "CUR_day2"):
    p = os.path.join(O, f"budew_itemlock_{tag}.json")
    if os.path.exists(p): P[f"budew_{tag}"] = json.load(open(p))
P["support"] = recs(rd("support_playdown_CUR.csv"))
P["support_day2"] = recs(rd("support_playdown_CUR_day2.csv"))
sba = rd("support_playdown_by_archetype_CUR.csv")
if not sba.empty:
    names = rd("archetypes_CUR.csv").set_index("deck_id")["name"]
    sba["archetype"] = sba["deck_id"].map(names).fillna(sba["deck_id"])
P["support_by_arch"] = recs(sba)
P["pokemon_rank"] = recs(rd("pokemon_rankings_CUR.csv"))
P["engines"] = recs(rd("advantage_pokemon_CUR.csv"))
tr = rd("advantage_trainers_CUR.csv")
cvf = rd("card_value_fit.csv")
if not tr.empty and not cvf.empty:
    tr = tr.merge(cvf[["name", "measured_wr", "predicted_wr", "residual_wr"]].drop_duplicates("name"), on="name", how="left")
P["trainers"] = recs(tr[tr["ce_per_play"].notna()] if not tr.empty else tr, ["name", "type", "field_inclusion", "avg_copies", "plays_per_game", "ce_per_play", "why",
                                                                            "advantage_ce_per_game", "meta_advantage_ce_per_100_games", "ce_per_play_fitted",
                                                                            "vs_avg_supporter", "advantage_fitted_ce_per_game", "meta_fitted_ce_per_100_games",
                                                                            "measured_wr", "predicted_wr", "residual_wr", "legal_post_rotation"], n=90)
P["damage"] = recs(rd("damage_value_CUR.csv"))
P["defenders"] = recs(rd("defender_pool_CUR.csv"), ["deck_id", "defender", "hp", "prizes", "share"], n=30)
dm = os.path.join(O, "damage_meta_CUR.json")
P["damage_meta"] = json.load(open(dm)) if os.path.exists(dm) else {}
jpm = json.load(open(os.path.join(D, "cards", "jp_print_marks.json")))
P["jp_reprints_H"] = sum(1 for v in jpm.values() if v == "H")
P["jp_reprints_legal"] = sum(1 for v in jpm.values() if v in ("I", "J", "K"))
P["n_matches"] = int(sum(1 for _ in open(os.path.join(D, "processed", "matches.csv"))) - 1)
mu = rd("matchups_CUR.csv")
P["matchups"] = recs(mu)
P["opp_features"] = recs(rd("opponent_features_CUR.csv").rename(columns={"Unnamed: 0": "deck_id"}), n=30)
cv = rd("card_value_per_copy.csv")
if not cv.empty:
    cv = cv[cv["within_arch_sd"] > 0.12].copy()
    cv["type"] = [("Pokémon" if "[" in str(c) else "Trainer/Energy") for c in cv["card"]]
P["card_values"] = recs(cv, ["card", "name", "type", "merged_with", "lists", "avg_copies", "within_arch_sd", "wr_per_copy", "wr_per_copy_se",
                             "d2_pp_per_copy", "d2_se", "legal_post"])
cnt = rd("card_count_effects.csv")
P["count_effects"] = recs(cnt, ["deck_id", "archetype", "card", "copies", "baseline_copies", "lists", "share_of_archetype", "raw_wr", "raw_day2",
                                "wr_effect", "wr_se", "wr_q", "d2_effect", "d2_se", "d2_q"])
P["copy_curves"] = recs(rd("engine_copy_curves.csv"))
P["ce_weights"] = recs(rd("ce_weights_fitted.csv"))
P["ce_listlevel"] = recs(rd("ce_fit_listlevel.csv"))
P["card_value_fit"] = recs(cvf)
fm = os.path.join(O, "ce_fit_meta.json")
P["ce_meta"] = json.load(open(fm)) if os.path.exists(fm) else {}
jp = os.path.join(O, "jp_summary.json")
P["jp"] = json.load(open(jp)) if os.path.exists(jp) else {}
P["jp_new_cards"] = recs(rd("jp_cityleague_new_cards.csv"), n=25)
P["share_by_event"] = recs(rd("archetype_share_by_event.csv").rename(columns={"Unnamed: 0": "deck_id", "deck_id": "deck_id"}), n=400)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model_config as C
P["knobs"] = {"P_ALIVE": C.P_ALIVE, "PRIZE_TO_CE": C.PRIZE_TO_CE, "CE": C.CE, "BUDEW_LOCK_TURNS": C.BUDEW_LOCK_TURNS,
              "SUPPORT": C.SUPPORT, "dig": __import__("access_sim").PARAMS["dig"]}
tpl = open(TPL).read()
html = tpl.replace("/*__DATA__*/null", json.dumps(P, ensure_ascii=False, default=float))
open(OUT, "w").write(html)
print("wrote", OUT, round(len(html) / 1024), "KB")
