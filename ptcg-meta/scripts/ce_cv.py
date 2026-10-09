"""How much do the hand-set CE weights help? Leave-one-card-out cross-validation of the stage-2 fit
(per-copy measured value ~ marginal resource components) under different prior strengths:
  null      intercept + ACE flag only
  hand      intercept + one scale on hand-set CE + ACE flag
  tau=x     Bayesian fit with prior N(s*hand, (s*x)^2) around the hand weights (regress.py uses tau=1)
  data      no prior (data-only)
Also writes the cards that drive each data-only weight.
Usage: python3 -I ce_cv.py DATADIR
"""
import os, sys, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model_config as MC
D = sys.argv[1]; O = os.path.join(D, "out")
G = list(MC.COMPONENT_GROUPS); G2 = G + ["ace"]
CB = pd.read_csv(os.path.join(O, "card_value_per_copy.csv")).set_index("card")
MV = pd.read_csv(os.path.join(O, "card_marginal_components.csv")).set_index("card")
HW = np.array([MC.HAND_WEIGHTS[g] for g in G])
ANCHOR = G.index("tutor"); ANCHOR_CE = 1.5

def wls(X, y, w):
    W = np.sqrt(w)
    b, *_ = np.linalg.lstsq(X * W[:, None], y * W, rcond=None)
    r = y - X @ b
    XtWX = (X * w[:, None]).T @ X
    s2 = float(np.sum(w * r ** 2) / max(len(y) - X.shape[1], 1))   # same as statsmodels WLS (as in regress.py)
    V = s2 * np.linalg.pinv(XtWX)
    return b, V

def fit(Xc, y, w, tau):
    """Xc: n x len(G2) components. Returns coefficient vector incl. intercept."""
    X = np.column_stack([np.ones(len(y)), Xc])
    if tau == "null":
        Xn = np.column_stack([np.ones(len(y)), Xc[:, -1]])
        b, _ = wls(Xn, y, w)
        return lambda Z: b[0] + b[1] * Z[:, -1]
    if tau == "hand":
        Xh = np.column_stack([np.ones(len(y)), Xc[:, :len(G)] @ HW, Xc[:, -1]])
        b, _ = wls(Xh, y, w)
        return lambda Z: b[0] + b[1] * (Z[:, :len(G)] @ HW) + b[2] * Z[:, -1]
    b, V = wls(X, y, w)
    if tau == "data":
        return lambda Z: np.column_stack([np.ones(len(Z)), Z]) @ b
    s = b[1 + ANCHOR] / ANCHOR_CE
    if s <= 0:                       # anchor not identified in this fold: fall back to the hand scale fit
        Xh = np.column_stack([np.ones(len(y)), Xc[:, :len(G)] @ HW]); bh, _ = wls(Xh, y, w); s = bh[1]
    pm = np.concatenate([[b[0]], s * HW, [b[-1]]])
    pv = np.concatenate([[1e6], np.full(len(G), (s * tau) ** 2), [1e6]])
    Vi = np.linalg.pinv(V); Pi = np.diag(1 / pv)
    post = np.linalg.solve(Vi + Pi, Vi @ b + Pi @ pm)
    return lambda Z: np.column_stack([np.ones(len(Z)), Z]) @ post

rows, drivers = [], []
for ycol, secol, tag in (("wr_per_copy", "wr_per_copy_se", "wr"), ("d2_pp_per_copy", "d2_se", "d2")):
    d = CB.join(MV[G2], how="inner")
    d = d[np.isfinite(d[ycol]) & np.isfinite(d[secol]) & (d[secol] > 0)]
    Xc, y, w = d[G2].values, d[ycol].values, 1 / d[secol].values ** 2
    # how much of the spread in measured values is real (not sampling noise)?
    ybar = np.average(y, weights=w)
    tot = np.average((y - ybar) ** 2, weights=w)
    noise = np.average(d[secol].values ** 2, weights=w)
    for tau in ["null", "hand", 0.25, 0.5, 1.0, 2.0, 4.0, "data"]:
        pred = np.empty(len(y))
        for i in range(len(y)):
            m = np.ones(len(y), bool); m[i] = False
            f = fit(Xc[m], y[m], w[m], tau)
            pred[i] = f(Xc[i:i + 1])[0]
        mse = np.average((y - pred) ** 2, weights=w)
        rows.append({"outcome": tag, "model": str(tau), "oos_mse": mse,
                     "oos_r2_vs_total": 1 - mse / tot, "oos_r2_of_real_signal": 1 - (mse - noise) / max(tot - noise, 1e-12)})
    # drivers of each data-only weight: each card's share of the information about that component
    for g in G:
        x = d[d[g] != 0]
        if not len(x): continue
        info = w[d.index.get_indexer(x.index)] * x[g].values ** 2
        for (cid, r), sh in zip(x.iterrows(), info / info.sum()):
            drivers.append({"outcome": tag, "group": g, "card": cid, "name": r["name"], "avg_copies": r["avg_copies"],
                            "lists": r["lists"], "component_per_copy": r[g], "measured_pts_per_copy": r[ycol] * 100,
                            "measured_se": r[secol] * 100, "info_share": sh})
CV = pd.DataFrame(rows)
CV.to_csv(os.path.join(O, "ce_cv.csv"), index=False)
DR = pd.DataFrame(drivers).sort_values(["outcome", "group", "info_share"], ascending=[True, True, False])
DR.to_csv(os.path.join(O, "ce_weight_drivers.csv"), index=False)
print(CV.round(4).to_string())
