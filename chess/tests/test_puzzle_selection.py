"""Regression tests for bounded, quality-ranked Lichess puzzle pools."""

import csv
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

import zstandard as zstd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from generate_mix import (
    allocate_move_quotas,
    print_statistics,
    read_puzzles,
    validate_config,
)


def config(limit=10):
    return {
        "name": "Test mix",
        "source": "test.csv.zst",
        "template": "mix.html",
        "puzzles_per_click": 10,
        "max_puzzles_per_theme": limit,
        "popularity_min": 70,
        "min_plays": 50,
        "rating": {"min": 1000, "max": 1400},
        "moves": {"min": 2, "max": 4},
        "move_weights": {"2": 20, "3": 50, "4": 30},
        "output": {"filename": "test.html"},
        "page": {"title": "Test", "heading": "Test"},
        "themes": [{"id": "fork", "name": "Fork", "weight": 1.0}],
    }


def puzzle(puzzle_id, move_count, popularity=85, deviation=70,
           plays=100, rating=1100, themes="fork"):
    moves = " ".join(["e2e4", "e7e5"] * move_count)
    return [
        puzzle_id, "fen", moves, str(rating), str(deviation),
        str(popularity), str(plays), themes,
        "https://lichess.org/Ab1Cd2Ef/black#42", "",
    ]


def read_rows(rows, cfg):
    with TemporaryDirectory() as directory:
        csv_data = StringIO()
        writer = csv.writer(csv_data)
        writer.writerows(rows)
        path = Path(directory) / "test.csv.zst"
        path.write_bytes(zstd.ZstdCompressor().compress(
            csv_data.getvalue().encode("utf-8")
        ))
        return read_puzzles(path, cfg, [theme["id"] for theme in cfg["themes"]],
                            [2, 3, 4])


class PoolSelectionTests(unittest.TestCase):
    def test_quota_weights_split_exactly(self):
        self.assertEqual(
            allocate_move_quotas(5000, {2: 7000, 3: 7000, 4: 7000},
                                 {2: 20, 3: 50, 4: 30}),
            {2: 1000, 3: 2500, 4: 1500},
        )

    def test_shortage_is_redistributed(self):
        self.assertEqual(
            allocate_move_quotas(10, {2: 1, 3: 15, 4: 15},
                                 {2: 20, 3: 50, 4: 30}),
            {2: 1, 3: 6, 4: 3},
        )

    def test_integer_quotas_handle_rounding(self):
        self.assertEqual(
            sum(allocate_move_quotas(7, {2: 10, 3: 10, 4: 10},
                                     {2: 20, 3: 50, 4: 30}).values()),
            7,
        )

    def test_found_and_selected_counts_and_compact_validation(self):
        cfg = config(10)
        rows = [
            puzzle(f"m{length}-{index}", length, popularity=90,
                   deviation=60, plays=100 + index)
            for length in (2, 3, 4) for index in range(12)
        ]
        selected, snapshots, found = read_rows(rows, cfg)
        self.assertEqual({length: len(selected["fork"][length])
                          for length in (2, 3, 4)},
                         {2: 2, 3: 5, 4: 3})
        self.assertEqual(found["fork"], {2: 12, 3: 12, 4: 12})
        ids = {puzzle_id for group in selected["fork"].values()
               for puzzle_id in group}
        self.assertEqual(set(snapshots), ids)
        self.assertEqual(len(snapshots), 10)
        self.assertIn("m2-11", selected["fork"][2])

        output = Path(__file__).resolve().parents[2] / "site/mixes/test.html"
        log = StringIO()
        with redirect_stdout(log):
            print_statistics(cfg, cfg["themes"], [2, 3, 4], selected,
                             {2: 20, 3: 50, 4: 30}, output, found)
        self.assertIn("найдено 36, отобрано 10", log.getvalue())
        self.assertIn("2 ход.: найдено 12, отобрано 2", log.getvalue())
        self.assertIn("3 ход.: найдено 12, отобрано 5", log.getvalue())
        self.assertIn("4 ход.: найдено 12, отобрано 3", log.getvalue())

    def test_popularity_then_deviation_then_plays(self):
        cfg = config(2)
        cfg["move_weights"] = {"2": 1}
        rows = [
            puzzle("low-pop", 2, popularity=90, deviation=20, plays=10000),
            puzzle("high-rd", 2, popularity=95, deviation=90, plays=10000),
            puzzle("few-plays", 2, popularity=95, deviation=40, plays=60),
            puzzle("many-plays", 2, popularity=95, deviation=40, plays=500),
            puzzle("bad-rating", 2, popularity=100, deviation=5,
                   plays=10000, rating=1800),
            puzzle("bad-plays", 2, popularity=100, deviation=5, plays=10),
        ]
        selected, snapshots, found = read_rows(rows, cfg)
        self.assertEqual(selected["fork"][2], ["many-plays", "few-plays"])
        self.assertEqual(found["fork"][2], 4)
        self.assertEqual(set(snapshots), {"many-plays", "few-plays"})

    def test_missing_move_lengths_give_remaining_slots_to_others(self):
        cfg = config(10)
        rows = (
            [puzzle("short-only", 2)]
            + [puzzle(f"medium-{i}", 3) for i in range(15)]
            + [puzzle(f"long-{i}", 4) for i in range(15)]
        )
        selected, _, found = read_rows(rows, cfg)
        self.assertEqual(found["fork"], {2: 1, 3: 15, 4: 15})
        self.assertEqual(
            [len(selected["fork"][length]) for length in (2, 3, 4)],
            [1, 6, 3],
        )

    def test_zero_disables_limit_and_omitted_key_defaults(self):
        cfg = config(0)
        selected, snapshots, found = read_rows(
            [puzzle(f"any-{i}", 2) for i in range(20)], cfg
        )
        self.assertEqual(len(selected["fork"][2]), 20)
        self.assertEqual(len(snapshots), 20)
        self.assertEqual(found["fork"][2], 20)
        validate_config(cfg)

        cfg.pop("max_puzzles_per_theme")
        validate_config(cfg)
        self.assertEqual(
            allocate_move_quotas(5000, {2: 6000, 3: 6000, 4: 6000},
                                 {2: 20, 3: 50, 4: 30})[2],
            1000,
        )

    def test_invalid_limits_are_rejected(self):
        for invalid in (-1, 2.5, True, "100"):
            with self.subTest(value=invalid):
                with self.assertRaisesRegex(RuntimeError, "max_puzzles_per_theme"):
                    validate_config(config(invalid))

    def test_same_database_in_different_order_gives_same_ids(self):
        cfg = config(5)
        rows = [puzzle(f"id{i:03}", 3, popularity=i % 5 + 80,
                       deviation=100 - i, plays=100 + i)
                for i in range(40)]
        first, _, _ = read_rows(rows, cfg)
        second, _, _ = read_rows(list(reversed(rows)), cfg)
        self.assertEqual(first, second)

    def test_overlapping_themes_keep_independent_limits(self):
        cfg = config(2)
        cfg["themes"].append({"id": "pin", "name": "Pin", "weight": 1})
        cfg["move_weights"] = {"2": 1}
        rows = [puzzle(f"shared-{i}", 2, themes="fork pin")
                for i in range(5)]
        selected, snapshots, found = read_rows(rows, cfg)
        self.assertEqual(len(selected["fork"][2]), 2)
        self.assertEqual(len(selected["pin"][2]), 2)
        self.assertEqual(found["fork"][2], 5)
        self.assertEqual(found["pin"][2], 5)
        self.assertEqual(len(snapshots), 2)


if __name__ == "__main__":
    unittest.main()
