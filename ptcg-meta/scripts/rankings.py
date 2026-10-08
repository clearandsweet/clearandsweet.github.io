"""Combine engine Advantage (CE/game) and attack damage value into Pokémon rankings.
Usage: python3 -I rankings.py DATADIR [WINDOW=CUR]
"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model_config as C
D = sys.argv[1]; WIN = sys.argv[2] if len(sys.argv) > 2 else "CUR"
O = os.path.join(D, "out")
adv = pd.read_csv(os.path.join(O, f"advantage_pokemon_{WIN}.csv")).rename(columns={"name": "card"})
dmg = pd.read_csv(os.path.join(O, f"damage_value_{WIN}.csv")).rename(columns={"attacker": "card"})
inv = pd.read_csv(os.path.join(O, f"card_inventory_{WIN}.csv"))
pk = inv[inv["cat"] == "pokemon"].sort_values("lists", ascending=False).drop_duplicates("name")
inc = pk.set_index("name")[["inclusion", "inclusion_day2", "legal_post"]].rename(columns={"inclusion": "field_inclusion", "inclusion_day2": "day2_inclusion"})
m = pd.merge(adv[["card", "uses_per_game", "ce_per_use", "advantage_ce_per_game", "extra_cards_per_game", "extra_energy_per_game",
                  "retreat_energy_saved_per_game", "item_lock_turns_per_game", "damage_hp_per_game", "heal_hp_per_game"]],
             dmg[["card", "exp_damage_vs_meta", "p_OHKO_meta_defender", "prizes_per_attack", "attacks_per_game", "prizes_per_game",
                  "damage_value_ce_per_game", "prize_liability", "prize_efficiency"]], on="card", how="outer")
m = m.join(inc, on="card")
m[["advantage_ce_per_game", "damage_value_ce_per_game"]] = m[["advantage_ce_per_game", "damage_value_ce_per_game"]].fillna(0)
m["total_impact_ce_per_game"] = m["advantage_ce_per_game"] + m["damage_value_ce_per_game"]
m["meta_weighted_impact"] = m["total_impact_ce_per_game"] * m["field_inclusion"].fillna(0)
m["role"] = np.where(m["damage_value_ce_per_game"] > m["advantage_ce_per_game"], "attacker", "engine/support")
m.sort_values("advantage_ce_per_game", ascending=False).to_csv(os.path.join(O, f"pokemon_rankings_{WIN}.csv"), index=False)
print(m.sort_values("advantage_ce_per_game", ascending=False).head(50)[["card", "advantage_ce_per_game", "damage_value_ce_per_game", "total_impact_ce_per_game", "field_inclusion", "legal_post"]].round(2).to_string())
