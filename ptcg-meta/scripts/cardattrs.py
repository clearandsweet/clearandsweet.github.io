"""Card attribute helpers shared by the models."""
import os, re, json
import pandas as pd

def load_attrs(D):
    cm = pd.read_csv(os.path.join(D, "processed", "cards.csv"), dtype={"number": str}).set_index("card_key")
    lc = json.load(open(os.path.join(D, "cards", "limitless_cache.json")))
    out = {}
    for key, r in cm.iterrows():
        sub = str(r["subtypes"]) if isinstance(r["subtypes"], str) else ""
        sup = r["supertype"] if isinstance(r["supertype"], str) else ""
        hp = r["hp"]; types = r["types"] if isinstance(r["types"], str) else ""
        if not sup:  # JP-only card: use Limitless type line
            l = lc.get(f'jp|{r["set"]}|{r["number"]}') or lc.get(f'en|{r["set"]}|{r["number"]}') or {}
            tl = (l.get("type_line") or "")
            sup = "Pokémon" if tl.startswith("Pok") else ("Energy" if "Energy" in tl else "Trainer")
            sub = tl.split("-", 1)[1].strip() if "-" in tl else ""
            m = re.search(r"(\d+) HP", " ".join(l.get("text") or []))
            hp = float(m.group(1)) if m else None
        subs = [s.strip() for s in re.split(r"[,/]", sub) if s.strip()]
        is_pok = sup.startswith("Pok")
        stage = 0 if "Basic" in subs else 1 if "Stage 1" in subs else 2 if "Stage 2" in subs else (0 if is_pok else None)
        rule_box = is_pok and any(s in subs for s in ("ex", "MEGA", "V", "VSTAR", "VMAX", "Radiant"))
        out[key] = {"name": r["name"], "cat": r["cat"], "supertype": sup, "subtypes": subs, "is_pokemon": is_pok,
                    "stage": stage, "is_basic": is_pok and stage == 0, "rule_box": bool(rule_box),
                    "is_ex": is_pok and "ex" in subs, "is_mega": is_pok and "MEGA" in subs,
                    "hp": float(hp) if hp == hp and hp not in (None, "") else None, "types": types.split(",") if types else [],
                    "retreat": r["retreat"] if r["retreat"] == r["retreat"] else None,
                    "is_item": "Item" in subs, "is_supporter": "Supporter" in subs, "is_tool": "Pokémon Tool" in subs,
                    "is_stadium": "Stadium" in subs, "legal_post": int(r["legal_post"]), "marks": r["marks"]}
    return out
