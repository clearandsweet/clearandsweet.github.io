"""Fitted CE weights (from regress.py) and helpers to price a component dict with them."""
import os, json
import pandas as pd
import model_config as C
def groups(comp):
    return C.group_units(comp)

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
