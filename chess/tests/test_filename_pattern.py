"""Tests for output filename date placeholders."""

from contextlib import redirect_stdout
from datetime import date
from io import StringIO
from html import escape
from pathlib import Path
import sys
import tomllib
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from generate_mix import (
    build_pattern_values, format_pattern, print_statistics, render_template,
)


class FilenamePatternTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "name": "Basic",
            "rating": {"min": 900, "max": 1200},
            "moves": {"min": 2, "max": 4},
        }
        self.values = build_pattern_values(
            self.config, "123", "2-4", date(2026, 1, 9)
        )

    def test_short_date_and_existing_placeholders(self) -> None:
        filename = format_pattern(
            "mix1 {date} R{rating_min}-{rating_max} M{moves}.html",
            self.values,
            "output.filename",
        )
        self.assertEqual(filename, "mix1 26-01-09 R900-1200 M2-4.html")

    def test_individual_date_parts_have_leading_zeros(self) -> None:
        filename = format_pattern(
            "{Y}{M}{D} {name} {theme_numbers} {moves_min}-{moves_max}.html",
            self.values,
            "output.filename",
        )
        self.assertEqual(filename, "260109 Basic 123 2-4.html")

    def test_all_mix_configs_put_date_after_mix_name(self) -> None:
        config_dir = Path(__file__).resolve().parents[1] / "configs"
        patterns = {
            "basic.toml": "mix1 {date} R{rating_min}-{rating_max} M{moves}.html",
            "deflection-attraction.toml": "mix2 {date} R{rating_min}-{rating_max} M{moves}.html",
            "mix3.toml": "mix3 {date} R{rating_min}-{rating_max} M{moves}.html",
        }
        for filename, expected in patterns.items():
            with self.subTest(config=filename):
                with (config_dir / filename).open("rb") as file:
                    mix_config = tomllib.load(file)
                self.assertEqual(mix_config["output"]["filename"], expected)

    def test_browser_title_uses_page_title_not_visible_heading(self) -> None:
        chess_dir = Path(__file__).resolve().parents[1]
        template_path = chess_dir / "templates" / "mix.html"

        for config_name in (
            "basic.toml",
            "deflection-attraction.toml",
            "mix3.toml",
        ):
            with self.subTest(config=config_name):
                with (chess_dir / "configs" / config_name).open("rb") as file:
                    config = tomllib.load(file)
                moves_min = config["moves"]["min"]
                moves_max = config["moves"]["max"]
                moves = (
                    str(moves_min)
                    if moves_min == moves_max
                    else f"{moves_min}-{moves_max}"
                )
                values = build_pattern_values(
                    config, "123", moves, date(2026, 11, 1)
                )
                page_title = format_pattern(
                    config["page"]["title"], values, "page.title"
                )
                heading = config["page"]["heading"]
                rendered = render_template(
                    template_path,
                    {
                        "PAGE_TITLE": escape(page_title),
                        "HEADING": escape(heading),
                    },
                )

                self.assertIn(f"<title>{escape(page_title)}</title>", rendered)
                self.assertIn(f"<h1>{escape(heading)}</h1>", rendered)
                self.assertNotIn(
                    escape(heading),
                    rendered.split("<title>", 1)[1].split("</title>", 1)[0],
                )

    def test_print_statistics_accepts_output_outside_chess_directory(self) -> None:
        # Generated files live in site/mixes, a sibling of the chess directory.
        root = Path(__file__).resolve().parents[2]
        output_file = root / "site" / "mixes" / "test.html"
        config = {
            "name": "Test mix",
            "rating": {"min": 900, "max": 1200},
            "moves": {"min": 2, "max": 2},
            "puzzles_per_click": 10,
        }
        buffer = StringIO()
        with redirect_stdout(buffer):
            print_statistics(
                config=config,
                themes=[{"id": "fork", "name": "Fork", "weight": 1}],
                move_counts=[2],
                puzzles={"fork": {2: ["abcd"]}},
                move_weights={2: 1},
                output_path=output_file,
            )
        self.assertIn("Создан файл: site", buffer.getvalue())
        self.assertIn("mixes", buffer.getvalue())
        self.assertIn("test.html", buffer.getvalue())

    def test_unknown_placeholder_still_fails(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Unknown placeholder"):
            format_pattern("{unknown}.html", self.values, "output.filename")


if __name__ == "__main__":
    unittest.main()
