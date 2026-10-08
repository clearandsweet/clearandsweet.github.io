"""Monte Carlo 'access' simulator for a 60-card list.

For each simulated game: shuffle, mulligan until a Basic is in the opening 7, set aside 6 Prizes,
then by the end of your turn t you have 'seen' the opening hand plus the top (draws_t + DIG[t]) cards
of the remaining deck, where draws_t = t (going second) or t-1 (going first) and DIG is the cumulative
extra digging from draw Supporters/Abilities. A target card is *accessible* at turn t if a copy is seen,
or an eligible searcher is seen and is 'free' (Bernoulli alpha: searchers also have other jobs).
All knobs live in PARAMS so they can be calibrated against the eye test.
"""
import numpy as np

PARAMS = {
    "dig": [4, 8, 12, 15, 18, 21, 24, 27],   # cumulative extra cards seen by end of own turn 1..8
    "n_sims": 600,
}

def _pok(a): return a["is_pokemon"]
SEARCHERS = {
    # name: (eligibility(target_attrs) -> bool, alpha, copies fetched per use)
    "Ultra Ball": (lambda a: _pok(a), 0.5, 1),
    "Nest Ball": (lambda a: a["is_basic"], 0.7, 1),
    "Buddy-Buddy Poffin": (lambda a: a["is_basic"] and (a["hp"] or 999) <= 70, 0.8, 2),
    "Poké Pad": (lambda a: _pok(a) and not a["rule_box"], 0.5, 1),
    "Dawn": (lambda a: _pok(a), 0.45, 1),
    "Cyrano": (lambda a: a["is_ex"], 0.6, 2),
    "Brock's Scouting": (lambda a: _pok(a), 0.45, 1),
    "Hilda": (lambda a: _pok(a) and a["stage"] in (1, 2), 0.4, 1),
    "Fighting Gong": (lambda a: a["is_basic"] and "Fighting" in a["types"], 0.5, 1),
    "Telepathic Psychic Energy": (lambda a: a["is_basic"] and "Psychic" in a["types"], 0.7, 2),
    "Lumiose City": (lambda a: a["is_basic"], 0.3, 1),
    "Fan Rotom": (lambda a: _pok(a) and "Colorless" in a["types"] and (a["hp"] or 999) <= 100, 0.8, 3),
    "Genesect ex": (lambda a: _pok(a) and a["stage"] in (1, 2) and "Metal" in a["types"], 0.8, 2),
    "Bug Catching Set": (lambda a: _pok(a) and "Grass" in a["types"], 0.35, 1),
    "Team Rocket's Petrel": (lambda a: _pok(a), 0.25, 1),
}
SUPPORTER_FINDERS = {"Meowth ex": 0.3, "Pokégear 3.0": 0.3, "Tatsugiri": 0.15}
POKEMON_SUPPORTERS = {"Dawn", "Brock's Scouting", "Cyrano", "Hilda"}

def build_deck(rows, attrs):
    """rows: iterable of (card_key, count). Returns arrays."""
    keys = []
    for k, c in rows:
        keys += [k] * int(c)
    keys = keys[:60] + ["__filler__"] * max(0, 60 - len(keys))
    return keys

def simulate(rows, attrs, targets, rng, n=None, max_turn=6):
    """Returns {target_name: dict(prized_all, acc_first[t], acc_second[t], acc_np_first[t], acc_np_second[t],
    count_first[t], count_second[t])} for t = 1..max_turn. Target identified by card_key."""
    n = n or PARAMS["n_sims"]
    keys = build_deck(rows, attrs)
    A = [attrs.get(k, {"is_pokemon": False, "is_basic": False, "name": k}) for k in keys]
    names = np.array([a.get("name", k) for a, k in zip(A, keys)])
    is_basic = np.array([bool(a.get("is_basic")) for a in A])
    perm = np.argsort(rng.random((n, 60)), axis=1)
    for _ in range(6):  # mulligans
        bad = ~is_basic[perm[:, :7]].any(axis=1)
        if not bad.any():
            break
        perm[bad] = np.argsort(rng.random((bad.sum(), 60)), axis=1)
    # rank[sim, card] : 0 if in opening hand, 99 if prized, else 1.. position in draw pile
    rank = np.empty((n, 60), dtype=np.int16)
    rows_idx = np.arange(n)[:, None]
    pos_rank = np.concatenate([np.zeros(7, np.int16), np.full(6, 99, np.int16), np.arange(1, 48, dtype=np.int16)])
    rank[rows_idx, perm] = pos_rank[None, :]
    dig = PARAMS["dig"]
    horizon_first = np.array([(t - 1) + dig[t - 1] for t in range(1, max_turn + 1)])
    horizon_second = np.array([t + dig[t - 1] for t in range(1, max_turn + 1)])
    deck_names = set(names.tolist())
    out = {}
    for tk in targets:
        ta = attrs.get(tk)
        if ta is None:
            continue
        copies = np.array([k == tk for k in keys])
        ncop = int(copies.sum())
        if ncop == 0:
            continue
        r_direct = rank[:, copies]                                  # n x ncop
        prized_all = (r_direct == 99).all(axis=1)
        # searchers
        s_ranks, s_mult = [], []
        for j, nm in enumerate(names):
            if nm in SEARCHERS:
                elig, alpha, mult = SEARCHERS[nm]
                if elig(ta):
                    free = rng.random(n) < alpha
                    s_ranks.append(np.where(free, rank[:, j], 99)); s_mult.append(mult)
            elif nm in SUPPORTER_FINDERS and ta["is_pokemon"] and (deck_names & POKEMON_SUPPORTERS):
                free = rng.random(n) < SUPPORTER_FINDERS[nm]
                s_ranks.append(np.where(free, rank[:, j], 99)); s_mult.append(1)
        S = np.stack(s_ranks, axis=1) if s_ranks else np.full((n, 1), 99, np.int16)
        M = np.array(s_mult) if s_mult else np.array([0])
        avail = (r_direct != 99).sum(axis=1)                        # unprized copies
        # a searcher can only find the card if at least one copy is still in the deck
        first_access = np.where(avail > 0, np.minimum(r_direct.min(axis=1), S.min(axis=1)), 99)
        res = {"copies": ncop, "prized_all": float(prized_all.mean()), "p_prized_any": float((r_direct == 99).any(axis=1).mean())}
        for label, hz in (("first", horizon_first), ("second", horizon_second)):
            acc = (first_access[:, None] <= hz[None, :])            # n x T
            res[f"acc_{label}"] = acc.mean(axis=0).round(4).tolist()
            notpr = ~prized_all
            res[f"acc_np_{label}"] = (acc[notpr].mean(axis=0).round(4).tolist() if notpr.any() else [0] * len(hz))
            cnt_direct = (r_direct[:, :, None] <= hz[None, None, :]).sum(axis=1)
            cnt_search = ((S[:, :, None] <= hz[None, None, :]) * M[None, :, None]).sum(axis=1)
            cnt = np.minimum(cnt_direct + cnt_search, avail[:, None])
            res[f"count_{label}"] = cnt.mean(axis=0).round(3).tolist()
        out[tk] = res
    return out
