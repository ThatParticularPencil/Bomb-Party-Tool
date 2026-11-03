"""Read-only access to the built BombParty dictionary."""

from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "bombparty.sqlite"

_ORDERS = {
    "word": "word",
    "length": "length, word",
    "frequency": "freq_rank IS NULL, freq_rank, word",
    "rarest2": "rarest2_count IS NULL, rarest2_count, word",
    "rarest3": "rarest3_count IS NULL, rarest3_count, word",
    "scarce3": "scarce3 DESC, word",
    "longest": "length DESC, word",
}


class Dictionary:
    def __init__(self, path: Path | str = DEFAULT_DB):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(
                f"No dictionary database at {self.path}. Run scripts/build_dictionary.py first."
            )
        self.conn = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> Dictionary:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def word_count(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM words").fetchone()[0])

    def meta(self) -> dict[str, str]:
        return {row["key"]: row["value"] for row in self.conn.execute("SELECT key, value FROM meta")}

    def get(self, word: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM words WHERE word = ?", (word.lower(),)).fetchone()
        return dict(row) if row else None

    def excluded(self) -> list[dict]:
        return [dict(row) for row in self.conn.execute("SELECT word, reason FROM excluded ORDER BY word")]

    def search(
        self,
        *,
        contains: str | None = None,
        starts: str | None = None,
        ends: str | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        lexicon_class: str | None = None,
        freq_band: str | None = None,
        manual_category: str | None = None,
        compound: bool | None = None,
        scientific: bool | None = None,
        prefixed: bool | None = None,
        hyphenated: bool | None = None,
        proper: bool | None = None,
        manual: bool | None = None,
        has_jqxz: bool | None = None,
        in_twl: bool | None = None,
        in_enable1: bool | None = None,
        in_sowpods: bool | None = None,
        in_moby: bool | None = None,
        max_rarest2: int | None = None,
        max_rarest3: int | None = None,
        under_50: bool | None = None,
        limit: int = 50,
        offset: int = 0,
        order: str = "word",
    ) -> list[dict]:
        if order not in _ORDERS:
            raise ValueError(f"Unknown order {order!r}. Choose from: {', '.join(_ORDERS)}")
        clauses: list[str] = []
        params: list[object] = []

        def like(column: str, value: str, mode: str) -> None:
            escaped = value.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            if mode == "contains":
                pattern = f"%{escaped}%"
            elif mode == "starts":
                pattern = f"{escaped}%"
            else:
                pattern = f"%{escaped}"
            clauses.append(f"{column} LIKE ? ESCAPE '\\'")
            params.append(pattern)

        if contains:
            like("word", contains, "contains")
        if starts:
            like("word", starts, "starts")
        if ends:
            like("word", ends, "ends")
        if min_length is not None:
            clauses.append("length >= ?")
            params.append(min_length)
        if max_length is not None:
            clauses.append("length <= ?")
            params.append(max_length)
        if lexicon_class:
            clauses.append("lexicon_class = ?")
            params.append(lexicon_class)
        if freq_band:
            clauses.append("freq_band = ?")
            params.append(freq_band)
        if manual_category:
            clauses.append("manual_category = ?")
            params.append(manual_category)
        for flag, column in (
            (compound, "is_compound"),
            (scientific, "is_scientific"),
            (prefixed, "is_prefixed"),
            (hyphenated, "is_hyphenated"),
            (proper, "likely_proper"),
            (has_jqxz, "has_jqxz"),
            (in_twl, "in_twl"),
            (in_enable1, "in_enable1"),
            (in_sowpods, "in_sowpods"),
            (in_moby, "in_moby"),
        ):
            if flag is not None:
                clauses.append(f"{column} = ?")
                params.append(int(flag))
        if manual is True:
            clauses.append("lexicon_class = 'manual'")
        elif manual is False:
            clauses.append("lexicon_class != 'manual'")
        if max_rarest2 is not None:
            clauses.append("rarest2_count <= ?")
            params.append(max_rarest2)
        if max_rarest3 is not None:
            clauses.append("rarest3_count <= ?")
            params.append(max_rarest3)
        if under_50:
            clauses.append(
                "(rarest2_count < 50 OR (rarest3_count IS NOT NULL AND rarest3_count < 50))"
            )
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        params.extend([limit, offset])
        sql = f"SELECT * FROM words{where} ORDER BY {_ORDERS[order]} LIMIT ? OFFSET ?"
        return [dict(row) for row in self.conn.execute(sql, params)]

    def prompts(
        self,
        *,
        length: int = 3,
        max_count: int = 49,
        min_count: int = 1,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        sql = """
            SELECT prompt, length, solution_count
            FROM prompts
            WHERE length = ? AND solution_count BETWEEN ? AND ?
            ORDER BY solution_count, prompt
            LIMIT ? OFFSET ?
        """
        return [
            dict(row)
            for row in self.conn.execute(sql, (length, min_count, max_count, limit, offset))
        ]

    def sample_prompts(
        self,
        *,
        length: int = 3,
        min_count: int = 1,
        max_count: int = 49,
        limit: int = 10,
        compound: bool | None = None,
        scientific: bool | None = None,
        prefixed: bool | None = None,
        freq_band: str | None = None,
    ) -> list[dict]:
        where = ["p.length = ?", "p.solution_count BETWEEN ? AND ?"]
        params: list[object] = [length, min_count, max_count]
        join = ""
        word_filters = []
        if compound:
            word_filters.append("w.is_compound = 1")
        if scientific:
            word_filters.append("w.is_scientific = 1")
        if prefixed:
            word_filters.append("w.is_prefixed = 1")
        if freq_band:
            word_filters.append("w.freq_band = ?")
            params.append(freq_band)
        if word_filters:
            join = "JOIN scarce_solutions s ON s.prompt = p.prompt JOIN words w ON w.word = s.word"
            where.extend(word_filters)
        params.append(limit)
        sql = f"""
            SELECT DISTINCT p.prompt, p.length, p.solution_count
            FROM prompts p
            {join}
            WHERE {' AND '.join(where)}
            ORDER BY RANDOM()
            LIMIT ?
        """
        return [dict(row) for row in self.conn.execute(sql, params)]

    def hint(
        self,
        prompt: str,
        *,
        compound: bool | None = None,
        scientific: bool | None = None,
        prefixed: bool | None = None,
        freq_band: str | None = None,
    ) -> str | None:
        prompt = prompt.lower()
        where = ["s.prompt = ?"]
        params: list[object] = [prompt]
        if compound:
            where.append("w.is_compound = 1")
        if scientific:
            where.append("w.is_scientific = 1")
        if prefixed:
            where.append("w.is_prefixed = 1")
        if freq_band:
            where.append("w.freq_band = ?")
            params.append(freq_band)
        sql = f"""
            SELECT w.word FROM scarce_solutions s
            JOIN words w ON w.word = s.word
            WHERE {' AND '.join(where)}
            ORDER BY w.freq_rank IS NULL, w.freq_rank, w.length, w.word
            LIMIT 1
        """
        row = self.conn.execute(sql, params).fetchone()
        if row:
            return row[0]
        if compound or scientific or prefixed or freq_band:
            return None
        escaped = prompt.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        row = self.conn.execute(
            """
            SELECT word FROM words
            WHERE word LIKE ? ESCAPE '\\'
            ORDER BY freq_rank IS NULL, freq_rank, length, word
            LIMIT 1
            """,
            (f"%{escaped}%",),
        ).fetchone()
        return None if row is None else row[0]

    def prompt_count(self, prompt: str) -> int | None:
        row = self.conn.execute(
            "SELECT solution_count FROM prompts WHERE prompt = ?", (prompt.lower(),)
        ).fetchone()
        return None if row is None else int(row[0])

    def solutions(self, prompt: str, *, limit: int = 200) -> dict:
        prompt = prompt.lower()
        count = self.prompt_count(prompt)
        if count is not None and count <= 100:
            words = [
                row[0]
                for row in self.conn.execute(
                    """
                    SELECT word FROM scarce_solutions
                    WHERE prompt = ?
                    ORDER BY word
                    LIMIT ?
                    """,
                    (prompt, limit),
                )
            ]
            return {"prompt": prompt, "solution_count": count, "words": words, "complete": count <= limit}
        escaped = prompt.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        words = [
            row[0]
            for row in self.conn.execute(
                "SELECT word FROM words WHERE word LIKE ? ESCAPE '\\' ORDER BY word LIMIT ?",
                (f"%{escaped}%", limit),
            )
        ]
        return {
            "prompt": prompt,
            "solution_count": count if count is not None else len(words),
            "words": words,
            "complete": count is not None and count <= limit,
        }

    def stats(self) -> dict[str, object]:
        def counts(sql: str) -> list[tuple]:
            return [(row[0], row[1]) for row in self.conn.execute(sql)]

        return {
            "meta": self.meta(),
            "words": self.word_count(),
            "lexicon_class": counts("SELECT lexicon_class, COUNT(*) FROM words GROUP BY 1 ORDER BY 2 DESC"),
            "freq_band": counts("SELECT freq_band, COUNT(*) FROM words GROUP BY 1 ORDER BY 2 DESC"),
            "manual_category": counts(
                "SELECT manual_category, COUNT(*) FROM words WHERE manual_category IS NOT NULL GROUP BY 1 ORDER BY 2 DESC"
            ),
            "flags": {
                "compound": self._flag("is_compound"),
                "prefixed": self._flag("is_prefixed"),
                "scientific": self._flag("is_scientific"),
                "hyphenated": self._flag("is_hyphenated"),
                "likely_proper": self._flag("likely_proper"),
                "has_jqxz": self._flag("has_jqxz"),
                "under_50_prompt": self.conn.execute(
                    """
                    SELECT COUNT(*) FROM words
                    WHERE rarest2_count < 50
                       OR (rarest3_count IS NOT NULL AND rarest3_count < 50)
                    """
                ).fetchone()[0],
                "unique_prompt_words": self.conn.execute(
                    "SELECT COUNT(*) FROM words WHERE unique_prompts != ''"
                ).fetchone()[0],
            },
            "prompts": [
                {
                    "length": row[0],
                    "prompts": row[1],
                    "min_solutions": row[2],
                    "max_solutions": row[3],
                    "under_50": row[4],
                    "unique": row[5],
                }
                for row in self.conn.execute(
                    """
                    SELECT length,
                           COUNT(*),
                           MIN(solution_count),
                           MAX(solution_count),
                           SUM(solution_count < 50),
                           SUM(solution_count = 1)
                    FROM prompts
                    GROUP BY 1
                    ORDER BY 1
                    """
                )
            ],
        }

    def _flag(self, column: str) -> int:
        return int(self.conn.execute(f"SELECT COUNT(*) FROM words WHERE {column} = 1").fetchone()[0])


def open_dictionary(path: Path | str = DEFAULT_DB) -> Dictionary:
    return Dictionary(path)
