# H Rotation Meta Ledger

A statistical study of the current Pokémon TCG Standard format (Oct 2026) and of how the coming
rotation of **H-mark** cards (and the arrival of **K-mark** cards) changes it.

Open `index.html` for the report. Everything in it is generated from the data and scripts in this folder.

## What's here

| Path | Contents |
|---|---|
| `index.html` | The report: metagame, rotation, Budew / item lock, support play-down, Advantage stat, damage value, Japan preview, card inventory, next-step methods and eye-test questions. |
| `data/processed/` | Tidy tables built from the scrape (gzipped CSV). `players` = every player at every event with record, Day 2 and top-cut flags and archetype; `list_cards` = every card in every published list; `matches` = every round's pairing and result with both decks; `cards` = every card seen, with regulation marks of all its prints and post-rotation legality; `jp_*` = Japanese lists. |
| `data/out/` | Analysis outputs (one CSV/JSON per table in the report, plus extras such as matchup matrices, per-archetype card usage, per-list rotation counts and simulation rows). |
| `scripts/` | The full pipeline. All model assumptions live in `scripts/model_config.py`; the report page is `scripts/report_template.html` filled by `build_report.py`. |
| `data/cards/` | `limitless_cache.json.gz` (every card page: regulation mark, text, all international and Japanese prints), `jp_print_marks.json` (marks of every Japanese Mega-era reprint of a rotating card). |

## Data sources

* **Limitless Labs** (`labs.limitlesstcg.com`, via its JSON API at `mew.limitlesstcg.com/labs/data/tcg/…`): standings, Day 2 / top-cut flags, pairings for every round, and the full decklist of every player at each Regional, International, Special Event and Worlds from Prague (Apr 2026) to Recife (Oct 2026).
* **Limitless TCG** (`limitlesstcg.com`): card pages with every international and Japanese print (used for regulation marks and reprint legality); Champions League Yokohama, Japan Championships 2026 and Champions League Aichi top lists; current-season Japanese City League top-16 lists.
* **pokemon-tcg-data** (GitHub): structured card text (HP, types, attacks, abilities, Weakness, retreat) through 30th Celebration.
* **Trainer Hill**: archetype counts across in-person and online events, used as a cross-check.

## Format windows

| Window | Events |
|---|---|
| `CUR` (current format) | Baltimore, Brisbane, Frankfurt, Recife (2027 season; Pitch Black legal, 30th Celebration from Brisbane) |
| `WORLDS` | World Championship 2026, San Francisco |
| `CRI` | Turin, NAIC 2026 |
| `POR` | Prague → Indianapolis (first events after the G rotation) |

## Rotation logic

A card rotates if **none** of its functional prints (Limitless groups identical-text reprints) has an I, J or K mark.
Basic Energy never rotates. Every Japanese Mega-era reprint of a rotating card was checked as well. All of them,
including the December 2025 "Starter Decks 100 Battle Collection" reprints, are H, so there is no reprint lifeline in
either region as of 8 Oct 2026. Only three K-block candidates (Aura Seeker, M7) have been revealed.

## Rebuilding

```bash
python3 -I scripts/labs_scrape.py data/labs 0075 0074 ...     # Labs standings, pairings, decklists (resumable)
python3 -I scripts/jp_scrape.py data/jp 2026-08-01 569,568,549  # JP majors + City Leagues
python3 -I scripts/limitless_cards.py data                      # card pages / prints for every card seen
python3 -I scripts/jp_reprint_marks.py data                     # marks of JP reprints of rotating cards
python3 -I scripts/build_dataset.py data                        # -> data/processed
python3 -I scripts/meta_analysis.py data                        # archetypes, matchups, inventory, rotation counts
python3 -I scripts/models.py data CUR 250 all                   # play-down, Budew, engines, trainers
python3 -I scripts/models.py data CUR 250 day2                  # same on the Day 2 field
python3 -I scripts/damage_model.py data CUR
python3 -I scripts/power.py data                                # Card / Deck Power for every list
python3 -I scripts/power_eval.py data CUR                       # Power tables + validation
python3 -I scripts/rotation_analysis.py data CUR
python3 -I scripts/rankings.py data CUR
python3 -I scripts/jp_analysis.py data CUR
python3 -I scripts/build_report.py data scripts/report_template.html index.html
```

`scripts/run_all.sh data scripts/report_template.html index.html` runs every step after the scrape.
The tables in `data/processed/` are stored gzipped; `gunzip -k data/processed/*.gz` restores the CSVs the scripts read.

The card pool JSON (`data/cards/*.json`) comes from `raw.githubusercontent.com/PokemonTCG/pokemon-tcg-data/master/cards/en/<set>.json`.

## Calibration from results (round 2)

* `features.py` builds every list's per-game resource vector (draw, search, recovery, acceleration, retreat, gust,
  disruption, item lock, evolution tempo, damage, healing, costs) from simulated engine uses and decomposed Trainers
  (`TRAINER_COMPONENTS` in `model_config.py`).
* `regress.py`: stage 1 estimates the win-rate and Day 2 change per extra copy of each common card within its archetype
  (archetype × format and event fixed effects, leave-one-event-out pilot skill, player-clustered SEs, collinear
  evolution lines merged). Stage 2 explains those per-copy effects by what one more copy adds (Supporters net of the
  Supporter they displace; engines via simulated marginal uses), with a ±1 CE prior around the hand-set weights.
  Output: `data/out/ce_weights_fitted.csv`, `card_value_per_copy.csv`.
* `cardcount.py`: copy-count effects (e.g. 3 vs 4 Teal Mask) inside every archetype with Benjamini-Hochberg q-values
  → `card_count_effects.csv`.
* `dimret.py`: simulated uses at 1–4 copies of each engine in real lists → `engine_copy_curves.csv`.
* `tcgl_logs.py`: parser for TCG Live battle logs (drop `.txt` exports in `data/logs/`) to calibrate the simulations.
  Trainer Hill exposes no public battle-log data (its Battle Journal / Battle Journal+ are personal, login-gated trackers).

"Uses per game" for an engine counts every copy in the list together; the copy curves give the per-copy split.

## Card and Deck Power (round 3)

* `ce_cv.py`: leave-one-card-out test of the stage-2 fit under different prior strengths (hand-set only, τ grid,
  data-only) → `ce_cv.csv`; the cards that set each data-only weight → `ce_weight_drivers.csv`.
  The marginal (fitted / data-only) weights predict "one more copy" better; the hand-set weights do worse than
  guessing the average there.
* `power.py`: for every list and every card, per game:
  * **Effect**: resource units from Abilities, Trainers and a few special Energy × CE weights (hand-set, fitted, data-only).
  * **Prizes taken**: attack share × attacks per game × Prizes per attack, measured against 1,500 real lists of the
    same format (Active with Weakness/Resistance, best gust target, spread and snipe KOs).
  * **Prizes given up**: the format's attack pool hitting the card as the Active, as the best gust target, or with
    spread, plus self-KOs. One KO per copy, at most 6 per deck. Prize progress is scaled so the average deck takes
    `PRIZES_TAKEN_PER_GAME` = 4.5 Prizes.
  * **Power = Effect + 10 × (Prizes taken − Prizes given up)**. Damage and healing effects use the same rate.
  Outputs `power_lists.csv.gz` (per list), `power_prizes_per_attack.csv`, `power_meta.json`. The per-card-per-list
  table (`power_cards_all.csv.gz`, ~33 MB) is regenerated by the script and not committed.
* `power_eval.py`: archetype tables (`power_archetypes_CUR.csv`, `power_archetypes_all.csv`), card table
  (`power_cards_CUR.csv`) and the validation: archetype × format means against non-mirror win rate and Day 2 rate,
  leave-one-archetype-out → `power_validation.csv`. The CE-per-Prize rate (10) was picked on this test from 3/6/10/15/20.
  Hand-set weights win the deck-level test; fitted and data-only weights do worse than guessing the average.

## Units

* **CE (card-equivalent)**: the value of drawing one random card. Searches, Energy acceleration, retreat savings,
  Item lock, damage and healing all convert into CE (see `model_config.py`). The Advantage tables use 1 Prize ≈ 3 CE;
  the Power model uses 1 Prize = 10 CE, the rate cross-validation picked against results.
* **Win rate**: ties count as ⅓ of a win; non-mirror unless stated.
* **Day 2 lift**: archetype Day 2 rate ÷ field Day 2 rate. The "shrunk" version adds 30 pseudo-players at the field rate.
