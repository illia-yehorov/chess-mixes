"""Tests for shared TOML defaults and per-mix overrides."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import tomllib
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import generate_mix
from generate_mix import load_config, merge_config


CONFIG_DIR = Path(__file__).resolve().parents[1] / "configs"
MIXES = (
    "1-basic.toml",
    "2-deflection-attraction.toml",
    "3-interference.toml",
    "4-clearance.toml",
)


class SharedConfigTests(unittest.TestCase):
    def test_all_existing_mixes_inherit_shared_values(self):
        for filename in MIXES:
            with self.subTest(mix=filename):
                path = CONFIG_DIR / filename
                with path.open("rb") as stream:
                    raw = tomllib.load(stream)
                self.assertNotIn("source", raw)
                self.assertNotIn("template", raw)
                self.assertNotIn("max_puzzles_per_theme", raw)
                self.assertNotIn("puzzles_per_click", raw)
                self.assertNotIn("popularity_min", raw)
                self.assertNotIn("min_plays", raw)
                self.assertNotIn("quality_weights", raw)

                config = load_config(path)
                self.assertEqual(config["source"], "lichess_db_puzzle.csv.zst")
                self.assertEqual(config["template"], "mix.html")
                self.assertEqual(config["puzzles_per_click"], 10)
                self.assertEqual(config["max_puzzles_per_theme"], 1000)
                self.assertEqual(config["popularity_min"], 85)
                self.assertEqual(config["min_plays"], 200)
                self.assertEqual(config["quality_weights"], {
                    "popularity": 80, "plays": 15, "rating_deviation": 5
                })
                self.assertEqual(config["moves"], {"min": 2, "max": 4})
                self.assertEqual(config["page"]["heading"],
                                 "Лёха & Папа — шахматная солянка")
                self.assertIn("title", config["page"])
                self.assertTrue(config["themes"])
                self.assertTrue(config["output"]["filename"].startswith("mix"))
                self.assertNotEqual(config["name"], "Шахматная солянка")

    def test_existing_rating_and_move_weights_are_preserved(self):
        for filename in MIXES:
            with self.subTest(mix=filename):
                cfg = load_config(CONFIG_DIR / filename)
                self.assertEqual(cfg["rating"],
                                 {"min": 900, "max": 1200} if filename.startswith("4-")
                                 else {"min": 1000, "max": 1400})
                weights = cfg["move_weights"]
                self.assertEqual(weights["3"], 50)
                if filename.startswith(("3-", "4-")):
                    self.assertEqual((weights["2"], weights["4"]), (30, 20))
                else:
                    self.assertEqual((weights["2"], weights["4"]), (20, 30))
                if filename.startswith("1-"):
                    self.assertEqual(weights["1"], 10)
                if filename.startswith("2-"):
                    self.assertEqual(weights["1"], 20)
                if filename.startswith("3-"):
                    self.assertEqual(weights["5"], 10)

    def test_nested_overrides_keep_other_inherited_keys(self):
        with TemporaryDirectory() as temp:
            directory = Path(temp)
            default_path = directory / "0-defaults.toml"
            default_path.write_text(
                (CONFIG_DIR / "0-defaults.toml").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            mix_path = directory / "custom.toml"
            mix_path.write_text(
                'name = "Custom"\n'
                'max_puzzles_per_theme = 25\n'
                '[rating]\nmax = 1250\n'
                '[move_weights]\n"3" = 0\n'
                '[quality_weights]\nplays = 25\n'
                '[page]\ntitle = "Custom page"\n'
                '[output]\nfilename = "custom.html"\n'
                '[[themes]]\nid = "fork"\nname = "Fork"\nweight = 1\n',
                encoding="utf-8",
            )
            with patch.object(generate_mix, "DEFAULT_CONFIG_PATH", default_path):
                merged = load_config(mix_path)

            self.assertEqual(merged["name"], "Custom")
            self.assertEqual(merged["max_puzzles_per_theme"], 25)
            self.assertEqual(merged["rating"], {"min": 1000, "max": 1250})
            self.assertEqual(merged["move_weights"],
                             {"2": 20, "3": 0, "4": 30})
            self.assertEqual(merged["quality_weights"], {
                "popularity": 80, "plays": 25, "rating_deviation": 5
            })
            self.assertEqual(merged["page"]["title"], "Custom page")
            self.assertEqual(merged["page"]["heading"],
                             "Лёха & Папа — шахматная солянка")

    def test_edited_shared_defaults_propagate_to_all_mixes(self):
        content = (CONFIG_DIR / "0-defaults.toml").read_text(encoding="utf-8")
        updated = content.replace("max_puzzles_per_theme = 1000",
                                  "max_puzzles_per_theme = 77").replace(
                                      "min_plays = 200", "min_plays = 300")
        with TemporaryDirectory() as temp:
            default_path = Path(temp) / "0-defaults.toml"
            default_path.write_text(updated, encoding="utf-8")
            with patch.object(generate_mix, "DEFAULT_CONFIG_PATH", default_path):
                for filename in MIXES:
                    merged = load_config(CONFIG_DIR / filename)
                    self.assertEqual(merged["max_puzzles_per_theme"], 77)
                    self.assertEqual(merged["min_plays"], 300)

    def test_theme_array_is_replaced_not_extended(self):
        shared = {"themes": [{"id": "fork"}, {"id": "pin"}],
                  "rating": {"min": 800, "max": 1600}}
        override = {"themes": [{"id": "clearance"}],
                    "rating": {"min": 900}}
        merged = merge_config(shared, override)
        self.assertEqual(merged["themes"], [{"id": "clearance"}])
        self.assertEqual(merged["rating"], {"min": 900, "max": 1600})
        self.assertEqual(shared["rating"], {"min": 800, "max": 1600})

    def test_shared_config_cannot_be_generated_as_a_mix(self):
        with self.assertRaisesRegex(RuntimeError, "not a mix"):
            load_config(CONFIG_DIR / "0-defaults.toml")

    def test_missing_shared_config_fails_clearly(self):
        with TemporaryDirectory() as temp:
            with patch.object(generate_mix, "DEFAULT_CONFIG_PATH",
                              Path(temp) / "missing-defaults.toml"):
                with self.assertRaisesRegex(RuntimeError,
                                            "Shared config file not found"):
                    load_config(CONFIG_DIR / MIXES[0])


if __name__ == "__main__":
    unittest.main()
