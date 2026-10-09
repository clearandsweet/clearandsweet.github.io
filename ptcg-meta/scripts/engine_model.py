"""Shared engine logic: per-list simulation rows and expected uses per game for Ability/Attack engines.
Used by models.py (report tables) and features.py (regression features) so both use identical math."""
import numpy as np
import model_config as C
from access_sim import simulate

def sim_list_rows(g, attrs, rng, target_names, n=None):
    """g: DataFrame of one list (card_key, name, count). Returns list of dicts, one per target card_key."""
    rows = list(zip(g["card_key"], g["count"]))
    targets = [k for k in g["card_key"].unique() if attrs.get(k, {}).get("name") in target_names]
    if not targets:
        return []
    pre = set()
    for k in targets:
        a = attrs[k]
        if a.get("stage") in (1, 2):
            pre |= {kk for kk in g["card_key"] if attrs.get(kk, {}).get("is_pokemon") and attrs[kk]["stage"] < a["stage"]}
    res = simulate(rows, attrs, targets + list(pre), rng, n=n, max_turn=8)
    grass = int(g.loc[g["name"] == "Grass Energy", "count"].sum())
    metal = int(g.loc[g["name"] == "Metal Energy", "count"].sum())
    candy = int(g.loc[g["name"] == "Rare Candy", "count"].sum())
    out = []
    for k in targets:
        r = res.get(k)
        if not r: continue
        a = attrs[k]
        lag_cnt = {}
        for side in ("first", "second"):
            cnt = np.array(r[f"count_{side}"])
            if a.get("stage") in (1, 2):
                basics = [kk for kk in res if attrs[kk]["stage"] == 0 and kk not in targets]
                need = 1 if (a["stage"] == 1 or candy) else 2
                if basics:
                    bc = np.array(res[basics[0]][f"count_{side}"]) if len(basics) == 1 else np.max([res[b][f"count_{side}"] for b in basics], axis=0)
                    prev = np.concatenate([np.zeros(need), bc[:-need]])
                    cnt = np.minimum(cnt, prev)
                else:
                    cnt = np.concatenate([np.zeros(need), cnt[:-need]])
            lag_cnt[side] = cnt.round(3).tolist()
        out.append({"card_key": k, "name": a["name"], "copies": r["copies"], "prized_all": r["prized_all"],
                    **{f"acc_first_{t+1}": v for t, v in enumerate(r["acc_first"])},
                    **{f"acc_second_{t+1}": v for t, v in enumerate(r["acc_second"])},
                    **{f"accnp_first_{t+1}": v for t, v in enumerate(r["acc_np_first"])},
                    **{f"accnp_second_{t+1}": v for t, v in enumerate(r["acc_np_second"])},
                    **{f"inplay_first_{t+1}": v for t, v in enumerate(lag_cnt["first"])},
                    **{f"inplay_second_{t+1}": v for t, v in enumerate(lag_cnt["second"])},
                    "grass": grass, "metal": metal})
    return out

ALIVE = np.array(C.P_ALIVE[:8])

def trigger_vec(eng, row, opp_avg):
    t = eng["trigger"]
    if isinstance(t, (int, float)): return np.full(8, float(t))
    if t == "grass_in_hand":
        g = max(row["grass"], 0); return np.full(8, 1 - (1 - min(g, 30) / 45) ** 6)
    if t == "metal_top4":
        m = max(row["metal"], 0); return np.full(8, 4 * m / 45)        # expected Metal Energy attached per use
    if t == "ko_last_turn":
        return np.array([0, 0, 0.35, 0.55, 0.6, 0.6, 0.6, 0.6])
    if t == "dragon_opp": return np.full(8, opp_avg["dragon_deck"])
    if t == "cursed_blast_opp": return np.full(8, opp_avg["cursed_blast"])
    if t == "munkidori_opp": return np.full(8, opp_avg["munkidori"])
    if t == "ex_opp": return np.full(8, opp_avg["ex_attackers"] * 0.5)
    return np.full(8, 0.5)

def engine_uses(eng, r, opp_avg):
    """Expected uses per game for the whole set of copies in the list (not per copy)."""
    trig = trigger_vec(eng, r, opp_avg)
    vals = []
    for side in ("first", "second"):
        inplay = np.array([r[f"inplay_{side}_{t}"] for t in range(1, 9)])
        surv = eng.get("surv", 0.92) ** np.maximum(0, np.arange(1, 9) - 2)
        decay = np.maximum(0, 1 - eng.get("decay", 0) * np.maximum(0, np.arange(1, 9) - 2))
        n_on = np.minimum(inplay, eng["cap"]) * surv * decay
        kind = eng["kind"]
        if kind == "turn" and eng["trigger"] == "grass_in_hand":
            eg = max(6 * min(r["grass"], 30) / 45, trig[0])          # expected basic Grass in hand
            uses = (ALIVE * np.minimum(n_on, eg)).sum()
        elif kind == "turn":
            uses = (ALIVE * n_on * trig).sum()
        elif kind in ("turn1", "passive", "attack"):
            uses = (ALIVE * np.minimum(n_on, 1) * trig).sum()
            if kind == "attack":
                uses = min(uses, C.BUDEW_LOCK_TURNS[side]) if r["name"] == "Budew" else min(uses, 2)
        elif kind == "early_attack":
            base = list(eng.get("turn_weights", [1, 0.5, 0.2]))
            tw = np.array(([0] + base if side == "first" else base) + [0] * 8)[:8]   # going first: no attack on turn 1
            uses = float((np.minimum(inplay, 1) * tw).sum())
        elif kind == "play":
            uses = float(np.max(np.minimum(inplay, eng["cap"]))) * trig[0]
        elif kind == "first":
            uses = float(min(inplay[0], 1)) * trig[0]
        vals.append(uses)
    return min(float(np.mean(vals)), eng.get("max_uses", 99))
