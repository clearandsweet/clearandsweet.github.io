"""Support play-down, Budew/item lock, engine usage, Advantage stat and damage value.
Usage: python3 -I models.py DATADIR [WINDOW=CUR] [MAX_LISTS_PER_ARCH=250]
"""
import json, os, sys, math
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cardattrs import load_attrs
from access_sim import simulate
from engine_model import sim_list_rows, engine_uses
import ce_weights
import model_config as C

D = sys.argv[1]; WIN = sys.argv[2] if len(sys.argv) > 2 else "CUR"
CAP = int(sys.argv[3]) if len(sys.argv) > 3 else 250
POP = sys.argv[4] if len(sys.argv) > 4 else "all"        # 'all' or 'day2': which field the lists AND opponents come from
TAG = WIN if POP == "all" else f"{WIN}_{POP}"
O = os.path.join(D, "out"); P = os.path.join(D, "processed")
attrs = load_attrs(D)
ev = pd.read_csv(os.path.join(O, "events_windows.csv"), dtype={"tid": str})
tids = set(ev.loc[ev["window"] == WIN, "tid"])
pl = pd.read_csv(os.path.join(P, "players.csv"), dtype={"tid": str})
pl = pl[pl["tid"].isin(tids) & (pl["has_list"] == 1)].copy()
if POP == "day2":
    pl = pl[pl["day2"] == 1].copy()
lc = pd.read_csv(os.path.join(P, "list_cards.csv"), dtype={"tid": str, "number": str})
lc = lc[lc["tid"].isin(tids)]
lc["uid"] = lc["tid"] + ":" + lc["tp_id"].astype(str)
pl["uid"] = pl["tid"] + ":" + pl["tp_id"].astype(str)
lists = {u: g for u, g in lc.groupby("uid")}
pl = pl[pl["uid"].isin(lists)]
N = len(pl)
share = pl["deck_id"].value_counts() / N
names_of = {u: set(g["name"]) for u, g in lists.items()}

def subtype_count(g, pred):
    return sum(c for k, c in zip(g["card_key"], g["count"]) if pred(attrs.get(k, {})))

# ---------- opponent features per archetype ----------
feat = {}
for d, grp in pl.groupby("deck_id"):
    us = grp["uid"].tolist()
    items, dragon, pok, stad, exatk = [], [], [], [], []
    has = lambda S: np.mean([bool(names_of[u] & S) for u in us])
    for u in us:
        g = lists[u]
        items.append(subtype_count(g, lambda a: a.get("is_item")))
        stad.append(subtype_count(g, lambda a: a.get("is_stadium")))
        pk = subtype_count(g, lambda a: a.get("is_pokemon"))
        dr = subtype_count(g, lambda a: a.get("is_pokemon") and "Dragon" in a.get("types", []))
        ex = subtype_count(g, lambda a: a.get("is_pokemon") and a.get("rule_box") and (a.get("hp") or 0) >= 200)
        dragon.append(dr / max(pk, 1)); exatk.append(ex / max(pk, 1))
    feat[d] = {"items": float(np.mean(items)), "dragon": float(np.mean(dragon)), "stadiums": float(np.mean(stad)),
               "ex_attackers": float(np.mean(exatk)), "bench_snipe": float(has(C.SPREAD_OR_SNIPE)),
               "cursed_blast": float(has(C.CURSED_BLAST)), "munkidori": float(has(C.COUNTER_MOVERS))}
featdf = pd.DataFrame(feat).T
featdf["share"] = share
featdf.sort_values("share", ascending=False).to_csv(os.path.join(O, f"opponent_features_{TAG}.csv"))
field_items = float((featdf["items"] * featdf["share"]).sum())

def desire(card, opp, own=None):
    s = C.SUPPORT[card]; d = s.get("by_arch", {}).get(own, s["desire"]); f = feat[opp]
    for m, mult in s.get("mods", {}).items():
        if m == "items_low":
            d *= (mult if f["items"] < 12 else 1.0)
        elif m == "dragon":
            d *= 1 + (mult - 1) * min(1.0, f["dragon"] / 0.35)
        elif m == "stadiums":
            d *= 1 + (mult - 1) * min(1.0, f["stadiums"] / 3)
        elif m == "ex_attackers":
            d *= 1 + (mult - 1) * min(1.0, f["ex_attackers"] / 0.3)
        else:
            d *= 1 + (mult - 1) * f[m]
    return min(d, 1.0)
opp_ids = share.index.tolist(); opp_w = share.values
_dcache = {}
def desire_field(card, own=None):
    k = (card, own)
    if k not in _dcache:
        _dcache[k] = float(sum(w * desire(card, o, own) for o, w in zip(opp_ids, opp_w)))
    return _dcache[k]

# ---------- simulate a sample of lists ----------
rng = np.random.default_rng(7)
sample = pl.sample(frac=1, random_state=1).groupby("deck_id").head(CAP)
SUP_NAMES = set(C.SUPPORT) | set(C.ENGINES)
sim_rows = []
for _, p in sample.iterrows():
    for row in sim_list_rows(lists[p["uid"]], attrs, rng, SUP_NAMES):
        sim_rows.append({"uid": p["uid"], "deck_id": p["deck_id"], "day2": p["day2"], "topcut": p["topcut"], **row})
S = pd.DataFrame(sim_rows)
S.to_csv(os.path.join(O, f"sim_support_{TAG}.csv.gz"), index=False, compression="gzip")
print("simulated", sample.shape[0], "lists;", len(S), "support rows", flush=True)

# ---------- support play-down ----------
def horizon(card, side):
    h = C.SUPPORT[card]["horizon"]
    return h[side] if isinstance(h, dict) else h
inc = {}
for nm in C.SUPPORT:
    has = pl["uid"].map(lambda u: nm in names_of[u])
    inc[nm] = {"all": has.mean(), "day2": has[pl["day2"] == 1].mean(), "topcut": has[pl["topcut"] == 1].mean() if (pl["topcut"] == 1).any() else np.nan,
               "by_arch": has.groupby(pl["deck_id"]).mean()}
out = []
for nm, grp in S.groupby("name"):
    if nm not in C.SUPPORT: continue
    rowsum = {}
    for side in ("first", "second"):
        h = horizon(nm, side)
        grp = grp.assign(**{f"acc_{side}": grp[f"acc_{side}_{h}"], f"accnp_{side}": grp[f"accnp_{side}_{h}"]})
    acc = (grp["acc_first"] + grp["acc_second"]) / 2
    accnp = (grp["accnp_first"] + grp["accnp_second"]) / 2
    drow = grp["deck_id"].map(lambda d: desire_field(nm, d))
    # archetype-weighted (by number of lists actually running the card)
    w = grp["deck_id"].map(pl.groupby("deck_id").size()) * grp["deck_id"].map(inc[nm]["by_arch"]) / grp["deck_id"].map(grp.groupby("deck_id").size())
    wavg = lambda s: float(np.average(s, weights=w))
    p_play = wavg(acc * drow)
    dfield = wavg(drow)
    by_arch = grp.assign(pp=acc * drow).groupby("deck_id")["pp"].mean()
    face = float(sum(share.get(d, 0) * inc[nm]["by_arch"].get(d, 0) * by_arch.get(d, 0) for d in by_arch.index))
    out.append({"card": nm, "field_inclusion": inc[nm]["all"], "day2_inclusion": inc[nm]["day2"], "topcut_inclusion": inc[nm]["topcut"],
                "avg_copies": wavg(grp["copies"]), "p_all_copies_prized": wavg(grp["prized_all"]),
                "horizon_turn": str(C.SUPPORT[nm]["horizon"]), "p_accessible_by_horizon": wavg(acc),
                "p_accessible_if_not_prized": wavg(accnp), "desire_vs_field": dfield,
                "p_played_if_in_deck": p_play, "p_played_if_in_deck_not_prized": wavg(accnp * drow),
                "p_opponent_plays_it_random_round": face,
                "top_archetypes": "; ".join(f"{d} {inc[nm]['by_arch'][d]:.0%}" for d in inc[nm]["by_arch"].sort_values(ascending=False).index[:4] if share.get(d, 0) > 0.01)})
SP = pd.DataFrame(out).sort_values("p_opponent_plays_it_random_round", ascending=False)
# per-archetype breakdown (only combos with >= 15 simulated lists)
ba = []
for nm, grp in S.groupby("name"):
    if nm not in C.SUPPORT: continue
    for d, g in grp.groupby("deck_id"):
        if len(g) < 15: continue
        df = desire_field(nm, d)
        acc = ((g[f"acc_first_{horizon(nm, 'first')}"] + g[f"acc_second_{horizon(nm, 'second')}"]) / 2).mean()
        accnp = ((g[f"accnp_first_{horizon(nm, 'first')}"] + g[f"accnp_second_{horizon(nm, 'second')}"]) / 2).mean()
        ba.append({"card": nm, "deck_id": d, "lists_simulated": len(g), "inclusion_in_archetype": float(inc[nm]["by_arch"].get(d, np.nan)),
                   "avg_copies": g["copies"].mean(), "p_all_copies_prized": g["prized_all"].mean(), "p_accessible": acc,
                   "desire": df, "p_played_if_in_deck": acc * df, "p_played_if_not_prized": accnp * df,
                   "archetype_share": float(share.get(d, 0))})
pd.DataFrame(ba).sort_values(["card", "archetype_share"], ascending=[True, False]).to_csv(os.path.join(O, f"support_playdown_by_archetype_{TAG}.csv"), index=False)
SP.to_csv(os.path.join(O, f"support_playdown_{TAG}.csv"), index=False)

# ---------- Budew / item lock ----------
def has_name(nm, sub):
    return sub["uid"].map(lambda u: nm in names_of[u])
bud = {}
for popname, sub in (("all", pl), ("day2", pl[pl["day2"] == 1]), ("topcut", pl[pl["topcut"] == 1])):
    if sub.empty: continue
    bud[popname] = {"p_opp_has_budew": float(has_name("Budew", sub).mean()),
                    "avg_budew_copies_when_played": float(lc[lc["uid"].isin(sub["uid"]) & (lc["name"] == "Budew")].groupby("uid")["count"].sum().mean()),
                    "other_item_lock_inclusion": {nm: float(has_name(nm, sub).mean()) for nm in C.ITEM_LOCK if nm != "Budew"}}
B = S[S["name"] == "Budew"]
wB = B["deck_id"].map(pl.groupby("deck_id").size()) / B["deck_id"].map(B.groupby("deck_id").size())
b_first = float(np.average(B["acc_first_2"], weights=wB))    # Budew deck going first attacks on its T2
b_second = float(np.average(B["acc_second_1"], weights=wB))  # Budew deck going second attacks on its T1
d_b = float(np.average([desire_field("Budew", d) for d in B["deck_id"]], weights=wB))
p_has = bud["all"]["p_opp_has_budew"]
# from YOUR perspective: you go first -> opponent (second) can Itchy Pollen on its T1 -> your T2 is locked
lock_you_first = p_has * b_second * d_b
lock_you_second = p_has * b_first * d_b
exp_lock_turns = p_has * d_b * (b_second * C.BUDEW_LOCK_TURNS["second"] + b_first * C.BUDEW_LOCK_TURNS["first"]) / 2
by_arch_budew = (has_name("Budew", pl).groupby(pl["deck_id"]).mean() * share).sort_values(ascending=False)
bud["model"] = {"p_budew_ready_first_attack_when_going_second(T1)": b_second, "p_budew_ready_first_attack_when_going_first(T2)": b_first,
                "p_budew_prized_all_copies": float(np.average(B["prized_all"], weights=wB)), "desire_vs_field": d_b,
                "p_you_are_item_locked_on_your_T2_if_you_go_first": lock_you_first,
                "p_you_are_item_locked_on_your_T2_if_you_go_second": lock_you_second,
                "p_item_locked_T2_any_order": (lock_you_first + lock_you_second) / 2,
                "expected_item_locked_turns_per_game": exp_lock_turns,
                "field_avg_items_per_list": field_items,
                "share_of_field_running_budew_by_archetype": {k: float(v) for k, v in by_arch_budew.head(10).items()}}
json.dump(bud, open(os.path.join(O, f"budew_itemlock_{TAG}.json"), "w"), indent=1)

# ---------- engine usage & Advantage stat (CE per game) ----------
opp_avg = {"dragon_deck": float((share * (featdf["dragon"] >= 0.3).astype(float)).sum()),
           "cursed_blast": float((share * featdf["cursed_blast"]).sum()),
           "munkidori": float((share * featdf["munkidori"]).sum()),
           "ex_attackers": float((share * (featdf["ex_attackers"] >= 0.15).astype(float)).sum())}
def value_ce(v, opp_items=field_items):
    ce = 0.0
    for k, x in v.items():
        if k in C.CE: ce += C.CE[k] * x
        elif k == "discard": ce -= C.CE["discard_cost"] * x
        elif k in ("dmg", "heal"): ce += C.dmg_ce(x)
        elif k == "prize_given": ce -= C.PRIZE_TO_CE * x * 0.5   # self-KO of a 1-Prize Pokémon (half the time it would die anyway)
        elif k == "gust": ce += C.GUST_CE * x
        elif k == "item_lock":
            ce += x * (C.ITEM_LOCK_CE_PER_ITEM * min(opp_items, 25) / 60 * 6 + C.ITEM_LOCK_SETUP_PENALTY)
    return ce
FIT = ce_weights.load(D)
eng_rows = []
for _, r in S.iterrows():
    eng = C.ENGINES.get(r["name"])
    if not eng: continue
    uses = engine_uses(eng, r, opp_avg)

    v = eng["value"]
    eng_rows.append({"uid": r["uid"], "deck_id": r["deck_id"], "name": r["name"], "copies": r["copies"], "uses_per_game": uses,
                     "ce_per_use": value_ce(v), "ce_per_game": uses * value_ce(v),
                     "ce_per_use_fitted": ce_weights.price(v, FIT) if FIT else np.nan,
                     "ce_per_game_fitted": uses * ce_weights.price(v, FIT) if FIT else np.nan,
                     "extra_cards_per_game": uses * (v.get("draw", 0) + v.get("tutor", 0) + v.get("select2", 0) - v.get("discard", 0)),
                     "extra_energy_per_game": uses * v.get("accel", 0),
                     "retreat_energy_saved_per_game": uses * v.get("retreat_energy", 0),
                     "item_lock_turns_per_game": uses * v.get("item_lock", 0),
                     "damage_hp_per_game": uses * v.get("dmg", 0), "heal_hp_per_game": uses * v.get("heal", 0)})
E = pd.DataFrame(eng_rows)
E.to_csv(os.path.join(O, f"engine_usage_lists_{TAG}.csv.gz"), index=False, compression="gzip")
w = E["deck_id"].map(pl.groupby("deck_id").size()) / E["deck_id"].map(E.groupby("deck_id").size())
E["w"] = w
eng_sum = E.groupby("name").apply(lambda g: pd.Series({
    "lists_simulated": len(g), "avg_copies": np.average(g["copies"], weights=g["w"]),
    "uses_per_game": np.average(g["uses_per_game"], weights=g["w"]), "ce_per_use": g["ce_per_use"].iloc[0],
    "advantage_ce_per_game": np.average(g["ce_per_game"], weights=g["w"]),
    "ce_per_use_fitted": g["ce_per_use_fitted"].iloc[0],
    "advantage_fitted_ce_per_game": np.average(g["ce_per_game_fitted"], weights=g["w"]) if g["ce_per_game_fitted"].notna().all() else np.nan,
    "extra_cards_per_game": np.average(g["extra_cards_per_game"], weights=g["w"]),
    "extra_energy_per_game": np.average(g["extra_energy_per_game"], weights=g["w"]),
    "retreat_energy_saved_per_game": np.average(g["retreat_energy_saved_per_game"], weights=g["w"]),
    "item_lock_turns_per_game": np.average(g["item_lock_turns_per_game"], weights=g["w"]),
    "damage_hp_per_game": np.average(g["damage_hp_per_game"], weights=g["w"]),
    "heal_hp_per_game": np.average(g["heal_hp_per_game"], weights=g["w"])}), include_groups=False)
eng_sum["field_inclusion"] = [pl["uid"].map(lambda u: n in names_of[u]).mean() for n in eng_sum.index]
eng_sum["meta_advantage_ce_per_100_games"] = eng_sum["advantage_ce_per_game"] * eng_sum["field_inclusion"] * 100
top_key = lc.groupby(["name", "card_key"])["uid"].nunique().reset_index().sort_values("uid", ascending=False).drop_duplicates("name").set_index("name")["card_key"]
eng_sum["legal_post_rotation"] = [int(attrs.get(top_key.get(n), {}).get("legal_post", 0)) for n in eng_sum.index]
eng_sum.sort_values("advantage_ce_per_game", ascending=False).to_csv(os.path.join(O, f"advantage_pokemon_{TAG}.csv"))

# ---------- trainers ----------
seen_frac = 0.68
tr = lc[lc["cat"] == "trainer"].copy()
tr["is_sup"] = tr["card_key"].map(lambda k: attrs.get(k, {}).get("is_supporter", False))
sup_tot = tr[tr["is_sup"]].groupby("uid")["count"].sum()
tr["plays"] = tr["count"] * seen_frac
cap = (6.5 / (sup_tot * seen_frac)).clip(upper=1.0)
tr.loc[tr["is_sup"], "plays"] *= tr.loc[tr["is_sup"], "uid"].map(cap).fillna(1)
trs = tr.groupby("name").agg(lists=("uid", "nunique"), copies=("count", "sum"), plays=("plays", "sum"))
trs["field_inclusion"] = trs["lists"] / N
trs["avg_copies"] = trs["copies"] / trs["lists"]
trs["plays_per_game"] = trs["plays"] / trs["lists"]
trs["ce_per_play"] = [C.TRAINER_CE.get(n, (np.nan, ""))[0] for n in trs.index]
trs["why"] = [C.TRAINER_CE.get(n, (np.nan, ""))[1] for n in trs.index]
trs["advantage_ce_per_game"] = trs["ce_per_play"] * trs["plays_per_game"]
def _fit_play(n):
    comp = C.TRAINER_COMPONENTS.get(n)
    if not (FIT and comp): return np.nan
    return ce_weights.price(comp, FIT)
AVG_SUP_FIT = sum(FIT["w"].get(g, 0) * x for g, x in FIT["avg_sup"].items()) if FIT else np.nan
trs["ce_per_play_fitted"] = [_fit_play(n) for n in trs.index]
_is_sup = [any(attrs[k]["is_supporter"] for k in attrs if attrs[k]["name"] == n) for n in trs.index]
trs["vs_avg_supporter"] = np.where(_is_sup, trs["ce_per_play_fitted"] - AVG_SUP_FIT, np.nan)
trs["advantage_fitted_ce_per_game"] = trs["ce_per_play_fitted"] * trs["plays_per_game"]
trs["meta_fitted_ce_per_100_games"] = trs["advantage_fitted_ce_per_game"] * trs["field_inclusion"] * 100
trs["meta_advantage_ce_per_100_games"] = trs["advantage_ce_per_game"] * trs["field_inclusion"] * 100
trs["type"] = [next((("Supporter" if attrs[k]["is_supporter"] else "Item" if attrs[k]["is_item"] else "Tool" if attrs[k]["is_tool"] else "Stadium" if attrs[k]["is_stadium"] else "") for k in attrs if attrs[k]["name"] == n), "") for n in trs.index]
trs["legal_post_rotation"] = [int(attrs.get(top_key.get(n), {}).get("legal_post", 0)) for n in trs.index]
trs.sort_values("meta_advantage_ce_per_100_games", ascending=False).to_csv(os.path.join(O, f"advantage_trainers_{TAG}.csv"))
print(SP[["card", "field_inclusion", "p_all_copies_prized", "p_accessible_by_horizon", "desire_vs_field", "p_played_if_in_deck", "p_opponent_plays_it_random_round"]].round(3).to_string())
print(json.dumps(bud["model"], indent=1))
print(eng_sum.sort_values("advantage_ce_per_game", ascending=False).round(2).to_string())
