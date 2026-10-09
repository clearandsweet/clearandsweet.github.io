"""Fitted CE weights (from regress.py) and helpers to price a component dict with them."""
import os, json
import pandas as pd
import model_config as C
RAW2G = {raw: g for g, raws in C.COMPONENT_GROUPS.items() for raw in raws}

def groups(comp):
    v = {}
    for k, x in comp.items():
        g = RAW2G.get(k)
        if g is None: continue
        if g == "cost": x = abs(x)
        if g in ("damage_100hp", "heal_100hp"): x = x / 100
        v[g] = v.get(g, 0) + x
    return v

def load(D):
    p = os.path.join(D, "out", "ce_weights_fitted.csv")
    if not os.path.exists(p): return None
    w = pd.read_csv(p).set_index("group")["fitted_weight"].to_dict()
    meta = json.load(open(os.path.join(D, "out", "ce_fit_meta.json")))
    return {"w": w, "avg_sup": meta.get("avg_supporter_components", {}), "u": 0.85}

def price(comp, fit, supporter=False, net_of_slot=False):
    gv = groups(comp)
    ce = sum(fit["w"].get(g, 0) * x for g, x in gv.items())
    if supporter and net_of_slot:
        ce -= fit["u"] * sum(fit["w"].get(g, 0) * x for g, x in fit["avg_sup"].items())
    return ce
