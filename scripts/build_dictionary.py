#!/usr/bin/env python3
"""Build the English BombParty dictionary.

Playable words =
    enable1
    ∪ SOWPODS
    ∪ (Moby official crosswords − six words Élisée removed)
    ∪ words added by hand and confirmed in the 273278-word list

The archived list is a checksum. Source membership is stored on every word
so a trainer can separate Scrabble words, crossword leftovers, and the
short list Élisée added himself.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "bombparty.sqlite"
WORDS_PATH = ROOT / "data" / "words.txt"
MANUAL_PATH = ROOT / "data" / "manual.tsv"

REMOVED = {
    "bogys": "Removed after complaints. In the Moby crosswords, rejected by BombParty.",
    "handicrafsman": "Removed after complaints. In the Moby crosswords, rejected by BombParty.",
    "handicrafsmen": "Removed after complaints. In the Moby crosswords, rejected by BombParty.",
    "lazys": "Removed after complaints. In the Moby crosswords, rejected by BombParty.",
    "questionniare": "Removed after complaints. In the Moby crosswords, rejected by BombParty.",
    "questionniares": "Removed after complaints. In the Moby crosswords, rejected by BombParty.",
}

# Words in the verified list that are in none of enable1, SOWPODS, or Moby.
# Categories describe why a player would have needed them, not a linguistic parse.
MANUAL_CATEGORY = {
    "ablebodied": "compound",
    "alabama": "place",
    "allah": "religion",
    "america": "place",
    "american": "demonym",
    "amish": "group",
    "amsterdam": "place",
    "antidisestablishmentarianism": "long",
    "april": "month",
    "arab": "demonym",
    "arabian": "demonym",
    "argh": "interjection",
    "arial": "brand",
    "asian": "demonym",
    "atlanta": "place",
    "australia": "place",
    "australian": "demonym",
    "austria": "place",
    "aztec": "group",
    "ballsack": "slang",
    "belgium": "place",
    "bezier": "personal_name",
    "british": "demonym",
    "butthole": "slang",
    "ceo": "acronym",
    "cest": "loanword",
    "christ": "personal_name",
    "christmas": "holiday",
    "cia": "acronym",
    "cumming": "slang",
    "cums": "slang",
    "december": "month",
    "denmark": "place",
    "derp": "slang",
    "donger": "slang",
    "dongers": "slang",
    "england": "place",
    "ent": "other",
    "ernest": "personal_name",
    "europe": "place",
    "european": "demonym",
    "fapping": "slang",
    "faps": "slang",
    "finland": "place",
    "finnish": "demonym",
    "florida": "place",
    "france": "place",
    "friday": "weekday",
    "gatling": "personal_name",
    "germany": "place",
    "ghana": "place",
    "haiti": "place",
    "hebrew": "language",
    "hentai": "slang",
    "hexakosioihexekontahexaphobia": "scientific",
    "highschool": "compound",
    "hitler": "personal_name",
    "inc": "acronym",
    "indian": "demonym",
    "iq": "acronym",
    "iran": "place",
    "ireland": "place",
    "irish": "demonym",
    "isis": "acronym",
    "islam": "religion",
    "italian": "demonym",
    "italy": "place",
    "jericho": "place",
    "july": "month",
    "kermit": "personal_name",
    "lapdance": "compound",
    "latin": "language",
    "meh": "interjection",
    "mia": "acronym",
    "miami": "place",
    "monday": "weekday",
    "muslim": "religion",
    "nasa": "acronym",
    "nato": "acronym",
    "nerf": "brand",
    "nigga": "slang",
    "nizzle": "slang",
    "noob": "slang",
    "norse": "demonym",
    "nsa": "acronym",
    "october": "month",
    "ok": "interjection",
    "olympic": "other",
    "ontario": "place",
    "persian": "demonym",
    "phish": "brand",
    "pluto": "place",
    "pokemon": "brand",
    "poland": "place",
    "popo": "slang",
    "pseudopseudohypoparathyroidism": "scientific",
    "psy": "acronym",
    "queef": "slang",
    "rambo": "personal_name",
    "reddit": "brand",
    "respawn": "slang",
    "ressurect": "misspelling",
    "rimjob": "slang",
    "rome": "place",
    "russian": "demonym",
    "santa": "personal_name",
    "satan": "personal_name",
    "saturday": "weekday",
    "saturn": "place",
    "selfie": "slang",
    "senpai": "slang",
    "shemale": "slang",
    "sms": "acronym",
    "spanish": "demonym",
    "sphenopalatineganglioneuralgia": "scientific",
    "std": "acronym",
    "stfu": "acronym",
    "tard": "slang",
    "thor": "personal_name",
    "tnt": "acronym",
    "trojan": "brand",
    "tuesday": "weekday",
    "twerk": "slang",
    "uranus": "place",
    "usa": "acronym",
    "utah": "place",
    "vatican": "place",
    "viagra": "brand",
    "wifi": "acronym",
    "ying": "other",
    "yoyo": "reduplicative",
    "zen": "religion",
}

# Right-hand pieces that are suffixes rather than independent compound heads.
COMPOUND_RIGHT_STOP = {
    "able", "ible", "ably", "ibly", "ness", "less", "ment", "ments", "hood", "hoods",
    "tion", "sion", "tions", "sions", "ation", "ations", "ence", "ance", "ences", "ances",
    "ally", "fully", "nesses", "izing", "ising", "ated", "ator", "ators", "ities",
}

PREFIXES = tuple(sorted((
    "counter", "pseudo", "hyper", "inter", "intra", "micro", "macro", "multi",
    "super", "supra", "ultra", "under", "extra", "trans", "anti", "semi",
    "mono", "poly", "mega", "mini", "auto", "fore", "tele", "over", "hypo",
    "non", "out", "sub", "mis", "dis", "pre", "tri", "un", "up", "re",
), key=len, reverse=True))

# Short prefixes match huge numbers of ordinary words. Only keep the split when
# the whole word is not itself a common word.
GUARDED_PREFIXES = {"dis", "mis", "out", "pre", "re", "sub", "tri", "un", "up"}
GUARDED_PREFIX_MAX_RANK = 20000

SCI_SUFFIXES = tuple(sorted((
    "ological", "ologist", "ography", "ographic", "oscopies", "oscopy", "oscopic",
    "ectomies", "ectomy", "ostomies", "ostomy", "phobias", "phobia", "phobic",
    "morphisms", "morphism", "morphic", "genesis", "plasties", "plasty",
    "pathies", "pathy", "algias", "algia", "emias", "emia", "urias", "uria",
    "itises", "itis", "phages", "phage", "cytes", "cyte", "plasms", "plasm",
    "icides", "icide", "ologies", "ology", "opsies", "opsy", "scopies", "scopy",
    "trophies", "trophy", "metries", "metry", "meters", "meter", "blasts", "blast",
    "oses", "osis", "omas", "oma", "zoic",
), key=len, reverse=True))

SCI_PREFIXES = (
    "pseudopseudo", "haemato", "hemato", "pseudo", "electro", "cardio", "gastro",
    "thermo", "chromo", "paleo", "archaeo", "crypto", "chloro", "phospho", "hydro",
    "neuro", "nitro", "amino", "cyclo", "photo", "astro", "micro", "macro",
    "tetra", "penta", "hexa", "hepta", "octa", "hyper", "intra", "supra", "retro",
    "poly", "mono", "nano", "cyto", "endo", "hypo", "exo",
)

PROPER_CATEGORIES = {"personal_name", "place", "brand", "holiday"}
SCARCE_BELOW = 50
STORE_SOLUTIONS_AT_OR_BELOW = 100

MUST_CONTAIN = (
    "substance", "wednesday", "looseleaf", "kalamazoo", "jacqueline", "yoyo",
    "aztec", "tnt", "hexakosioihexekontahexaphobia", "sphenopalatineganglioneuralgia",
    "gaywing", "hadjs", "hajjs", "mccaffrey", "antieavesdropping",
    "straightforwarder", "straightforwardest", "upsidedown", "phish", "noob",
    "butthole", "kaleidoscopical", "frankforter", "extraclassroom",
)
MUST_MISS = ("thursday", "sunday", *REMOVED)


def load_words(path: Path) -> set[str]:
    words: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        word = line.strip().lower()
        if word and word.isalpha():
            words.add(word)
    return words


def load_names(path: Path) -> set[str]:
    names: set[str] = set()
    text = path.read_text(encoding="latin-1")
    for line in text.splitlines():
        word = line.strip().lower()
        if len(word) >= 2 and word.isalpha():
            names.add(word)
    return names


def load_frequency(path: Path) -> dict[str, tuple[int, int]]:
    """Map word -> (rank starting at 1, count). File is already sorted by count."""
    ranks: dict[str, tuple[int, int]] = {}
    rank = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) < 2 or not parts[0].isalpha():
            continue
        word = parts[0].lower()
        try:
            count = int(parts[1])
        except ValueError:
            continue
        if word in ranks:
            continue
        rank += 1
        ranks[word] = (rank, count)
    return ranks


def frequency_band(rank: int | None) -> str:
    if rank is None:
        return "unlisted"
    if rank <= 5000:
        return "common"
    if rank <= 20000:
        return "familiar"
    if rank <= 60000:
        return "uncommon"
    return "rare"


def lexicon_class(in_enable1: bool, in_sowpods: bool, in_moby: bool, in_twl: bool) -> str:
    if not in_enable1 and not in_sowpods and not in_moby:
        return "manual"
    if in_moby and not in_enable1 and not in_sowpods:
        return "moby_only"
    if in_enable1 and not in_sowpods:
        return "enable_only"
    if in_sowpods and not in_enable1 and in_twl:
        return "twl_not_enable"
    if in_sowpods and not in_enable1:
        return "sowpods_only"
    return "core"


def compound_split(word: str, words: set[str]) -> str | None:
    best: tuple[int, str] | None = None
    for index in range(4, len(word) - 3):
        left, right = word[:index], word[index:]
        if right in COMPOUND_RIGHT_STOP:
            continue
        if left in words and right in words:
            balance = abs(len(left) - len(right))
            if best is None or balance < best[0]:
                best = (balance, f"{left}+{right}")
    return None if best is None else best[1]


def find_prefix(word: str, words: set[str], freq_rank: int | None) -> tuple[str | None, str | None]:
    for prefix in PREFIXES:
        if not word.startswith(prefix) or len(word) < len(prefix) + 4:
            continue
        remainder = word[len(prefix):]
        if remainder not in words:
            continue
        if prefix in GUARDED_PREFIXES and freq_rank is not None and freq_rank <= GUARDED_PREFIX_MAX_RANK:
            continue
        return prefix, remainder
    return None, None


def scientific_hit(word: str) -> str | None:
    hits: list[str] = []
    for suffix in SCI_SUFFIXES:
        if word.endswith(suffix) and len(word) >= len(suffix) + 3:
            hits.append(suffix)
            break
    for prefix in SCI_PREFIXES:
        if word.startswith(prefix) and len(word) >= len(prefix) + 4:
            hits.append(prefix)
            break
    return "+".join(hits) if hits else None


def ngram_counts(words: list[str], size: int) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for word in words:
        if len(word) < size:
            continue
        seen = {word[index:index + size] for index in range(len(word) - size + 1)}
        for gram in seen:
            counts[gram] += 1
    return counts


def rarest(word: str, size: int, counts: dict[str, int]) -> tuple[str | None, int | None, int, list[str]]:
    if len(word) < size:
        return None, None, 0, []
    best_gram: str | None = None
    best_count: int | None = None
    scarce = 0
    unique: list[str] = []
    seen: set[str] = set()
    for index in range(len(word) - size + 1):
        gram = word[index:index + size]
        if gram in seen:
            continue
        seen.add(gram)
        count = counts[gram]
        if best_count is None or count < best_count:
            best_gram = gram
            best_count = count
        if count < SCARCE_BELOW:
            scarce += 1
        if count == 1 and size < 4:
            unique.append(gram)
    return best_gram, best_count, scarce, unique


def tags_for(row: dict) -> str:
    tags: list[str] = [row["lexicon_class"], row["freq_band"]]
    if row["manual_category"]:
        tags.append(row["manual_category"])
    if row["is_compound"]:
        tags.append("compound")
    if row["is_prefixed"]:
        tags.append("prefixed")
    if row["is_scientific"]:
        tags.append("scientific")
    if row["is_hyphenated"]:
        tags.append("hyphen")
    if row["likely_proper"]:
        tags.append("proper")
    if row["has_jqxz"]:
        tags.append("jqxz")
    if row["rarest2_count"] is not None and row["rarest2_count"] < SCARCE_BELOW:
        tags.append("prompt2<50")
    if row["rarest3_count"] is not None and row["rarest3_count"] < SCARCE_BELOW:
        tags.append("prompt3<50")
    if row["unique_prompts"]:
        tags.append("unique-prompt")
    return " ".join(tags)


def build() -> None:
    enable1 = load_words(RAW / "enable1.txt")
    sowpods = load_words(RAW / "sowpods.txt")
    moby = load_words(RAW / "crosswd.txt")
    twl = load_words(RAW / "twl06.txt")
    archived = load_words(RAW / "wayback_complete.txt")
    names = load_names(RAW / "names.txt")
    frequency = load_frequency(RAW / "count_1w.txt")
    print(
        f"loaded enable1={len(enable1)} sowpods={len(sowpods)} moby={len(moby)} "
        f"twl={len(twl)} archived={len(archived)} names={len(names)} freq={len(frequency)}"
    )

    missing_removed = sorted(set(REMOVED) - moby)
    if missing_removed:
        raise SystemExit(f"Expected removed words in Moby, missing {missing_removed}")

    moby_kept = moby - set(REMOVED)
    union = enable1 | sowpods | moby_kept
    manual = archived - union
    extra_union = union - archived
    if extra_union:
        sample = ", ".join(sorted(extra_union)[:20])
        raise SystemExit(f"{len(extra_union)} source words are not in the verified list: {sample}")
    unknown = sorted(set(MANUAL_CATEGORY) ^ manual)
    if unknown:
        raise SystemExit(
            "Manual category map does not match sourceless words.\n"
            + "\n".join(unknown)
        )

    words = sorted(archived)
    for word in MUST_CONTAIN:
        if word not in archived:
            raise SystemExit(f"Missing expected word {word}")
    for word in MUST_MISS:
        if word in archived:
            raise SystemExit(f"Excluded word is present: {word}")

    glenn_path = RAW / "glenn_dictionary.txt"
    if glenn_path.exists():
        glenn = load_words(glenn_path)
        if not glenn <= archived:
            raise SystemExit("Glenn's earlier list is not a subset of the verified dictionary")
        print(f"glenn subset ok; verified list has {len(archived - glenn)} later words")

    print("counting prompts")
    counts = {size: ngram_counts(words, size) for size in (2, 3, 4)}

    rows: list[dict] = []
    solution_rows: list[tuple[str, str]] = []
    for word in words:
        freq = frequency.get(word)
        freq_rank = None if freq is None else freq[0]
        freq_count = None if freq is None else freq[1]
        in_enable1 = word in enable1
        in_sowpods = word in sowpods
        in_moby = word in moby_kept
        in_twl = word in twl
        kind = lexicon_class(in_enable1, in_sowpods, in_moby, in_twl)
        category = MANUAL_CATEGORY.get(word)
        split = compound_split(word, archived)
        prefix, remainder = find_prefix(word, archived, freq_rank)
        science = scientific_hit(word)
        in_name = word in names
        likely_proper = int(
            (category in PROPER_CATEGORIES)
            or (in_name and len(word) >= 4 and (freq_rank is None or freq_rank > 8000))
        )
        unique: list[str] = []
        rare: dict[int, tuple[str | None, int | None, int]] = {}
        for size in (2, 3, 4):
            gram, count, scarce, size_unique = rarest(word, size, counts[size])
            rare[size] = (gram, count, scarce)
            unique.extend(size_unique)
            if count is not None and count <= STORE_SOLUTIONS_AT_OR_BELOW:
                seen: set[str] = set()
                for index in range(len(word) - size + 1):
                    prompt = word[index:index + size]
                    if prompt in seen:
                        continue
                    seen.add(prompt)
                    if counts[size][prompt] <= STORE_SOLUTIONS_AT_OR_BELOW:
                        solution_rows.append((prompt, word))
        row = {
            "word": word,
            "length": len(word),
            "in_enable1": int(in_enable1),
            "in_sowpods": int(in_sowpods),
            "in_moby": int(in_moby),
            "in_twl": int(in_twl),
            "in_name_list": int(in_name),
            "lexicon_class": kind,
            "manual_category": category,
            "frequency": freq_count,
            "freq_rank": freq_rank,
            "freq_band": frequency_band(freq_rank),
            "is_compound": int(split is not None),
            "compound_split": split,
            "is_prefixed": int(prefix is not None),
            "prefix": prefix,
            "prefix_remainder": remainder,
            "is_scientific": int(science is not None),
            "scientific_hit": science,
            "is_hyphenated": int("-" in word),
            "likely_proper": likely_proper,
            "has_jqxz": int(any(letter in word for letter in "jqxz")),
            "rarest2": rare[2][0],
            "rarest2_count": rare[2][1],
            "rarest3": rare[3][0],
            "rarest3_count": rare[3][1],
            "rarest4": rare[4][0],
            "rarest4_count": rare[4][1],
            "scarce2": rare[2][2],
            "scarce3": rare[3][2],
            "scarce4": rare[4][2],
            "unique_prompts": ",".join(sorted(set(unique))),
        }
        row["tags"] = tags_for(row)
        rows.append(row)

    digest = hashlib.sha256("\n".join(words).encode("utf-8")).hexdigest()
    WORDS_PATH.write_text("\n".join(words) + "\n", encoding="utf-8")
    manual_lines = ["word\tcategory"]
    manual_lines.extend(f"{word}\t{MANUAL_CATEGORY[word]}" for word in sorted(MANUAL_CATEGORY))
    MANUAL_PATH.write_text("\n".join(manual_lines) + "\n", encoding="utf-8")

    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA temp_store=MEMORY")
    columns = [
        "word TEXT PRIMARY KEY",
        "length INTEGER NOT NULL",
        "in_enable1 INTEGER NOT NULL",
        "in_sowpods INTEGER NOT NULL",
        "in_moby INTEGER NOT NULL",
        "in_twl INTEGER NOT NULL",
        "in_name_list INTEGER NOT NULL",
        "lexicon_class TEXT NOT NULL",
        "manual_category TEXT",
        "frequency INTEGER",
        "freq_rank INTEGER",
        "freq_band TEXT NOT NULL",
        "is_compound INTEGER NOT NULL",
        "compound_split TEXT",
        "is_prefixed INTEGER NOT NULL",
        "prefix TEXT",
        "prefix_remainder TEXT",
        "is_scientific INTEGER NOT NULL",
        "scientific_hit TEXT",
        "is_hyphenated INTEGER NOT NULL",
        "likely_proper INTEGER NOT NULL",
        "has_jqxz INTEGER NOT NULL",
        "rarest2 TEXT",
        "rarest2_count INTEGER",
        "rarest3 TEXT",
        "rarest3_count INTEGER",
        "rarest4 TEXT",
        "rarest4_count INTEGER",
        "scarce2 INTEGER NOT NULL",
        "scarce3 INTEGER NOT NULL",
        "scarce4 INTEGER NOT NULL",
        "unique_prompts TEXT NOT NULL",
        "tags TEXT NOT NULL",
    ]
    conn.execute(f"CREATE TABLE words ({', '.join(columns)})")
    conn.execute("CREATE TABLE prompts (prompt TEXT PRIMARY KEY, length INTEGER NOT NULL, solution_count INTEGER NOT NULL)")
    conn.execute("CREATE TABLE scarce_solutions (prompt TEXT NOT NULL, word TEXT NOT NULL, PRIMARY KEY (prompt, word))")
    conn.execute("CREATE TABLE excluded (word TEXT PRIMARY KEY, reason TEXT NOT NULL)")
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    word_columns = [
        "word", "length", "in_enable1", "in_sowpods", "in_moby", "in_twl", "in_name_list",
        "lexicon_class", "manual_category", "frequency", "freq_rank", "freq_band",
        "is_compound", "compound_split", "is_prefixed", "prefix", "prefix_remainder",
        "is_scientific", "scientific_hit", "is_hyphenated", "likely_proper", "has_jqxz",
        "rarest2", "rarest2_count", "rarest3", "rarest3_count", "rarest4", "rarest4_count",
        "scarce2", "scarce3", "scarce4", "unique_prompts", "tags",
    ]
    placeholders = ", ".join("?" for _ in word_columns)
    conn.executemany(
        f"INSERT INTO words ({', '.join(word_columns)}) VALUES ({placeholders})",
        [tuple(row[column] for column in word_columns) for row in rows],
    )
    conn.executemany(
        "INSERT INTO prompts (prompt, length, solution_count) VALUES (?, ?, ?)",
        (
            (prompt, size, count)
            for size, bucket in counts.items()
            for prompt, count in bucket.items()
        ),
    )
    conn.executemany("INSERT INTO scarce_solutions (prompt, word) VALUES (?, ?)", solution_rows)
    conn.executemany("INSERT INTO excluded (word, reason) VALUES (?, ?)", REMOVED.items())
    meta = {
        "word_count": str(len(words)),
        "sha256": digest,
        "enable1": str(len(enable1)),
        "sowpods": str(len(sowpods)),
        "moby": str(len(moby_kept)),
        "moby_raw": str(len(moby)),
        "twl": str(len(twl)),
        "union": str(len(union)),
        "manual": str(len(manual)),
        "removed": str(len(REMOVED)),
        "formula": "enable1 ∪ sowpods ∪ (moby crosswords − 6 removed) ∪ 132 hand-added words",
        "scarce_below": str(SCARCE_BELOW),
        "solutions_stored_at_or_below": str(STORE_SOLUTIONS_AT_OR_BELOW),
        "freq_bands": "common<=5000 familiar<=20000 uncommon<=60000 rare=listed unlisted=absent",
    }
    conn.executemany("INSERT INTO meta (key, value) VALUES (?, ?)", meta.items())
    print("indexing")
    conn.execute("CREATE INDEX idx_words_class ON words(lexicon_class)")
    conn.execute("CREATE INDEX idx_words_length ON words(length)")
    conn.execute("CREATE INDEX idx_words_band ON words(freq_band)")
    conn.execute("CREATE INDEX idx_words_compound ON words(is_compound)")
    conn.execute("CREATE INDEX idx_words_scientific ON words(is_scientific)")
    conn.execute("CREATE INDEX idx_words_prefixed ON words(is_prefixed)")
    conn.execute("CREATE INDEX idx_words_rarest3 ON words(rarest3_count)")
    conn.execute("CREATE INDEX idx_words_rarest2 ON words(rarest2_count)")
    conn.execute("CREATE INDEX idx_prompts_difficulty ON prompts(length, solution_count)")
    conn.execute("CREATE INDEX idx_scarce_word ON scarce_solutions(word)")
    conn.commit()
    stored = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
    prompt_count = conn.execute("SELECT COUNT(*) FROM prompts").fetchone()[0]
    solution_count = conn.execute("SELECT COUNT(*) FROM scarce_solutions").fetchone()[0]
    conn.close()
    if stored != 273278:
        raise SystemExit(f"Expected 273278 words, stored {stored}")

    # Claims from the dictionary write-up. Fail loudly if a prompt is no longer unique.
    checks = {
        "tnt": "tnt",
        "yoy": "yoyo",
        "azt": "aztec",
        "zte": "aztec",
        "xek": "hexakosioihexekontahexaphobia",
        "djs": "hadjs",
        "jjs": "hajjs",
        "mcc": "mccaffrey",
        "iea": "antieavesdropping",
    }
    count_lookup = {size: counts[size] for size in counts}
    for prompt, expected in checks.items():
        found = None
        for size, bucket in count_lookup.items():
            if prompt in bucket:
                found = bucket[prompt]
                break
        if found != 1:
            raise SystemExit(f"Prompt {prompt} was expected to be unique ({expected}) but has {found} solutions")

    print(f"wrote {DB_PATH}")
    print(f"words={stored} prompts={prompt_count} stored_solutions={solution_count}")
    print(f"sha256={digest}")


if __name__ == "__main__":
    build()
