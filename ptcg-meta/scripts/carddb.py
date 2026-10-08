"""Card database: pokemon-tcg-data repo (EN) + Limitless page cache.
Provides lookup by (set code, number), print-group legality now/post-rotation, and card text.
"""
import json, os, glob, re
BASIC_ENERGY = {"Grass Energy", "Fire Energy", "Water Energy", "Lightning Energy", "Psychic Energy",
                "Fighting Energy", "Darkness Energy", "Metal Energy", "Fairy Energy"}
LEGAL_NOW = {"H", "I", "J"}
LEGAL_POST = {"I", "J", "K"}

class CardDB:
    def __init__(self, datadir):
        cdir = os.path.join(datadir, "cards")
        sets = json.load(open(os.path.join(cdir, "sets_en.json")))
        self.code_of = {}
        for s in sets:
            code = s.get("ptcgoCode") or s["id"]
            code = {"PR-SV": "SVP"}.get(code, code)
            self.code_of[s["id"]] = code
        self.by_key = {}
        for f in glob.glob(os.path.join(cdir, "*.json")):
            sid = os.path.basename(f)[:-5]
            if sid not in self.code_of:
                continue
            for c in json.load(open(f)):
                key = (self.code_of[sid], c["number"])
                if key in self.by_key and sid.endswith("c"):
                    continue  # prefer main 30C set over classic collection on collisions
                c["_set"] = self.code_of[sid]
                self.by_key[key] = c
        self.en_codes = set(json.load(open(os.path.join(cdir, "en_codes.json"))))
        cp = os.path.join(cdir, "limitless_cache.json")
        self.lcache = json.load(open(cp)) if os.path.exists(cp) else {}

    def lang_of(self, setc):
        return "en" if setc in self.en_codes else "jp"

    def get(self, setc, num, lang="en"):
        lang = self.lang_of(setc)
        c = self.by_key.get((setc, str(num))) if lang == "en" else None
        return c

    def lim(self, setc, num, lang="en"):
        lang = self.lang_of(setc)
        return self.lcache.get(f"{lang}|{setc}|{num}")

    def mark(self, setc, num, lang="en"):
        c = self.get(setc, num, lang)
        if c and c.get("regulationMark"):
            return c["regulationMark"]
        l = self.lim(setc, num, lang)
        return l.get("mark") if l else None

    def print_marks(self, setc, num, name, lang="en"):
        """Marks of all functional reprints (international), using the Limitless prints table."""
        marks = set()
        m = self.mark(setc, num, lang)
        if m: marks.add(m)
        l = self.lim(setc, num, lang)
        unknown = []
        if l:
            for p in l["prints"]["int"]:
                if p.get("current"):
                    continue
                pm = self.mark(p["set"], p["number"])
                if pm: marks.add(pm)
                else: unknown.append(f'{p["set"]} {p["number"]}')
        return marks, unknown

    def jp_print_sets(self, setc, num, lang="en"):
        l = self.lim(setc, num, lang)
        return [p["set"] for p in l["prints"]["jp"] if not p.get("current")] if l else []

    def status(self, setc, num, name, lang="en"):
        """Returns dict: legal_now, legal_post (international), marks, unknown prints."""
        if name in BASIC_ENERGY:
            return {"legal_now": True, "legal_post": True, "marks": ["basic"], "unknown": []}
        marks, unknown = self.print_marks(setc, num, name, lang)
        return {"legal_now": bool(marks & LEGAL_NOW) or not marks, "legal_post": bool(marks & LEGAL_POST),
                "marks": sorted(marks), "unknown": unknown}

    def text(self, setc, num, lang="en"):
        c = self.get(setc, num, lang)
        if c:
            parts = []
            for a in c.get("abilities", []) or []:
                parts.append(f'[{a.get("type")}] {a["name"]}: {a.get("text","")}')
            for a in c.get("attacks", []) or []:
                cost = "".join(x[0] if x != "Colorless" else "C" for x in a.get("cost", []))
                parts.append(f'[Attack {cost}] {a["name"]} {a.get("damage","")}: {a.get("text","")}')
            for r in c.get("rules", []) or []:
                parts.append(f"[Rule] {r}")
            hp = c.get("hp"); rc = c.get("convertedRetreatCost")
            head = f'{c["name"]} ({c["supertype"]}/{",".join(c.get("subtypes") or [])}) HP{hp} RC{rc} {",".join(c.get("types") or [])} mark {c.get("regulationMark")}'
            return head + "\n   " + "\n   ".join(parts)
        l = self.lim(setc, num, lang)
        return (" | ".join(l["text"]) + f' mark {l.get("mark")}') if l else None
