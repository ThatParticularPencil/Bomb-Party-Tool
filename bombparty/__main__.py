"""Search the English BombParty dictionary from the command line.

Examples:
  python3 -m bombparty stats
  python3 -m bombparty word aztec
  python3 -m bombparty solutions tnt
  python3 -m bombparty prompts --length 3 --max-count 1 --limit 20
  python3 -m bombparty search --compound --band common --max-length 12
  python3 -m bombparty search ent --manual
"""

from __future__ import annotations

import argparse
import json

from bombparty.dictionary import open_dictionary
from bombparty.train import cards, practice


def main() -> None:
    parser = argparse.ArgumentParser(description="Search the English BombParty dictionary")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("stats", help="Counts by source, frequency, and prompt difficulty")

    word = sub.add_parser("word", help="Show every stored field for one word")
    word.add_argument("word")

    search = sub.add_parser("search", help="Filter the dictionary")
    search.add_argument("contains", nargs="?", help="Substring the word must contain")
    search.add_argument("--starts")
    search.add_argument("--ends")
    search.add_argument("--min-length", type=int)
    search.add_argument("--max-length", type=int)
    search.add_argument("--class", dest="lexicon_class", help="core, enable_only, sowpods_only, twl_not_enable, moby_only, manual")
    search.add_argument("--band", dest="freq_band", help="common, familiar, uncommon, rare, unlisted")
    search.add_argument("--category", dest="manual_category")
    search.add_argument("--compound", action="store_true")
    search.add_argument("--scientific", action="store_true")
    search.add_argument("--prefixed", action="store_true")
    search.add_argument("--hyphen", action="store_true")
    search.add_argument("--proper", action="store_true")
    search.add_argument("--manual", action="store_true")
    search.add_argument("--jqxz", action="store_true")
    search.add_argument("--twl", action="store_true")
    search.add_argument("--enable", action="store_true")
    search.add_argument("--sowpods", action="store_true")
    search.add_argument("--moby", action="store_true")
    search.add_argument("--max-rarest2", type=int, help="Word contains a 2-letter prompt with at most this many solutions")
    search.add_argument("--max-rarest3", type=int, help="Word contains a 3-letter prompt with at most this many solutions")
    search.add_argument("--under-50", action="store_true", help="Word contains a 2- or 3-letter prompt with fewer than 50 solutions")
    search.add_argument("--limit", type=int, default=40)
    search.add_argument(
        "--order",
        default="word",
        choices=["word", "length", "longest", "frequency", "rarest2", "rarest3", "scarce3"],
    )
    search.add_argument("--json", action="store_true")

    prompts = sub.add_parser("prompts", help="List letter prompts by how many words solve them")
    prompts.add_argument("--length", type=int, default=3)
    prompts.add_argument("--max-count", type=int, default=49)
    prompts.add_argument("--min-count", type=int, default=1)
    prompts.add_argument("--limit", type=int, default=40)

    solutions = sub.add_parser("solutions", help="Words that contain a prompt")
    solutions.add_argument("prompt")
    solutions.add_argument("--limit", type=int, default=100)

    def add_drill_flags(drill: argparse.ArgumentParser) -> None:
        drill.add_argument("--rounds", type=int, default=10)
        drill.add_argument("--length", type=int, default=3)
        drill.add_argument("--min-count", type=int, default=1)
        drill.add_argument("--max-count", type=int, default=49)
        drill.add_argument("--compound", action="store_true")
        drill.add_argument("--scientific", action="store_true")
        drill.add_argument("--prefixed", action="store_true")
        drill.add_argument("--band", dest="freq_band", help="common, familiar, uncommon, rare, unlisted")

    add_drill_flags(sub.add_parser("practice", help="Type a word for each prompt. ? hints, blank skips, q quits"))
    add_drill_flags(sub.add_parser("cards", help="Print random prompts with one answer"))

    args = parser.parse_args()
    with open_dictionary() as dictionary:
        if args.cmd == "stats":
            _print_stats(dictionary.stats())
        elif args.cmd == "word":
            row = dictionary.get(args.word)
            if row is None:
                excluded = {item["word"]: item["reason"] for item in dictionary.excluded()}
                reason = excluded.get(args.word.lower())
                if reason:
                    print(f"{args.word.lower()}\texcluded\t{reason}")
                else:
                    print(f"{args.word.lower()}\tnot in the dictionary")
                raise SystemExit(1)
            for key, value in row.items():
                print(f"{key}\t{value}")
        elif args.cmd == "search":
            rows = dictionary.search(
                contains=args.contains,
                starts=args.starts,
                ends=args.ends,
                min_length=args.min_length,
                max_length=args.max_length,
                lexicon_class=args.lexicon_class,
                freq_band=args.freq_band,
                manual_category=args.manual_category,
                compound=True if args.compound else None,
                scientific=True if args.scientific else None,
                prefixed=True if args.prefixed else None,
                hyphenated=True if args.hyphen else None,
                proper=True if args.proper else None,
                manual=True if args.manual else None,
                has_jqxz=True if args.jqxz else None,
                in_twl=True if args.twl else None,
                in_enable1=True if args.enable else None,
                in_sowpods=True if args.sowpods else None,
                in_moby=True if args.moby else None,
                max_rarest2=args.max_rarest2,
                max_rarest3=args.max_rarest3,
                under_50=True if args.under_50 else None,
                limit=args.limit,
                order=args.order,
            )
            if args.json:
                print(json.dumps(rows, indent=2))
            else:
                for row in rows:
                    print(
                        f"{row['word']}\t{row['length']}\t{row['lexicon_class']}\t{row['freq_band']}\t{row['tags']}"
                    )
                print(f"{len(rows)} shown")
        elif args.cmd == "prompts":
            for row in dictionary.prompts(
                length=args.length,
                max_count=args.max_count,
                min_count=args.min_count,
                limit=args.limit,
            ):
                print(f"{row['prompt']}\t{row['solution_count']}")
        elif args.cmd in {"practice", "cards"}:
            filters = {
                "length": args.length,
                "min_count": args.min_count,
                "max_count": args.max_count,
                "compound": True if args.compound else None,
                "scientific": True if args.scientific else None,
                "prefixed": True if args.prefixed else None,
                "freq_band": args.freq_band,
            }
            if args.cmd == "practice":
                practice(dictionary, rounds=args.rounds, **filters)
            else:
                cards(dictionary, rounds=args.rounds, **filters)
        elif args.cmd == "solutions":
            result = dictionary.solutions(args.prompt, limit=args.limit)
            count = result["solution_count"]
            shown = len(result["words"])
            print(f"{result['prompt']}\t{count} solutions\tshowing {shown}")
            for word in result["words"]:
                print(word)


def _print_stats(stats: dict) -> None:
    meta = stats["meta"]
    print(f"words\t{stats['words']}")
    for key in ("word_count", "enable1", "sowpods", "moby", "manual", "removed"):
        if key in meta:
            print(f"{key}\t{meta[key]}")
    print("lexicon")
    for name, count in stats["lexicon_class"]:
        print(f"  {name}\t{count}")
    print("frequency")
    for name, count in stats["freq_band"]:
        print(f"  {name}\t{count}")
    print("manual categories")
    for name, count in stats["manual_category"]:
        print(f"  {name}\t{count}")
    print("flags")
    for name, count in stats["flags"].items():
        print(f"  {name}\t{count}")
    print("prompts")
    for row in stats["prompts"]:
        print(
            f"  length {row['length']}\t{row['prompts']} prompts\t"
            f"under 50: {row['under_50']}\tunique: {row['unique']}"
        )


if __name__ == "__main__":
    main()
