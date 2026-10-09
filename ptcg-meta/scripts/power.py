"""Card Power and Deck Power (per game, in CE).

For every list and every card in it:
  effect     CE from Abilities and Trainer effects: resource units per game x CE weights (hand / fitted / data-only)
  offense    Prize progress this card's attacks take: attack share x attacks per game x Prizes per attack,
             where Prizes per attack is measured against the real lists of the same window (Active hits,
             gusted Bench targets, spread KOs; Weakness and Resistance applied)
  liability  Prize progress the opponent takes through this card: the window's attack pool hitting it as the
             Active, as the best gust target on the Bench, or with spread; plus self-KO costs (Cursed Blast)
  power      effect + POWER_CE_PER_PRIZE x (offense - liability)
Deck Power = sum over the 60 cards. Validation: archetype-window means vs non-mirror win rate and Day 2 rate.
Usage: python3 -I power.py DATADIR
"""
import os, sys, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cardattrs import load_attrs
from carddb import CardDB
import model_config as C

D = sys.argv[1]
O, P = os.path.join(D, "out"), os.path.join(D, "processed")
attrs = load_attrs(D)
db = CardDB(D)
rng = np.random.default_rng(5)
P2CE = C.POWER_CE_PER_PRIZE

# ---------------- weights ----------------
G = list(C.COMPONENT_GROUPS)
RAW2G = {raw: g for g, raws in C.COMPONENT_GROUPS.items() for raw in raws}
cw = pd.read_csv(os.path.join(O, "ce_weights_fitted.csv")).set_index("group")
HW_POWER = dict(C.HAND_WEIGHTS, damage_100hp=100 / C.HP_PER_PRIZE * P2CE, heal_100hp=100 / C.HP_PER_PRIZE * P2CE)
WSETS = {"hand": np.array([HW_POWER[g] for g in G]),
         "fitted": np.array([cw.loc[g, "fitted_weight"] for g in G]),
         "data": np.array([cw.loc[g, "data_only_wr"] for g in G])}
def gvec(comp, mult=1.0):
    v = np.zeros(len(G))
    for k, x in comp.items():
        g = RAW2G.get(k)
        if g is None: continue
        x = abs(x) if g == "cost" else x
        if g in ("damage_100hp", "heal_100hp"): x = x / 100
        v[G.index(g)] += x * mult
    return v

# ---------------- card facts ----------------
wr_facts = {}
for (s, n), c in db.by_key.items():
    if c.get("supertype", "").startswith("Pok"):
        wr_facts.setdefault(c["name"], ({w["type"] for w in c.get("weaknesses") or []}, {r["type"] for r in c.get("resistances") or []}))
TYPES = ["Grass", "Fire", "Water", "Lightning", "Psychic", "Fighting", "Darkness", "Metal", "Dragon", "Colorless", "Fairy"]
TI = {t: i for i, t in enumerate(TYPES)}
def pfacts(key):
    a = attrs.get(key, {})
    nm = a.get("name", key)
    weak, res = wr_facts.get(nm, (set(), set()))
    prizes = 3 if a.get("is_mega") else 2 if a.get("is_ex") else 1
    return {"name": nm, "hp": float(a.get("hp") or 70), "prizes": prizes, "types": a.get("types") or [],
            "weak": weak, "resist": res, "stage": a.get("stage") or 0, "dragon": "Dragon" in (a.get("types") or [])}

# ---------------- attackers ----------------
ATK = list(C.ATTACKERS)
AI = {n: i for i, n in enumerate(ATK)}
A_dmg = np.array([C.ATTACKERS[n]["dmg"] for n in ATK], float)
A_type = np.array([TI.get(C.ATTACKERS[n]["type"], TI["Colorless"]) for n in ATK])
A_ignore = np.array([bool(C.ATTACKERS[n].get("ignore_wr")) for n in ATK])
A_fz = np.array([bool(C.ATTACKERS[n].get("fairy_zone")) for n in ATK])
A_exonly = np.array([bool(C.ATTACKERS[n].get("vs_ex_only")) for n in ATK])
A_spread = np.array([C.ATTACKERS[n].get("spread", 0) for n in ATK], float)
alive = np.array(C.P_ALIVE)
def base_attacks(first):
    turns = np.arange(1, 11)
    att = np.where(turns >= first, 1.0, 0.0); att[turns == np.ceil(first)] *= (np.ceil(first) - first + 0.5)
    return float((alive * att).sum())
A_base = np.array([base_attacks(C.ATTACKERS[n]["first"]) for n in ATK])

# ---------------- data ----------------
ev = pd.read_csv(os.path.join(O, "events_windows.csv"), dtype={"tid": str})
win_of = dict(zip(ev["tid"], ev["window"]))
pl = pd.read_csv(os.path.join(P, "players.csv"), dtype={"tid": str})
pl["uid"] = pl["tid"] + ":" + pl["tp_id"].astype(str)
pl["window"] = pl["tid"].map(win_of)
F = pd.read_csv(os.path.join(O, "list_features.csv.gz"), dtype={"tid": str}).set_index("uid")
uses_cols = [c for c in F.columns if c.startswith("uses::")]
lc = pd.read_csv(os.path.join(P, "list_cards.csv"), dtype={"tid": str, "number": str})
lc["uid"] = lc["tid"] + ":" + lc["tp_id"].astype(str)
lc = lc[lc["uid"].isin(F.index)]
spd = pd.read_csv(os.path.join(O, "support_playdown_by_archetype_CUR.csv"))
SP_ARCH = {(r.card, r.deck_id): r.p_played_if_in_deck for r in spd.itertuples()}
SP_CARD = pd.read_csv(os.path.join(O, "support_playdown_CUR.csv")).set_index("card")["p_played_if_in_deck"].to_dict()
legal = {k: a.get("legal_post", 1) for k, a in attrs.items()}

# ---------------- per-list profile ----------------
def build(uid, g, deck_id):
    """Return the per-card table (effect resources) and the Pokémon target profile of one list."""
    cards = []
    tr = g[g["cat"] == "trainer"]
    sup_cnt = sum(c for k, c in zip(tr["card_key"], tr["count"]) if attrs.get(k, {}).get("is_supporter"))
    sup_scale = min(1.0, 6.5 / max(sup_cnt * 0.68, 1e-9))
    fr = F.loc[uid]
    # aggregate by name (Pokémon: the most-copied print gives the facts)
    by = {}
    for cat, k, nm, c in zip(g["cat"], g["card_key"], g["name"], g["count"]):
        e = by.setdefault((cat, nm), {"cat": cat, "name": nm, "copies": 0, "key": k, "kc": 0})
        e["copies"] += c
        if c > e["kc"]: e["key"], e["kc"] = k, c
    for (cat, nm), e in by.items():
        e["legal"] = int(legal.get(e["key"], 1))
        res = np.zeros(len(G))
        if cat == "trainer" and nm in C.TRAINER_COMPONENTS:
            a = attrs.get(e["key"], {})
            res = gvec(C.TRAINER_COMPONENTS[nm], e["copies"] * 0.68 * (sup_scale if a.get("is_supporter") else 1.0))
        elif cat == "energy" and nm in C.ENERGY_COMPONENTS:
            res = gvec(C.ENERGY_COMPONENTS[nm], e["copies"] * C.ENERGY_PLAYS_PER_COPY)
        elif cat == "pokemon" and nm in C.ENGINES:
            u = float(fr.get(f"uses::{nm}", 0) or 0)
            val = C.ENGINES[nm]["value"]
            if nm in C.POWER_SKIP_ENGINE_DMG:
                val = {k: x for k, x in val.items() if k != "dmg"}
            res = gvec(val, u)
            e["uses"] = u
        e["res"] = res
        cards.append(e)
    # Pokémon profile
    pk = [e for e in cards if e["cat"] == "pokemon"]
    for e in pk: e.update(pfacts(e["key"]))
    att = [e for e in pk if e["name"] in AI]
    if att:
        wts = np.array([e["copies"] * C.ATTACKERS[e["name"]]["cadence"] for e in att], float)
        for e, w in zip(att, wts / wts.sum()): e["atk_share"] = w
    else:
        cand = [e for e in pk if e["copies"] >= 2] or pk
        if cand:
            max(cand, key=lambda e: e["hp"])["atk_share"] = 0.0
            max(cand, key=lambda e: e["hp"])["default_active"] = True
    # presence on the board mid-game
    stage_names = {}
    for e in pk: stage_names.setdefault(e["stage"], []).append(e)
    for e in pk:
        n = int(min(4, e["copies"]))
        if e["name"] in C.SUPPORT:
            q = SP_ARCH.get((e["name"], deck_id), SP_CARD.get(e["name"], 0.6))
        elif e.get("atk_share", 0) > 0:
            q = C.P_ON_BOARD[min(4, max(0, n - 1))] if n > 1 else 0.3     # a second copy powering up on the Bench
        else:
            q = C.P_ON_BOARD[n]
        if e["stage"] < 2 and e["name"] not in C.SUPPORT:                 # lower stages evolve away
            nxt = sum(x["copies"] for x in stage_names.get(e["stage"] + 1, []))
            if nxt: q *= max(0.25, 1 - nxt / max(e["copies"], 1))
        e["q"] = float(q)
    # Active share: attackers (and Budew while it attacks)
    act = {e["name"]: e.get("atk_share", 0.0) + (1.0 if e.get("default_active") else 0.0) for e in pk}
    bud = next((e for e in pk if e["name"] == "Budew"), None)
    return cards, pk, act, bud

def target_arrays(pk):
    hp = np.array([e["hp"] for e in pk]); pr = np.array([e["prizes"] for e in pk], float)
    weak = np.zeros((len(pk), len(TYPES)), bool); res = np.zeros((len(pk), len(TYPES)), bool)
    for i, e in enumerate(pk):
        for t in e["weak"]:
            if t in TI: weak[i, TI[t]] = True
        for t in e["resist"]:
            if t in TI: res[i, TI[t]] = True
    drag = np.array([e["dragon"] for e in pk])
    return hp, pr, weak, res, drag

def prog_matrix(hp, pr, weak, res, drag):
    """Prize progress per hit (targets x attackers) and the gust value (a sure KO counts in full, a partial hit half)."""
    dmg = np.where(A_exonly[None, :] & (pr[:, None] == 1), 20.0, A_dmg[None, :])
    w = weak[:, A_type] | (A_fz[None, :] & drag[:, None])
    mult = np.where(w & ~A_ignore[None, :], 2.0, 1.0)
    eff = np.maximum(dmg * mult - np.where(res[:, A_type] & ~A_ignore[None, :], 30.0, 0.0), 0)
    frac = np.minimum(1.0, eff / hp[:, None])
    return frac * pr[:, None], np.where(frac >= 1, 1.0, 0.5 * frac) * pr[:, None]

def gust_alloc(vg, v, q):
    """Gust the most valuable available target (ordered by vg); returns the progress (v) attributed to each."""
    out = np.zeros(len(v)); rem = 1.0
    for i in np.argsort(-vg):
        out[i] = rem * q[i] * v[i]; rem *= (1 - q[i])
    return out

def _leftover(dmg, hp, pr, q):
    if dmg <= 0 or q.sum() <= 0: return np.zeros(len(hp))
    hpp = (q * hp).sum() / max((q * pr).sum(), 1e-9)
    return (q * pr / (q * pr).sum()) * dmg * C.SPREAD_CONVERSION / hpp

def spread_alloc(j, hp, pr, q):
    """Bench damage of attacker j: counters (cheapest Prize first) or aimed snipes; non-KO damage converts at SPREAD_CONVERSION."""
    out = np.zeros(len(hp))
    nm = ATK[j]
    if nm in C.SNIPE:
        dmg, n = C.SNIPE[nm]
        ko = np.nonzero(hp <= dmg)[0]
        dist = np.zeros(n + 1); dist[0] = 1.0                      # P(k KO-able targets already taken)
        for i in ko[np.argsort(-(pr[ko]))]:
            p_take = q[i] * dist[:n].sum()
            out[i] += p_take * pr[i]
            nd = dist.copy()
            for kk in range(n):
                moved = q[i] * dist[kk]; nd[kk] -= moved; nd[kk + 1] += moved
            dist = nd
        unused = float(sum(dist[k] * (n - k) for k in range(n + 1)))
        return out + _leftover(dmg * unused, hp, pr, q)
    rem = A_spread[j]
    for i in np.argsort(hp / pr):
        if hp[i] <= rem and q[i] > 0:
            out[i] += q[i] * pr[i]; rem -= q[i] * hp[i]
    return out + _leftover(rem, hp, pr, q)

# ---------------- pass 1: profiles for every list ----------------
lists = {u: g for u, g in lc.groupby("uid")}
meta = pl[pl["uid"].isin(lists)].set_index("uid")
PROF = {}
for uid in F.index:
    if uid not in lists or uid not in meta.index: continue
    cards, pk, act, bud = build(uid, lists[uid], meta.at[uid, "deck_id"])
    PROF[uid] = (cards, pk, act, bud)
print("profiles", len(PROF), flush=True)

# window meta: attack pool, attacks per game, gust rate
WIN = {}
for w, grp in meta.loc[list(PROF)].groupby("window"):
    pool = np.zeros(len(ATK)); A = []
    for uid in grp.index:
        cards, pk, act, bud = PROF[uid]
        a_l = 0.0
        for e in pk:
            s = e.get("atk_share", 0)
            if s > 0:
                pool[AI[e["name"]]] += s; a_l += s * A_base[AI[e["name"]]]
        A.append(a_l)
    pool /= pool.sum()
    A_opp = float(np.mean(A))
    p_g = float(min(0.6, F.loc[grp.index, "gust"].mean() / A_opp))
    WIN[w] = {"pool": pool, "A_opp": A_opp, "p_gust": p_g, "uids": list(grp.index)}
    print(w, "lists", len(grp), "attacks/game", round(A_opp, 2), "p_gust", round(p_g, 3),
          "top attackers", ", ".join(f"{ATK[i]} {pool[i]:.2f}" for i in np.argsort(-pool)[:5]), flush=True)

# offense: Prizes per attack of every attacker vs a sample of the window's real lists
PPA = {}
for w, M in WIN.items():
    samp = rng.choice(M["uids"], size=min(1500, len(M["uids"])), replace=False)
    acc = np.zeros(len(ATK)); acc_act = np.zeros(len(ATK)); acc_g = np.zeros(len(ATK)); acc_s = np.zeros(len(ATK))
    for uid in samp:
        cards, pk, act, bud = PROF[uid]
        if not pk: continue
        hp, pr, weak, res, drag = target_arrays(pk)
        PM, PG = prog_matrix(hp, pr, weak, res, drag)
        a = np.array([act[e["name"]] for e in pk]); a = a / a.sum() if a.sum() > 0 else a
        q = np.array([e["q"] for e in pk])
        active = a @ PM
        gust = np.array([gust_alloc(PG[:, j], PM[:, j], q).sum() for j in range(len(ATK))])
        spr = np.array([spread_alloc(j, hp, pr, q).sum() if A_spread[j] > 0 else 0.0 for j in range(len(ATK))])
        acc_act += active; acc_g += gust; acc_s += spr
    n = len(samp)
    PPA[w] = {"active": acc_act / n, "gust": acc_g / n, "spread": acc_s / n,
              "ppa": (1 - M["p_gust"]) * acc_act / n + M["p_gust"] * acc_g / n + acc_s / n}

# ---------------- pass 2: per-card power for every list ----------------
rows, lrows = [], []
for uid, (cards, pk, act, bud) in PROF.items():
    w = meta.at[uid, "window"]; M = WIN[w]; pool = M["pool"]
    # liability per opponent attack
    lia = {}
    if pk:
        hp, pr, weak, res, drag = target_arrays(pk)
        PM, PG = prog_matrix(hp, pr, weak, res, drag)
        v, vg = PM @ pool, PG @ pool
        q = np.array([e["q"] for e in pk])
        a = np.array([act[e["name"]] for e in pk]); a = a / a.sum() if a.sum() > 0 else a
        if bud is not None:
            bshare = min(0.35, C.BUDEW_ACTIVE_SHARE * bud.get("uses", 0) / M["A_opp"])
            a = a * (1 - bshare); a[pk.index(bud)] += bshare
        g_att = gust_alloc(vg, v, q)
        s_att = np.zeros(len(pk))
        for j in np.nonzero(A_spread > 0)[0]:
            s_att += pool[j] * spread_alloc(j, hp, pr, q)
        for e, x1, x2, x3 in zip(pk, (1 - M["p_gust"]) * a * v, M["p_gust"] * g_att, s_att):
            lia[e["name"]] = (x1 * M["A_opp"], x2 * M["A_opp"], x3 * M["A_opp"])
    for e in cards:
        nm = e["name"]
        off = 0.0
        if e.get("atk_share", 0) > 0:
            j = AI[nm]; off = e["atk_share"] * A_base[j] * PPA[w]["ppa"][j]
        la, lg, ls = lia.get(nm, (0.0, 0.0, 0.0)) if e["cat"] == "pokemon" else (0.0, 0.0, 0.0)
        lself = e.get("uses", 0) * C.ENGINES[nm]["value"]["prize_given"] if nm in C.ENGINES and "prize_given" in C.ENGINES[nm]["value"] else 0.0
        r = {"uid": uid, "window": w, "deck_id": meta.at[uid, "deck_id"], "cat": e["cat"], "name": nm, "copies": e["copies"],
             "legal_post": e["legal"], "offense_raw": off, "lia_active_raw": la, "lia_gust_raw": lg, "lia_spread_raw": ls, "lia_self": lself,
             "active_weight": act.get(nm, 0.0) if e["cat"] == "pokemon" else 0.0,
             "hp": e.get("hp"), "prizes": e.get("prizes"), "q_board": e.get("q"), "attack_share": e.get("atk_share", 0.0)}
        for ws, W_ in WSETS.items():
            r[f"effect_{ws}"] = float(e["res"] @ W_)
        r["dmgheal_units"] = float(e["res"][G.index("damage_100hp")] + e["res"][G.index("heal_100hp")])
        rows.append(r)
CP = pd.DataFrame(rows)
# realization: scale Prize progress so the window's mean offense per list equals PRIZES_TAKEN_PER_GAME
off_list = CP.groupby(["window", "uid"])["offense_raw"].sum().groupby("window").mean()
KAPPA = (C.PRIZES_TAKEN_PER_GAME / off_list).to_dict()
k = CP["window"].map(KAPPA)
CP["offense_prizes"] = CP["offense_raw"] * k
CP["lia_hits"] = (CP["lia_active_raw"] + CP["lia_gust_raw"] + CP["lia_spread_raw"]) * k
# a copy can only be Knocked Out once: cap each card at Prizes x copies on the board, hand the excess to the Active attackers
CP["lia_cap"] = np.where(CP["active_weight"] > 0, CP["prizes"] * CP["copies"], CP["prizes"] * CP["copies"] * CP["q_board"]).astype(float)
CP["lia_excess"] = np.maximum(0, CP["lia_hits"] - CP["lia_cap"].fillna(0))
ex = CP.groupby("uid")["lia_excess"].transform("sum")
aw = CP["active_weight"] / CP.groupby("uid")["active_weight"].transform("sum").replace(0, np.nan)
CP["liability_prizes"] = np.minimum(CP["lia_hits"], CP["lia_cap"].fillna(0)) + (ex * aw).fillna(0) + CP["lia_self"]
# a deck cannot take, or give up, more than 6 Prizes in a game
for col in ("offense_prizes", "liability_prizes"):
    tot = CP.groupby("uid")[col].transform("sum")
    CP[col] *= np.minimum(1.0, 6.0 / tot.replace(0, np.nan)).fillna(1.0)
for ws in WSETS:
    CP[f"power_{ws}"] = CP[f"effect_{ws}"] + P2CE * (CP["offense_prizes"] - CP["liability_prizes"])
CP.to_csv(os.path.join(O, "power_cards_all.csv.gz"), index=False, compression="gzip")

# ---------------- deck totals ----------------
agg = {f"effect_{ws}": "sum" for ws in WSETS} | {f"power_{ws}": "sum" for ws in WSETS} | {"offense_prizes": "sum", "liability_prizes": "sum", "dmgheal_units": "sum"}
DL = CP.groupby("uid").agg(agg)
for ws in WSETS:
    DL[f"power_H_{ws}"] = CP[CP["legal_post"] == 0].groupby("uid")[f"power_{ws}"].sum().reindex(DL.index).fillna(0)
    DL[f"effect_H_{ws}"] = CP[CP["legal_post"] == 0].groupby("uid")[f"effect_{ws}"].sum().reindex(DL.index).fillna(0)
DL["offense_H"] = CP[CP["legal_post"] == 0].groupby("uid")["offense_prizes"].sum().reindex(DL.index).fillna(0)
DL = DL.join(meta[["window", "deck_id", "day2", "player_id", "tid"]])
DL = DL.join(F[["W", "L", "T"]])
DL.to_csv(os.path.join(O, "power_lists.csv.gz"), compression="gzip")
meta_out = {w: {"attacks_per_game": M["A_opp"], "p_gust": M["p_gust"], "kappa": KAPPA[w],
                "attack_pool": {ATK[i]: round(float(M["pool"][i]), 4) for i in np.argsort(-M["pool"]) if M["pool"][i] > 0.002}}
            for w, M in WIN.items()}
PP = pd.DataFrame({w: PPA[w]["ppa"] for w in PPA}, index=ATK)
PP.index.name = "attacker"
PP.to_csv(os.path.join(O, "power_prizes_per_attack.csv"))
json.dump(meta_out, open(os.path.join(O, "power_meta.json"), "w"), indent=1)
print("cards rows", len(CP), "lists", len(DL))
print(DL.groupby("window")[[f"power_{ws}" for ws in WSETS] + ["offense_prizes", "liability_prizes"]].mean().round(2).to_string())
