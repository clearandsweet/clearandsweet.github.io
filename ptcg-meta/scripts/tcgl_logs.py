"""Parse Pokémon TCG Live battle logs (text copied from the post-game Battle Log) and measure, per game and player:
first turn each Pokémon entered play, Ability uses, attacks, Items/Supporters played per turn, Item-locked turns,
KOs and Prizes. The aggregate output is what the play-down and engine-usage simulations are calibrated against.

Usage:  python3 -I tcgl_logs.py LOG_DIR OUT_DIR
        LOG_DIR holds .txt files; one file may contain several games separated by blank-line-delimited "Setup" blocks.
Patterns are deliberately tolerant; unmatched lines are counted and written to OUT_DIR/unparsed_lines.txt so the
regexes can be tightened against real logs.
"""
import os, re, sys, json, glob, collections
TURN = re.compile(r"^Turn\s*#\s*(\d+)\s*-\s*(.+?)['’]s Turn", re.I)
FIRST = re.compile(r"^(.+?) decided to go (first|second)", re.I)
WON_TOSS = re.compile(r"^(.+?) won the coin toss", re.I)
TO_BENCH = re.compile(r"^(.+?) played (.+?) to the Bench", re.I)
TO_ACTIVE = re.compile(r"^(.+?) played (.+?) to the Active Spot", re.I)
EVOLVE = re.compile(r"^(.+?) evolved (.+?) (?:in)?to (.+?)(?: on the Bench| in the Active Spot)?\.?$", re.I)
ATTACK = re.compile(r"^(.+?)['’]s (.+?) used (.+?) on (.+?)['’]s (.+?) for (\d+) damage", re.I)
ATTACK_NODMG = re.compile(r"^(.+?)['’]s (.+?) used (.+?) on (.+?)['’]s (.+?)\.?$", re.I)
ABILITY = re.compile(r"^(.+?)['’]s (.+?) used (.+?)\.?$", re.I)
TRAINER = re.compile(r"^(.+?) played (.+?)\.?$", re.I)
KO = re.compile(r"^(.+?)['’]s (.+?) was Knocked Out", re.I)
PRIZE = re.compile(r"^(.+?) took (a|an|\d+) Prize card", re.I)
END = re.compile(r"^(.+?) (?:wins|won)\b|^(.+?) conceded|Opponent conceded", re.I)
DRAW = re.compile(r"^(.+?) drew (a card|\d+ cards)", re.I)

def split_games(text):
    blocks, cur = [], []
    for line in text.splitlines():
        if line.strip().lower() == "setup" and cur:
            blocks.append(cur); cur = []
        cur.append(line)
    if cur: blocks.append(cur)
    return [b for b in blocks if any(TURN.match(l.strip()) for l in b)]

def parse_game(lines, item_names=None, supporter_names=None):
    item_names = item_names or set(); supporter_names = supporter_names or set()
    g = {"players": {}, "first": None, "turns": [], "unparsed": []}
    turn, who = 0, None
    def P(name):
        return g["players"].setdefault(name, {"in_play_turn": {}, "abilities": collections.Counter(), "attacks": collections.Counter(),
                                              "items_by_turn": collections.Counter(), "supporters_by_turn": collections.Counter(),
                                              "trainers": collections.Counter(), "kos_taken": 0, "prizes": 0, "locked_turns": []})
    last_lock_by = None
    for raw in lines:
        l = raw.strip().lstrip("-•· ").strip()
        if not l: continue
        m = TURN.match(l)
        if m:
            turn, who = int(m.group(1)), m.group(2).strip(); P(who)
            if last_lock_by and last_lock_by != who:
                P(who)["locked_turns"].append(turn)
            last_lock_by = None if last_lock_by == who else last_lock_by
            continue
        if (m := FIRST.match(l)):
            name, choice = m.group(1).strip(), m.group(2).lower(); P(name)
            g["first"] = name if choice == "first" else None
            g["_chooser"] = (name, choice); continue
        for rx, kind in ((TO_BENCH, "bench"), (TO_ACTIVE, "active")):
            if (m := rx.match(l)):
                p = P(m.group(1).strip())
                for poke in re.split(r",| and ", m.group(2)):
                    poke = poke.strip()
                    if poke: p["in_play_turn"].setdefault(poke, turn)
                break
        else:
            if (m := EVOLVE.match(l)):
                P(m.group(1).strip())["in_play_turn"].setdefault(m.group(3).strip(), turn); continue
            if (m := ATTACK.match(l)) or (m := ATTACK_NODMG.match(l)):
                p = P(m.group(1).strip()); atk = m.group(3).strip()
                p["attacks"][f"{m.group(2).strip()}::{atk}"] += 1
                if atk.lower() in ("itchy pollen", "oceanic gloom", "disconnect", "fulgurite"):
                    last_lock_by = m.group(1).strip()
                continue
            if (m := ABILITY.match(l)):
                P(m.group(1).strip())["abilities"][f"{m.group(2).strip()}::{m.group(3).strip()}"] += 1; continue
            if (m := KO.match(l)):
                continue
            if (m := PRIZE.match(l)):
                n = 1 if m.group(2).lower() in ("a", "an") else int(m.group(2))
                P(m.group(1).strip())["prizes"] += n; continue
            if (m := TRAINER.match(l)):
                p = P(m.group(1).strip()); card = m.group(2).strip()
                p["trainers"][card] += 1
                if card in item_names: p["items_by_turn"][turn] += 1
                if card in supporter_names: p["supporters_by_turn"][turn] += 1
                continue
            if DRAW.match(l) or END.match(l) or WON_TOSS.match(l):
                continue
            g["unparsed"].append(l)
    if g["first"] is None and g.get("_chooser"):
        name, choice = g["_chooser"]
        others = [p for p in g["players"] if p != name]
        g["first"] = others[0] if (choice == "second" and others) else name
    return g

def main(log_dir, out_dir, item_names=None, supporter_names=None):
    os.makedirs(out_dir, exist_ok=True)
    games, unparsed = [], []
    for f in sorted(glob.glob(os.path.join(log_dir, "*.txt"))):
        for b in split_games(open(f, encoding="utf-8", errors="replace").read()):
            g = parse_game(b, item_names, supporter_names); g["file"] = os.path.basename(f)
            unparsed += g.pop("unparsed"); games.append(g)
    # aggregate: share of games each Pokémon entered play by turn t (per player-game), ability uses per game
    played_by = collections.defaultdict(lambda: collections.Counter()); appear = collections.Counter()
    abil = collections.Counter(); n_pg = 0; locked = collections.Counter()
    for g in games:
        for name, p in g["players"].items():
            n_pg += 1
            for poke, t in p["in_play_turn"].items():
                appear[poke] += 1
                for T in range(1, 9):
                    if t <= T * 2: played_by[poke][T] += 1   # log turns count both players; own turn T ~ log turn 2T-1/2T
            for k, v in p["abilities"].items(): abil[k.split("::")[1]] += v
            locked[len(p["locked_turns"])] += 1
    summary = {"games": len(games), "player_games": n_pg,
               "pokemon_in_play_rate": {k: round(v / max(n_pg, 1), 4) for k, v in appear.most_common(80)},
               "pokemon_in_play_by_own_turn": {k: {T: round(c / max(n_pg, 1), 4) for T, c in sorted(v.items())} for k, v in played_by.items() if appear[k] >= 3},
               "ability_uses_per_player_game": {k: round(v / max(n_pg, 1), 3) for k, v in abil.most_common(60)},
               "item_locked_turns_distribution": dict(locked), "unparsed_lines": len(unparsed)}
    json.dump(summary, open(os.path.join(out_dir, "log_summary.json"), "w"), indent=1)
    json.dump(games, open(os.path.join(out_dir, "games_parsed.json"), "w"), default=dict)
    open(os.path.join(out_dir, "unparsed_lines.txt"), "w").write("\n".join(unparsed))
    return summary

if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1], sys.argv[2]), indent=1)[:3000])
