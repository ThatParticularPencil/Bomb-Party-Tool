# BombParty dictionary

English bomb.party list: **273,278** words.

`enable1` ∪ `SOWPODS` ∪ (Moby crosswords − `bogys`, `handicrafsman`, `handicrafsmen`, `lazys`, `questionniare`, `questionniares`) ∪ 132 hand-added words.

```bash
python3 scripts/build_dictionary.py
python3 -m bombparty stats
python3 -m bombparty word aztec
python3 -m bombparty search --compound --band common --limit 20
python3 -m bombparty prompts --length 3 --max-count 49
python3 -m bombparty solutions tnt
python3 -m bombparty practice --rounds 10 --max-count 49
python3 -m bombparty cards --rounds 15 --scientific
```

`practice` asks for a word containing the prompt (`?` hint, blank skip, `q` quit). `cards` prints prompt, solution count, and one answer. `--compound`, `--scientific`, `--prefixed`, and `--band common` limit both. Word filters only see prompts with at most 100 solutions.

`data/words.txt` is the plain list. `data/bombparty.sqlite` has tags: `lexicon_class` (`core`, `enable_only`, `sowpods_only`, `twl_not_enable`, `moby_only`, `manual`), `freq_band`, `is_compound`, `is_prefixed`, `is_scientific`, `is_hyphenated` (always 0; hyphens were normalized away), `manual_category`, and prompt rarity (`rarest2_count`, `rarest3_count`). Prompts with ≤100 solutions are in `scarce_solutions`. `<50` means `solution_count < 50`.
