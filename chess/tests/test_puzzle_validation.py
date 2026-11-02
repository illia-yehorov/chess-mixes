"""Unit tests for the compact Lichess CSV validation snapshot."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from generate_mix import build_validation_record


class PuzzleValidationTests(unittest.TestCase):
    def test_snapshot_uses_game_id_and_excludes_setup_move_from_solution(self):
        row = ["abc12", "fen", "e2e4 e7e5 g1f3 b8c6", "1100", "75",
               "85", "100", "fork short",
               "https://lichess.org/Ab1Cd2Ef/black#42"]
        self.assertEqual(
            build_validation_record(row, row[2].split(), 1100),
            [1100, "Ab1Cd2Ef", "e2e4", "e7e5 g1f3 b8c6"],
        )

    def test_missing_game_url_keeps_other_validation_fields(self):
        row = ["abc12", "fen", "e2e4 e7e5", "1100", "75", "85", "100", "fork"]
        self.assertEqual(
            build_validation_record(row, row[2].split(), 1100),
            [1100, "", "e2e4", "e7e5"],
        )


if __name__ == "__main__":
    unittest.main()
