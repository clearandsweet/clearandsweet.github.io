"""All tunable assumptions for the play-down / advantage / damage models live here.
Units: CE = 'card equivalent' (the value of drawing one random card from your deck).
"""
# Probability the game is still running at the start of your own turn t (t = 1..10).
P_ALIVE = [1.0, 1.0, 1.0, 1.0, 0.92, 0.78, 0.60, 0.40, 0.22, 0.10]
PRIZE_TO_CE = 10.0         # 1 Prize ~ 10 CE: picked by cross-validating Deck Power against archetype results (power_eval.py)
HP_PER_PRIZE = 140.0       # meta-weighted HP you must chew through per Prize (recomputed from data when possible)
REALIZATION = 0.6          # share of raw damage progress that turns into Prizes (heals, retreats, games ending); measured in power.py
# Price list: CE per unit of each resource. Every Ability, attack effect and Trainer is priced from these and nothing else.
CE = {
    "draw": 1.0,           # draw 1 random card
    "select2": 1.25,       # look at 2, keep 1
    "tutor": 1.5,          # search 1 specific card
    "recover": 1.25,       # 1 card back from the discard pile
    "accel": 1.0,          # one Energy attachment beyond your one per turn (tempo)
    "energy_card": 1.0,    # an Energy that went into play without coming from your hand (the card itself)
    "retreat_energy": 2.0, # each Energy you didn't discard to retreat (= the card + re-attaching it)
    "gust": 2.0,           # pick the opponent's Active (the regression prices a gust at ~1.4 searches)
    "opp_card": 0.7,       # each card removed from / reset in the opponent's hand
    "energy_denial": 2.0,  # each opposing Energy removed (their card + their attachment)
    "item_lock": 1.8,      # each turn the opponent can't play Items
    "evo_tempo": 2.5,      # an evolution turn skipped
    "dmg": PRIZE_TO_CE * REALIZATION / HP_PER_PRIZE,    # per HP of damage (100 HP ~ 4.3 CE)
    "heal": PRIZE_TO_CE * REALIZATION / HP_PER_PRIZE,   # per HP healed or added
    "prize": PRIZE_TO_CE,  # an extra Prize taken (Briar)
    "turn_end": -PRIZE_TO_CE,   # per expected Prize lost when an effect ends your turn
    "discard": -0.5,       # each card you must discard as a cost
    "hand_reset": -0.6,    # each of your cards shuffled away by your own shuffle-draw
}
def dmg_ce(hp):
    """Convert damage (HP) into CE through realized Prize progress."""
    return hp * CE["dmg"]

# ---------------- support Pokémon play-down model ----------------
# horizon: own turn by which the card 'should' hit the bench if wanted.
# desire: P(choose to play | accessible) before matchup modifiers. 'mods' are applied per opponent archetype
# using opponent features (see models.py: items, dragon, cursed_blast, munkidori, bench_snipe, stadiums, ex_attackers).
SUPPORT = {
    "Budew":                {"horizon": {"first": 2, "second": 1}, "desire": 0.92, "mods": {"items_low": 0.6},
                             "by_arch": {"n-zoroark": 0.75, "slowking-scr": 0.6, "lopunny-dusknoir": 0.75}},
    "Latias ex":            {"horizon": 2, "desire": 0.70, "by_arch": {"basic-box-m": 0.95, "slowking-scr": 0.90, "raging-bolt-ogerpon": 0.95,
                                                                        "mew-ex-30c": 0.90, "lopunny-dusknoir": 0.80, "dhelmise-pbl": 0.75}},
    "Fezandipiti ex":       {"horizon": 5, "desire": 0.80},
    "Meowth ex":            {"horizon": 2, "desire": 0.75, "by_arch": {"basic-box-m": 0.85, "ogerpon-meganium-hydrapple": 0.85}},
    "Munkidori":            {"horizon": 3, "desire": 0.90},
    "Shaymin":              {"horizon": 3, "desire": 0.55, "mods": {"bench_snipe": 1.5}},
    "Lillie's Clefairy ex": {"horizon": 3, "desire": 0.35, "mods": {"dragon": 2.7}},
    "Psyduck":              {"horizon": 3, "desire": 0.15, "mods": {"cursed_blast": 6.0}},
    "Dudunsparce":          {"horizon": 3, "desire": 0.80},
    "Dunsparce":            {"horizon": 2, "desire": 0.80},
    "Pecharunt ex":         {"horizon": 2, "desire": 0.80},
    "Chien-Pao":            {"horizon": 3, "desire": 0.35, "mods": {"stadiums": 2.0}},
    "Genesect":             {"horizon": 2, "desire": 0.60},
    "Tatsugiri":            {"horizon": 1, "desire": 0.55},
    "Patrat":               {"horizon": 3, "desire": 0.15, "mods": {"munkidori": 6.0}},
    "Mew ex":               {"horizon": 3, "desire": 0.60},
    "Moltres":              {"horizon": 4, "desire": 0.40, "mods": {"ex_attackers": 1.4}, "by_arch": {"lopunny-dudunsparce": 0.6}},
    "Fan Rotom":            {"horizon": 1, "desire": 0.85},
    "Iron Leaves ex":       {"horizon": 4, "desire": 0.55},
    "Teal Mask Ogerpon ex": {"horizon": 2, "desire": 0.95},
    "Kyurem":               {"horizon": 5, "desire": 0.35},
    "Rabsca":               {"horizon": 3, "desire": 0.35, "mods": {"bench_snipe": 1.6}},
    "Genesect ex":          {"horizon": 2, "desire": 0.85},
    "Lunatone":             {"horizon": 2, "desire": 0.95},
}
SPREAD_OR_SNIPE = {"Dragapult ex", "Munkidori", "Dusknoir", "Dusclops", "Iron Crown ex", "Wellspring Mask Ogerpon ex",
                   "Kyurem", "Fezandipiti ex", "Annihilape", "Froslass", "Mega Skarmory ex", "Sinistcha"}
CURSED_BLAST = {"Dusknoir", "Dusclops"}
COUNTER_MOVERS = {"Munkidori"}

# ---------------- Budew / item lock ----------------
ITEM_LOCK = {
    # name: how the lock is applied
    "Budew": "attack:0",            # Itchy Pollen, free attack
    "Frillish": "attack:1",
    "Flaaffy": "attack:2",
    "Galvantula ex": "attack:3",
    "Tyranitar": "ability:active",
    "Jellicent ex": "ability:active",
}
BUDEW_LOCK_TURNS = {"first": 1.5, "second": 1.9}   # expected Itchy Pollen uses per game once Budew is out (report figure)
# engine model: Budew is used on own turns 1-3 with these weights when it is in play (sum = max lock turns per game)
# each locked turn is priced at CE["item_lock"] (~0.5 CE per held-back Item x ~1.5 Items + setup tempo)

# ---------------- engines (per-turn / on-play abilities) ----------------
# kind: turn (once per turn per copy), turn1 (once per turn total), play (once when played/evolved), passive (per turn),
#       attack (uses an attack), first (first turn only)
# value: dict of CE components per use; 'dmg' / 'heal' in HP get converted with dmg_ce.
ENGINES = {
    "Teal Mask Ogerpon ex": {"kind": "turn", "cap": 3, "trigger": "grass_in_hand", "value": {"accel": 1, "draw": 1}, "surv": 0.97, "max_uses": 9},
    "Drakloak":             {"kind": "turn", "cap": 2, "trigger": 0.95, "value": {"select2": 1}, "surv": 0.90, "decay": 0.12},
    "Dudunsparce":          {"kind": "play", "cap": 3, "trigger": 0.9, "value": {"draw": 3}},
    "Fezandipiti ex":       {"kind": "turn1", "cap": 1, "trigger": "ko_last_turn", "value": {"draw": 3}, "surv": 0.95},
    "Meowth ex":            {"kind": "play", "cap": 2, "trigger": 0.85, "value": {"tutor": 1}},
    "Kadabra":              {"kind": "play", "cap": 4, "trigger": 0.9, "value": {"draw": 2}},
    "Alakazam":             {"kind": "play", "cap": 3, "trigger": 0.9, "value": {"draw": 3}},
    "N's Zoroark ex":       {"kind": "turn", "cap": 2, "trigger": 0.9, "value": {"draw": 2, "discard": 1}, "surv": 0.92},
    "Mega Kangaskhan ex":   {"kind": "turn1", "cap": 1, "trigger": 0.7, "value": {"draw": 2}, "surv": 0.93},
    "Lunatone":             {"kind": "turn1", "cap": 1, "trigger": 0.75, "value": {"draw": 3, "discard": 1}, "surv": 0.92},
    "Blaziken ex":          {"kind": "turn", "cap": 1, "trigger": 0.85, "value": {"accel": 1, "energy_card": 1}, "surv": 0.92},
    "Metang":               {"kind": "turn", "cap": 3, "trigger": "metal_top4", "value": {"accel": 1, "energy_card": 1}, "surv": 0.88, "decay": 0.1, "max_uses": 7},
    "Hydrapple ex":         {"kind": "turn", "cap": 1, "trigger": "grass_in_hand", "value": {"accel": 1, "heal": 30}, "surv": 0.92},
    "Meganium":             {"kind": "passive", "cap": 1, "trigger": 0.9, "value": {"accel": 1}, "surv": 0.9},
    "Thwackey":             {"kind": "turn", "cap": 2, "trigger": 0.8, "value": {"tutor": 1}, "surv": 0.88},
    "Genesect ex":          {"kind": "turn", "cap": 1, "trigger": 0.45, "value": {"tutor": 2}, "surv": 0.93},
    "Latias ex":            {"kind": "passive", "cap": 1, "trigger": 0.6, "value": {"retreat_energy": 1.3}, "surv": 0.95},
    "Budew":                {"kind": "early_attack", "cap": 1, "trigger": 1.0, "value": {"item_lock": 1}, "surv": 0.85,
                             "turn_weights": [0.95, 0.6, 0.25]},
    "Munkidori":            {"kind": "turn", "cap": 2, "trigger": 0.8, "value": {"dmg": 30, "heal": 30}, "surv": 0.9},
    "Dusclops":             {"kind": "play", "cap": 2, "trigger": 0.75, "value": {"dmg": 50, "prize_given": 1}},
    "Dusknoir":             {"kind": "play", "cap": 2, "trigger": 0.75, "value": {"dmg": 130, "prize_given": 1}},
    "Iron Leaves ex":       {"kind": "play", "cap": 1, "trigger": 0.6, "value": {"retreat_energy": 1, "accel": 2}},
    "Pecharunt ex":         {"kind": "turn1", "cap": 1, "trigger": 0.6, "value": {"retreat_energy": 1, "dmg": -10}, "surv": 0.93},
    "Tatsugiri":            {"kind": "turn", "cap": 1, "trigger": 0.35, "value": {"tutor": 0.75}, "surv": 0.9},
    "Fan Rotom":            {"kind": "first", "cap": 1, "trigger": 0.9, "value": {"tutor": 2.5}},
    "Hariyama":             {"kind": "play", "cap": 2, "trigger": 0.8, "value": {"gust": 1}},
    "Noctowl":              {"kind": "play", "cap": 2, "trigger": 0.8, "value": {"tutor": 2}},
    "Shaymin":              {"kind": "passive", "cap": 1, "trigger": 0.25, "value": {"heal": 100}, "surv": 0.92},
    "Lillie's Clefairy ex": {"kind": "passive", "cap": 1, "trigger": "dragon_opp", "value": {"dmg": 100}, "surv": 0.92},
    "Psyduck":              {"kind": "passive", "cap": 1, "trigger": "cursed_blast_opp", "value": {"heal": 90}, "surv": 0.9},
    "Chien-Pao":            {"kind": "play", "cap": 1, "trigger": 0.6, "value": {"opp_card": 1.5}},
    "Genesect":             {"kind": "passive", "cap": 1, "trigger": 0.15, "value": {"opp_card": 1.5}, "surv": 0.9},
    "Dunsparce":            {"kind": "attack", "cap": 1, "trigger": 0.4, "value": {"retreat_energy": 1}, "surv": 0.9},
    "Froslass":             {"kind": "passive", "cap": 2, "trigger": 1.0, "value": {"dmg": 25}, "surv": 0.88},
    "Toxtricity":           {"kind": "turn", "cap": 2, "trigger": 0.7, "value": {"accel": 1, "energy_card": 1, "dmg": -20}, "surv": 0.9},
    "Iron Crown ex":        {"kind": "passive", "cap": 1, "trigger": 0.6, "value": {"dmg": 20}, "surv": 0.93},
    "Patrat":               {"kind": "passive", "cap": 1, "trigger": "munkidori_opp", "value": {"heal": 30}, "surv": 0.85},
    "Rabsca":               {"kind": "passive", "cap": 1, "trigger": 0.3, "value": {"heal": 60}, "surv": 0.85},
    "Annihilape":           {"kind": "passive", "cap": 1, "trigger": 0.25, "value": {"heal": 75}, "surv": 0.9},
    "Cynthia's Gabite":     {"kind": "turn", "cap": 2, "trigger": 0.6, "value": {"tutor": 1}, "surv": 0.88},
    "Cynthia's Roserade":   {"kind": "passive", "cap": 1, "trigger": 0.8, "value": {"dmg": 30}, "surv": 0.88},
    "Toucannon":            {"kind": "turn", "cap": 2, "trigger": 0.95, "value": {"draw": 1}, "surv": 0.9},
    "Marnie's Grimmsnarl ex": {"kind": "play", "cap": 2, "trigger": 0.9, "value": {"accel": 3, "energy_card": 3}},
    "Team Rocket's Spidops": {"kind": "turn", "cap": 3, "trigger": 0.7, "value": {"accel": 1, "energy_card": 1}, "surv": 0.9, "max_uses": 6},
    "Mega Greninja ex":     {"kind": "turn1", "cap": 1, "trigger": 0.6, "value": {"dmg": 60, "discard": 1}, "surv": 0.9},
    "Ethan's Quilava":      {"kind": "turn", "cap": 2, "trigger": 0.6, "value": {"tutor": 1}, "surv": 0.88},
    "Hop's Snorlax":        {"kind": "passive", "cap": 1, "trigger": 0.8, "value": {"dmg": 30}, "surv": 0.9},
    "Dipplin":              {"kind": "passive", "cap": 1, "trigger": 0.6, "value": {"dmg": 100}, "surv": 0.85},
    "Seaking":              {"kind": "passive", "cap": 1, "trigger": 0.6, "value": {"dmg": 60, "draw": 2}, "surv": 0.85},
    "Flutter Mane":         {"kind": "passive", "cap": 1, "trigger": 0.3, "value": {"opp_card": 1}, "surv": 0.85},
    "Abra":                 {"kind": "turn1", "cap": 1, "trigger": 0.25, "value": {"retreat_energy": 1}, "surv": 0.8},
    "Pecharunt":            {"kind": "passive", "cap": 1, "trigger": 0.4, "value": {"dmg": 50}, "surv": 0.85},
    "Eelektrik":            {"kind": "turn", "cap": 2, "trigger": 0.8, "value": {"accel": 1, "energy_card": 1}, "surv": 0.88, "max_uses": 6},
    "Mega Venusaur ex":     {"kind": "turn1", "cap": 1, "trigger": 0.6, "value": {"accel": 1}, "surv": 0.93},
    "Steven's Metagross ex": {"kind": "turn1", "cap": 1, "trigger": 0.8, "value": {"accel": 2, "energy_card": 2}, "surv": 0.93},
    "Mega Dragonite ex":    {"kind": "turn1", "cap": 1, "trigger": 0.5, "value": {"retreat_energy": 1}, "surv": 0.93},
    "Bouffalant":           {"kind": "passive", "cap": 1, "trigger": 0.6, "value": {"heal": 60}, "surv": 0.9},
    "Crustle":              {"kind": "passive", "cap": 1, "trigger": "ex_opp", "value": {"heal": 120}, "surv": 0.92},
    "Mew ex":               {"kind": "passive", "cap": 1, "trigger": 0.3, "value": {"retreat_energy": 0.5, "tutor": 0.5}, "surv": 0.9},
    "Tyranitar":            {"kind": "passive", "cap": 1, "trigger": 0.6, "value": {"item_lock": 1}, "surv": 0.9},
    "Jellicent ex":         {"kind": "passive", "cap": 1, "trigger": 0.6, "value": {"item_lock": 1}, "surv": 0.9},
    "Yveltal":              {"kind": "attack", "cap": 1, "trigger": 0.5, "value": {"gust": 0.6, "dmg": 20}, "surv": 0.85},
}

# ---------------- attackers: typical damage per attack ----------------
# dmg: expected damage to the Active in a typical game state; spread: extra bench damage/counters per attack;
# ignore_wr: placing counters / text that ignores Weakness; first: typical own turn of first attack (avg of going 1st/2nd);
# cadence: share of later turns this card is the attacker; note: how dmg was estimated.
ATTACKERS = {
    "Dragapult ex":            dict(type="Dragon", dmg=200, spread=60, first=2.5, cadence=0.85, note="Phantom Dive 200 + 6 counters"),
    "N's Zoroark ex":          dict(type="Darkness", dmg=210, first=2.5, cadence=0.8, note="Night Joker copying Zekrom 250 / Reshiram 170"),
    "Teal Mask Ogerpon ex":    dict(type="Grass", dmg=180, first=2.0, cadence=0.35, note="30 + 30 x ~5 Energy on both Actives"),
    "Lillie's Clefairy ex":    dict(type="Psychic", dmg=160, first=2.5, cadence=0.25, fairy_zone=True, note="20 + 20 x ~7 Benched"),
    "Mega Kangaskhan ex":      dict(type="Colorless", dmg=250, first=2.5, cadence=0.45, note="200 + 50 per heads (E=1)"),
    "Alakazam":                dict(type="Psychic", dmg=160, ignore_wr=True, first=2.5, cadence=0.8, note="2 counters x ~8 cards in hand"),
    "Slowking":                dict(type="Psychic", dmg=140, first=2.5, cadence=0.8, note="Seek Inspiration (copied attack) / Super Psy Bolt 120"),
    "Mega Excadrill ex":       dict(type="Metal", dmg=280, first=3.0, cadence=0.8, note="Maximum Drilling 200 / 330 with 2 extra Energy"),
    "Dipplin":                 dict(type="Grass", dmg=200, first=2.5, cadence=0.8, note="Do the Wave 20 x 5 Bench, twice via Festival Lead"),
    "Dhelmise":                dict(type="Psychic", dmg=170, first=3.0, cadence=0.85, note="30 + 140 once 4 Hide 'n' Sneak are discarded"),
    "Crustle":                 dict(type="Grass", dmg=120, first=2.0, cadence=0.85, note="Superb Scissors 120 (ignores effects); walls ex"),
    "Hydrapple ex":            dict(type="Grass", dmg=330, first=3.0, cadence=0.6, note="30 + 30 x Grass Energy (doubled by Meganium)"),
    "Mega Lucario ex":         dict(type="Fighting", dmg=200, first=2.5, cadence=0.75, note="Mega Brave 270 alternating with Aura Jab 130"),
    "Hariyama":                dict(type="Fighting", dmg=210, first=3.0, cadence=0.25, note="Wild Press 210 (70 to self)"),
    "Mega Lopunny ex":         dict(type="Colorless", dmg=210, first=2.5, cadence=0.8, note="Gale Thrust 230 after a switch / Spiky Hopper 160"),
    "Team Rocket's Honchkrow": dict(type="Darkness", dmg=180, first=2.5, cadence=0.8, note="60 x ~3 TR Supporters discarded"),
    "Cynthia's Garchomp ex":   dict(type="Fighting", dmg=220, first=3.0, cadence=0.8, note="Draconic Buster 260 / Corkscrew Dive 100"),
    "Mega Sharpedo ex":        dict(type="Darkness", dmg=250, first=2.5, cadence=0.8, note="Hungry Jaws 120 + 150 when damaged"),
    "Marnie's Grimmsnarl ex":  dict(type="Darkness", dmg=180, spread=30, first=3.0, cadence=0.8, note="Shadow Bullet 180 + 30 bench"),
    "Team Rocket's Mewtwo ex": dict(type="Psychic", dmg=260, first=3.0, cadence=0.7, note="160 + 60 per Energy discarded (~1.7)"),
    "Raging Bolt ex":          dict(type="Dragon", dmg=280, first=2.0, cadence=0.6, note="70 x ~4 Energy discarded"),
    "Mega Greninja ex":        dict(type="Water", dmg=200, spread=60, first=3.0, cadence=0.8, note="Ninja Spinner 120+80; Mortal Shuriken 6 counters"),
    "Ethan's Typhlosion":      dict(type="Fire", dmg=220, first=3.0, cadence=0.8, note="40 + 60 x ~3 Ethan's Adventure"),
    "Arboliva ex":             dict(type="Grass", dmg=120, ignore_wr=True, first=3.0, cadence=0.5, note="Oil Salvo 6 x 20 anywhere"),
    "Mega Venusaur ex":        dict(type="Grass", dmg=240, first=3.0, cadence=0.8, note="Jungle Dump 240 + heal 30"),
    "Mega Chandelure ex":      dict(type="Psychic", dmg=230, first=3.0, cadence=0.8, note="130 + 50 per retreat cost (+1 from Binding Flame)"),
    "Greninja ex":             dict(type="Water", dmg=170, spread=60, first=3.0, cadence=0.8, note="Shinobi Blade 170 / Mirage Barrage 2x120"),
    "Mega Starmie ex":         dict(type="Water", dmg=180, spread=25, first=2.5, cadence=0.8, note="Nebula Beam 210 / Jetting Blow 120+50"),
    "Mew ex":                  dict(type="Psychic", dmg=160, first=2.5, cadence=0.4, note="Memory Helix copying a Benched attacker"),
    "Hop's Trevenant":         dict(type="Psychic", dmg=130, first=2.5, cadence=0.8, note="Horrifying Revenge 30 + 100"),
    "Ceruledge ex":            dict(type="Fire", dmg=190, first=2.5, cadence=0.8, note="30 + 20 x ~8 Energy in discard"),
    "Beedrill ex":             dict(type="Grass", dmg=270, first=3.0, cadence=0.8, note="110 x ~2.5 Beedrill in play"),
    "Toucannon":               dict(type="Colorless", dmg=200, first=3.0, cadence=0.8, note="60 + 20 x ~7 Benched"),
    "Mega Absol ex":           dict(type="Darkness", dmg=200, first=2.5, cadence=0.6, note="Claw of Darkness 200 (+ hand discard)"),
    "Mega Manectric ex":       dict(type="Lightning", dmg=260, first=3.0, cadence=0.7, note="Riotous Blasting 200/330, Flash Ray 120"),
    "Toxtricity":              dict(type="Darkness", dmg=100, first=3.0, cadence=0.2, note="Gentle Slap 100"),
    "Moltres":                 dict(type="Fire", dmg=110, first=2.0, cadence=0.25, vs_ex_only=True, note="20 + 90 vs ex for one Energy"),
    "Iron Leaves ex":          dict(type="Grass", dmg=180, first=3.0, cadence=0.25, note="Prism Edge 180"),
    "Wellspring Mask Ogerpon ex": dict(type="Water", dmg=100, spread=120, first=3.0, cadence=0.2, note="Torrential Pump 100 + 120 bench"),
    "Fezandipiti ex":          dict(type="Darkness", dmg=0, spread=100, first=3.5, cadence=0.15, note="Cruel Arrow 100 anywhere"),
    "Dudunsparce ex":          dict(type="Colorless", dmg=150, first=3.0, cadence=0.4, note="Tenacious Tail 60 x ex / Destructive Drill 150"),
    "Metagross":               dict(type="Metal", dmg=300, first=3.5, cadence=0.6, note="Metallic Hammer 150 + 150"),
    "Kyurem":                  dict(type="Dragon", dmg=110, spread=220, first=3.5, cadence=0.3, note="Trifrost 110 to 3 Pokémon"),
    "Yveltal":                 dict(type="Darkness", dmg=20, first=2.0, cadence=0.3, note="Clutch 20 + retreat lock (used for the trap, not Dark Feather)"),
    "Bloodmoon Ursaluna ex":   dict(type="Colorless", dmg=240, first=4.0, cadence=0.5, note="Blood Moon 240"),
    "Mega Dragonite ex":       dict(type="Dragon", dmg=330, first=3.0, cadence=0.7, note="Ryuno Glide 330"),
    "Hop's Zacian ex":         dict(type="Metal", dmg=200, spread=15, first=2.5, cadence=0.7, note="Brave Slash 240 alternating with Insta-Strike"),
    "Steven's Metagross ex":   dict(type="Metal", dmg=200, first=3.0, cadence=0.8, note="Metal Stomp 200"),
    "Gengar ex":               dict(type="Darkness", dmg=130, ignore_wr=True, first=3.0, cadence=0.8, note="Chaotic Pain 13 counters anywhere"),
    "Mega Gengar ex":          dict(type="Darkness", dmg=230, first=3.0, cadence=0.8, note="Void Gale 230"),
    "Mega Froslass ex":        dict(type="Water", dmg=250, first=2.5, cadence=0.8, note="50 x ~5 cards in opponent's hand"),
    "Mega Darkrai ex":         dict(type="Darkness", dmg=220, first=2.5, cadence=0.8, note="Dusk Raid 110 + 110"),
    "Hydreigon ex":            dict(type="Darkness", dmg=200, first=3.0, cadence=0.8, note="Dark Bite 200"),
    "Mega Charizard X ex":     dict(type="Fire", dmg=270, first=3.0, cadence=0.8, note="90 x ~3 Fire discarded"),
    "Mega Camerupt ex":        dict(type="Fire", dmg=280, first=3.0, cadence=0.7, note="Volcanic Meteor 280"),
    "Team Rocket's Spidops":   dict(type="Grass", dmg=120, first=2.5, cadence=0.3, note="30 x ~4 TR Pokémon"),
    "N's Zekrom":              dict(type="Dragon", dmg=250, first=3.5, cadence=0.2, note="Rampaging Thunder 250"),
    "N's Reshiram":            dict(type="Dragon", dmg=170, first=3.5, cadence=0.2, note="Virtuous Flame 170"),
    "Munkidori":               dict(type="Psychic", dmg=60, first=2.5, cadence=0.1, note="Mind Bend 60"),
}

# ---------------- trainers: what one play does, in resource units ----------------
# Units are what the card text does in a typical game, in the CE price-list vocabulary above. Rules:
#  * count every card the text gives you (Dawn = 3 searches), discounted only by the chance a search or draw misses
#    (Pokégear, Bug Catching Set) or by what the text caps (Cyrano finds ~2.5 of 3 ex in real lists);
#  * costs the text imposes are negative units in the same vocabulary (discards, your hand shuffled away, Energy you
#    lose, a turn that ends without an attack);
#  * whether you can play it at all (Unfair Stamp needs a KO, Briar needs the opponent at 2 Prizes) is NOT in the
#    per-play value; it lowers plays per game through TRAINER_PLAYABLE.
# Whether the effect was *needed* (is the Basic Dawn finds already in play?) is left to the regression: the
# measured value per copy and its residual against these units are reported next to them.
TRAINER_COMPONENTS = {
    # Supporters
    "Lillie's Determination": {"draw": 6.4, "hand_reset": 3},
    "Judge": {"draw": 4, "hand_reset": 3, "opp_card": 1.5},
    "Boss's Orders": {"gust": 1},
    "Crispin": {"tutor": 1, "accel": 1, "energy_card": 1},
    "Dawn": {"tutor": 3},
    "Hilda": {"tutor": 2},
    "Team Rocket's Petrel": {"tutor": 1},
    "Ciphermaniac's Codebreaking": {"tutor": 1.5},
    "Cyrano": {"tutor": 2.5},
    "Lana's Aid": {"recover": 3},
    "Xerosic's Machinations": {"opp_card": 2.5},
    "Kieran": {"retreat_energy": 0.8, "dmg": 15},
    "Black Belt's Training": {"dmg": 32},
    "Eri": {"opp_card": 1.2},
    "Gwynn": {"draw": 5.1, "discard": 1.7},
    "Wally's Compassion": {"heal": 160, "accel": -2.5},
    "Briar": {"prize": 0.7},
    "Janine's Secret Art": {"accel": 2, "energy_card": 2},
    "Team Rocket's Giovanni": {"gust": 1, "retreat_energy": 1},
    "Team Rocket's Proton": {"tutor": 3},
    "Team Rocket's Ariana": {"draw": 4.5},
    "Team Rocket's Archer": {"draw": 5, "hand_reset": 2, "opp_card": 2},
    "Surfer": {"retreat_energy": 1.2, "draw": 2.5},
    "Pokémon Center Lady": {"heal": 60},
    "Bianca's Devotion": {"heal": 120},
    "AZ's Tranquility": {"retreat_energy": 1.2, "heal": 60},
    "Ethan's Adventure": {"tutor": 3},
    "Tarragon": {"recover": 4},
    "Harlequin": {"draw": 4, "hand_reset": 3, "opp_card": 1.5},
    "Canari": {"tutor": 3.5, "discard": 1},
    "Misty's Vitality": {"accel": 3.5, "energy_card": 3.5, "turn_end": 0.33},
    "Firebreather": {"tutor": 4},
    "Emma": {"draw": 1.5},
    "Gladion's Final Battle": {"dmg": 80},
    "Ruffian": {"opp_card": 1, "energy_denial": 0.5},
    "Rosa's Encouragement": {"accel": 1.8, "energy_card": 1.8},
    # Items
    "Night Stretcher": {"recover": 1},
    "Ultra Ball": {"tutor": 1, "discard": 2},
    "Poké Pad": {"tutor": 1},
    "Buddy-Buddy Poffin": {"tutor": 2},
    "Nest Ball": {"tutor": 1},
    "Special Red Card": {"opp_card": 2.5},
    "Unfair Stamp": {"draw": 5, "hand_reset": 2, "opp_card": 3},
    "Switch": {"retreat_energy": 1.2},
    "Rare Candy": {"evo_tempo": 1},
    "Crushing Hammer": {"energy_denial": 0.5},
    "Enhanced Hammer": {"energy_denial": 0.8},
    "Secret Box": {"tutor": 4, "discard": 3},
    "Pokégear 3.0": {"tutor": 0.8},
    "Sacred Ash": {"recover": 1.5},
    "Energy Switch": {"accel": 0.7},
    "Energy Recycler": {"recover": 0.8},
    "Energy Retrieval": {"recover": 2},
    "Wondrous Patch": {"accel": 1, "energy_card": 1},
    "N's PP Up": {"accel": 1, "energy_card": 1},
    "Glass Trumpet": {"accel": 2, "energy_card": 2},
    "Prime Catcher": {"gust": 1, "retreat_energy": 1.2},
    "Pokémon Catcher": {"gust": 0.5},
    "Poké Ball": {"tutor": 0.5},
    "Bug Catching Set": {"tutor": 1.6},
    "Fighting Gong": {"tutor": 1},
    "Tool Scrapper": {"opp_card": 1.5},
    "Precious Trolley": {"tutor": 4},
    "Miracle Headset": {"recover": 2},
    "Transformation Tome": {"tutor": 0.7},
    "Mega Signal": {"tutor": 1},
    "Hop's Bag": {"tutor": 2},
    "Super Potion": {"heal": 60, "accel": -1, "energy_card": -1},
    "Iron Defender": {"heal": 30},
    "Energy Swatter": {"opp_card": 1},
    "Jumbo Ice Cream": {"heal": 80},
    "Premium Power Pro": {"dmg": 30},
    "Team Rocket's Transceiver": {"tutor": 1},
    # Tools (value over the turns they stay attached)
    "Hero's Cape": {"heal": 100},
    "Brave Bangle": {"dmg": 45},
    "Binding Mochi": {"dmg": 60},
    "Maximum Belt": {"dmg": 75},
    "Lucky Helmet": {"draw": 1.5},
    "Handheld Fan": {"energy_denial": 0.6},
    "Air Balloon": {"retreat_energy": 1.5},
    "Cynthia's Power Weight": {"heal": 70},
    "Hop's Choice Band": {"accel": 1, "dmg": 45},
    "Adversity Policy": {"draw": 0.5},
    # Stadiums (value per Stadium played, ~2 turns in play)
    "Risky Ruins": {"dmg": 40},
    "Team Rocket's Watchtower": {"opp_card": 1.5},
    "Jamming Tower": {"opp_card": 1},
    "Battle Cage": {"heal": 60},
    "Area Zero Underdepths": {"tutor": 1},
    "Gravity Mountain": {"dmg": 60},
    "Team Rocket's Factory": {"draw": 3},
    "Prism Tower": {"select2": 1},
    "Forest of Vitality": {"evo_tempo": 1},
    "Academy at Night": {"select2": 1},
    "N's Castle": {"retreat_energy": 1.5},
    "Lumiose City": {"tutor": 1, "turn_end": 0.1},
    "Nighttime Mine": {"energy_denial": 0.5},
    "Festival Grounds": {},
}
# How each set of units was read from the card text (shown in the report next to the breakdown).
TRAINER_NOTES = {
    "Lillie's Determination": "draw 6 (8 at 6 Prizes, ~20% of plays); your ~3-card hand is shuffled away",
    "Judge": "both players shuffle and draw 4: you draw 4 for ~3; the opponent's ~6-card hand drops to 4",
    "Boss's Orders": "one gust",
    "Crispin": "2 Basic Energy: 1 to hand (a search), 1 attached from the deck (extra attachment + the card)",
    "Dawn": "Basic + Stage 1 + Stage 2: 3 searches",
    "Hilda": "an Evolution Pokémon and an Energy: 2 searches",
    "Team Rocket's Petrel": "any Trainer: 1 search",
    "Ciphermaniac's Codebreaking": "2 chosen cards on top of the deck, drawn over the next turns: ~1.5 searches",
    "Cyrano": "up to 3 Pokémon ex; lists find ~2.5 useful ones",
    "Lana's Aid": "3 non-Rule Box Pokémon / Basic Energy back to hand",
    "Xerosic's Machinations": "opponent discards down to 3 (~2.5 cards)",
    "Kieran": "switch (~0.8 retreat saved) or +30 to an ex (~half the time)",
    "Black Belt's Training": "+40 to an Active ex this turn (~80% of plays hit an ex)",
    "Eri": "up to 2 opposing Items discarded (~1.2 found)",
    "Gwynn": "discard ~1.7 non-Rule Box Pokémon, draw 3 each",
    "Wally's Compassion": "heal a Mega ex (~160 damage); its Energy goes back to hand, ~2.5 attachments to redo",
    "Briar": "+1 Prize on a Tera KO (~70% of plays get the KO)",
    "Janine's Secret Art": "2 Darkness Energy from the deck attached (Active becomes Poisoned: synergy with Binding Mochi)",
    "Team Rocket's Giovanni": "pivot + gust",
    "Team Rocket's Proton": "3 Basic TR Pokémon; legal on turn 1 going first",
    "Team Rocket's Ariana": "draw to 5, or to 8 when all your Pokémon are TR (usual): ~4.5 cards",
    "Team Rocket's Archer": "after a TR KO: you draw 5 from ~2; opponent's ~5 cards drop to 3",
    "Surfer": "pivot + draw to 5 (~2.5 cards)",
    "Pokémon Center Lady": "heal 60",
    "Bianca's Devotion": "full heal of a Pokémon at 30 HP or less (~120)",
    "AZ's Tranquility": "pivot + heal 80 on an ex (~60 average)",
    "Ethan's Adventure": "3 Ethan's Pokémon / Fire Energy",
    "Tarragon": "4 Fighting Pokémon / Energy back to hand",
    "Harlequin": "both shuffle; coin flip 5/3 or 3/5: on average like Judge",
    "Canari": "discard 1, up to 4 Lightning Pokémon (~3.5)",
    "Misty's Vitality": "up to 4 Water Energy attached (~3.5 used); the turn ends: ~60% of the time that costs an attack worth ~0.55 realized Prizes",
    "Firebreather": "up to 7 Fire Energy to hand (~4 useful)",
    "Emma": "draw 1 per Pokémon in the opponent's hand (~1.5)",
    "Gladion's Final Battle": "+80 this turn",
    "Ruffian": "a Tool and a Special Energy (when present) from one Pokémon",
    "Rosa's Encouragement": "up to 2 Basic Energy from the discard onto a Stage 2 (~1.8)",
    "Night Stretcher": "1 Pokémon or Basic Energy back to hand",
    "Ultra Ball": "1 search, 2 discards (the regression says discards are fuel, not a cost, at the margin)",
    "Poké Pad": "1 search (non-Rule Box)",
    "Buddy-Buddy Poffin": "2 Basics with 70 HP or less to the Bench",
    "Nest Ball": "1 Basic to the Bench",
    "Special Red Card": "opponent's hand to 3 (~2.5 cards)",
    "Unfair Stamp": "after a KO: you draw 5 from ~2; opponent's ~5 cards drop to 2",
    "Switch": "pivot (~1.2 retreat Energy saved)",
    "Rare Candy": "skip the Stage 1 turn",
    "Crushing Hammer": "50%: remove an Energy",
    "Enhanced Hammer": "remove a Special Energy (~80% of plays have a target)",
    "Secret Box": "4 searches (Item, Tool, Supporter, Stadium), 3 discards",
    "Pokégear 3.0": "~80% to find a Supporter in the top 7",
    "Sacred Ash": "5 Pokémon back into the deck (~1.5 cards of value)",
    "Energy Switch": "move a Basic Energy (~0.7 of an attachment)",
    "Energy Recycler": "5 Basic Energy back into the deck",
    "Energy Retrieval": "2 Basic Energy back to hand",
    "Wondrous Patch": "1 Psychic Energy from the discard to a Benched Psychic Pokémon",
    "N's PP Up": "1 Basic Energy from the discard to a Benched N's Pokémon",
    "Glass Trumpet": "2 Basic Energy from the discard (needs a Tera in play)",
    "Prime Catcher": "gust + pivot",
    "Pokémon Catcher": "50%: gust",
    "Poké Ball": "50%: a search",
    "Bug Catching Set": "top 7: up to 2 Grass Pokémon / Energy (~1.6)",
    "Fighting Gong": "a Fighting Basic or Energy",
    "Tool Scrapper": "up to 2 Tools (usually the opponent's)",
    "Precious Trolley": "any number of Basics to the Bench (~4)",
    "Miracle Headset": "2 Supporters back to hand",
    "Transformation Tome": "pair: swap a Basic in play for one in the discard",
    "Mega Signal": "a Mega Evolution ex",
    "Hop's Bag": "2 Basic Hop's Pokémon to the Bench",
    "Super Potion": "heal 60, discard an attached Energy (the card + the attachment)",
    "Iron Defender": "−30 damage to your Metal Pokémon for a turn",
    "Energy Swatter": "an Energy from the opponent's hand to the bottom",
    "Jumbo Ice Cream": "heal 80 (Active with 3+ Energy)",
    "Premium Power Pro": "+30 this turn (Fighting)",
    "Team Rocket's Transceiver": "a TR Supporter",
    "Hero's Cape": "+100 HP",
    "Brave Bangle": "+30 to an Active ex, ~1.5 attacks",
    "Binding Mochi": "+40 while Poisoned, ~1.5 attacks",
    "Maximum Belt": "+50 to an Active ex, ~1.5 attacks",
    "Lucky Helmet": "draw 2 when hit as the Active (~0.75 triggers)",
    "Handheld Fan": "moves an Energy off the attacker when hit",
    "Air Balloon": "−2 retreat cost while attached (~1.5 Energy saved)",
    "Cynthia's Power Weight": "+70 HP on a Cynthia's Pokémon",
    "Hop's Choice Band": "−1 attack cost and +30 for Hop's Pokémon, ~1.5 attacks",
    "Adversity Policy": "draw 3 when hit by your Weakness (rare)",
    "Risky Ruins": "2 counters on each opposing non-Darkness Basic benched (~2)",
    "Team Rocket's Watchtower": "turns off Colorless Abilities (Meowth ex, Dudunsparce, Kangaskhan…)",
    "Jamming Tower": "turns off all Tools",
    "Battle Cage": "blocks Bench counters (Phantom Dive, Munkidori)",
    "Area Zero Underdepths": "8 Bench spots with a Tera in play (~one more benched engine)",
    "Gravity Mountain": "−30 HP on Stage 2s",
    "Team Rocket's Factory": "draw 2 per TR Supporter played (~1.5 turns)",
    "Prism Tower": "discard 2, draw 1, each turn: a filter",
    "Forest of Vitality": "Grass Pokémon evolve the turn they're played (~1 evolution turn skipped)",
    "Academy at Night": "put a card on top each turn",
    "N's Castle": "N's Pokémon retreat free (~1.5 Energy saved)",
    "Lumiose City": "a Basic to the Bench, ends your turn (used when you weren't attacking)",
    "Nighttime Mine": "Tera attacks cost 1 more",
    "Festival Grounds": "enabler: its value is counted on Dipplin's double attack",
}
# Share of seen copies you can actually play (conditions in the card text). Lowers plays per game, not value per play.
TRAINER_PLAYABLE = {
    "Unfair Stamp": 0.8,            # one of your Pokémon was KO'd last turn
    "Team Rocket's Archer": 0.7,    # a TR Pokémon was KO'd last turn
    "Special Red Card": 0.6,        # opponent at 3 or fewer Prizes
    "Rosa's Encouragement": 0.5,    # you're behind on Prizes
    "Briar": 0.35,                  # opponent at exactly 2 Prizes
    "Gladion's Final Battle": 0.6,  # last card in hand
    "Glass Trumpet": 0.9,           # a Tera in play
}
# Regression groups: each raw unit maps to one fitted weight.
COMPONENT_GROUPS = {
    "draw": ["draw"], "select": ["select2"], "tutor": ["tutor"], "recover": ["recover"],
    "accel": ["accel"], "energy_card": ["energy_card"], "retreat": ["retreat_energy"], "gust": ["gust"],
    "disruption": ["opp_card"], "energy_denial": ["energy_denial"], "item_lock": ["item_lock"], "evo_tempo": ["evo_tempo"],
    "damage_100hp": ["dmg"], "heal_100hp": ["heal"], "prize": ["prize", "turn_end"], "cost": ["hand_reset", "discard"],
}
RAW2GROUP = {raw: g for g, raws in COMPONENT_GROUPS.items() for raw in raws}
def group_units(comp, mult=1.0):
    """Raw units -> regression-group units. Costs become positive 'cost' units (priced negative), damage/heal per
    100 HP, turn_end becomes negative Prize units. Units outside the vocabulary (prize_given) are ignored."""
    v = {}
    for k, x in comp.items():
        g = RAW2GROUP.get(k)
        if g is None: continue
        x = x * mult
        if g == "cost": x = abs(x)
        elif g in ("damage_100hp", "heal_100hp"): x = x / 100
        elif k == "turn_end": x = -x
        v[g] = v.get(g, 0.0) + x
    return v
HAND_WEIGHTS = {  # hand-set CE per group unit: the price list above, per group
    "draw": CE["draw"], "select": CE["select2"], "tutor": CE["tutor"], "recover": CE["recover"], "accel": CE["accel"],
    "energy_card": CE["energy_card"], "retreat": CE["retreat_energy"], "gust": CE["gust"], "disruption": CE["opp_card"],
    "energy_denial": CE["energy_denial"], "item_lock": CE["item_lock"], "evo_tempo": CE["evo_tempo"],
    "damage_100hp": 100 * CE["dmg"], "heal_100hp": 100 * CE["heal"], "prize": CE["prize"],
    "cost": (CE["discard"] + CE["hand_reset"]) / 2,
}
def hand_price(comp, mult=1.0):
    """CE of a component dict at the hand-set price list (exact discard / hand_reset prices)."""
    ce = 0.0
    for k, x in comp.items():
        if k in ("discard", "hand_reset"): ce += CE[k] * abs(x) * mult
        elif k in CE: ce += CE[k] * x * mult
    return ce
def breakdown(comp):
    """'3 search × 1.5 = 4.5' style text for the report."""
    lab = {"draw": "draw", "select2": "look-2-keep-1", "tutor": "search", "recover": "recover", "accel": "extra attachment",
           "energy_card": "Energy not from hand", "retreat_energy": "retreat Energy saved", "gust": "gust", "opp_card": "opponent card",
           "energy_denial": "opposing Energy removed", "item_lock": "Item-lock turn", "evo_tempo": "evolution turn",
           "dmg": "HP damage", "heal": "HP healed", "prize": "Prize", "turn_end": "Prize lost (turn ends)", "discard": "discard",
           "hand_reset": "card shuffled away"}
    terms = []
    for k, x in comp.items():
        if k not in CE: continue
        val = CE[k] * (abs(x) if k in ("discard", "hand_reset") else x)
        per = f"{abs(CE[k]):.3f}" if k in ("dmg", "heal") else f"{abs(CE[k]):g}"
        terms.append((val, f"{abs(x):g} {lab.get(k, k)} × {per}"))
    out = "".join(("−" if v < 0 else "") + t if i == 0 else (" − " if v < 0 else " + ") + t for i, (v, t) in enumerate(terms))
    return f"{out} = {hand_price(comp):.2f}" if terms else "0"
TRAINER_CE = {n: (round(hand_price(c), 2), TRAINER_NOTES.get(n, "")) for n, c in TRAINER_COMPONENTS.items()}

# ---------------- Power model (power.py) ----------------
# Special Energy with a resource effect when attached (per attachment; ~0.6 attachments per copy per game).
ENERGY_COMPONENTS = {
    "Telepathic Psychic Energy": {"tutor": 2},     # 2 Basic Psychic Pokémon to the Bench
    "Enriching Energy": {"draw": 4},
}
ENERGY_PLAYS_PER_COPY = 0.6
# Probability a non-support Pokémon is on the board mid-game, by copies (1, 2, 3, 4+).
P_ON_BOARD = [0.0, 0.6, 0.84, 0.94, 0.97]
SPREAD_CONVERSION = 0.65     # bench damage that does not KO converts to Prize progress at this rate
BUDEW_ACTIVE_SHARE = 0.5     # share of Budew's Itchy Pollen turns on which it takes the opponent's hit
# Bench damage that is aimed, not spread: (damage per target, number of Benched targets).
SNIPE = {"Kyurem": (110, 2), "Wellspring Mask Ogerpon ex": (120, 1), "Fezandipiti ex": (100, 1), "Marnie's Grimmsnarl ex": (30, 1)}
# Average Prizes a player takes per game (winner ~5.6 incl. games not ended by Prizes, loser ~3.4). The raw
# Prize-progress model counts 2HKO progress that is never cashed in (heals, retreats, the game ending), so the
# window's mean offense is scaled to this figure (the same factor applies to liability).
PRIZES_TAKEN_PER_GAME = 4.5
# Exchange rate between Prizes and card-equivalents in the Power model. Chosen by leave-one-archetype-out
# cross-validation of Deck Power against archetype win rate (grid 3/6/10/15/20; 10 was best). Damage and healing
# effects use the same rate, so 100 HP of damage = 100 / HP_PER_PRIZE Prizes = 7.1 CE.
POWER_CE_PER_PRIZE = PRIZE_TO_CE
# Engine damage that the ATTACKERS entry already counts (Festival Lead's second attack, Mortal Shuriken): skipped in Power.
POWER_SKIP_ENGINE_DMG = {"Dipplin", "Mega Greninja ex"}
