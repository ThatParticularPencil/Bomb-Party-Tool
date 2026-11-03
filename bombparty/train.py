"""Tiny BombParty drills. Type a word that contains the prompt."""

from __future__ import annotations

from bombparty.dictionary import Dictionary


def cards(dictionary: Dictionary, *, rounds: int, **filters) -> None:
    rows = dictionary.sample_prompts(limit=rounds, **filters)
    if not rows:
        print("no prompts match")
        return
    for row in rows:
        answer = dictionary.hint(row["prompt"], **_hint_filters(filters))
        print(f"{row['prompt']}\t{row['solution_count']}\t{answer or ''}")


def practice(dictionary: Dictionary, *, rounds: int, **filters) -> None:
    rows = dictionary.sample_prompts(limit=rounds, **filters)
    if not rows:
        print("no prompts match")
        return
    hint_filters = _hint_filters(filters)
    got = 0
    for index, row in enumerate(rows, 1):
        prompt = row["prompt"]
        print(f"\n[{index}/{len(rows)}] {prompt.upper()}   {row['solution_count']} words")
        print("word, ? for a hint, blank to skip, q to quit")
        while True:
            try:
                guess = input("> ").strip().lower()
            except EOFError:
                print(f"\n{got}/{index - 1}")
                return
            if guess in {"q", "quit"}:
                print(f"{got}/{index - 1}")
                return
            if guess in {"?", "hint"}:
                print(dictionary.hint(prompt, **hint_filters) or "no hint")
                continue
            if guess == "":
                print(dictionary.hint(prompt, **hint_filters) or "no answer stored")
                break
            if prompt not in guess:
                print(f"needs {prompt}")
                continue
            entry = dictionary.get(guess)
            if entry is None:
                print("not in the dictionary")
                continue
            reject = _reject(entry, filters)
            if reject:
                print(reject)
                continue
            print("ok")
            got += 1
            break
    print(f"\n{got}/{len(rows)}")


def _hint_filters(filters: dict) -> dict:
    return {
        "compound": filters.get("compound"),
        "scientific": filters.get("scientific"),
        "prefixed": filters.get("prefixed"),
        "freq_band": filters.get("freq_band"),
    }


def _reject(entry: dict, filters: dict) -> str | None:
    if filters.get("compound") and not entry["is_compound"]:
        return "use a compound"
    if filters.get("scientific") and not entry["is_scientific"]:
        return "use a scientific word"
    if filters.get("prefixed") and not entry["is_prefixed"]:
        return "use a prefixed word"
    band = filters.get("freq_band")
    if band and entry["freq_band"] != band:
        return f"use a {band} word"
    return None
