"""Regression tests for the static GitHub Pages catalog."""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from build_site import render_cards


class SiteBuilderTests(unittest.TestCase):
    def test_empty_catalog_has_a_clear_message(self):
        with TemporaryDirectory() as tmp:
            result = render_cards(Path(tmp))
        self.assertIn("Пока нет опубликованных солянок", result)
        self.assertNotIn("<li ", result)

    def test_catalog_uses_title_and_encodes_filename(self):
        with TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "mix1 26-11-02 R1000-1400.html").write_text(
                "<!doctype html><html><head><title>My &amp; Mix</title></head>"
                "<body>tasks</body></html>",
                encoding="utf-8",
            )
            result = render_cards(directory)
        self.assertIn("My &amp; Mix", result)
        self.assertIn("mixes/mix1%2026-11-02%20R1000-1400.html", result)
        self.assertIn("mix1 26-11-02 R1000-1400.html", result)
        self.assertEqual(result.count('class="mix-card"'), 1)


if __name__ == "__main__":
    unittest.main()
