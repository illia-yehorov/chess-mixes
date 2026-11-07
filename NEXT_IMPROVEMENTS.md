# NEXT IMPROVEMENTS / Что улучшить дальше

## 1. Balanced puzzle difficulty — next priority

**Current issue:** `rating.min` and `rating.max` only filter which puzzles are eligible. The generator picks the best Quality Score within theme and solution-length quotas, without controlling the distribution of ratings. If nearly all highest-quality puzzles are near the upper rating bound, the training set becomes too hard.

**Proposed improvement:**
- Break the selected rating interval into configurable rating buckets (for example, 1000–1099, 1100–1199, 1200–1299, 1300–1400).
- Distribute slots across rating buckets using configurable weights, e.g. equal weights or a desired easy/medium/hard distribution.
- Apply these quotas **inside each theme and solution-length group**, so existing theme and move weights still work.
- If a rare theme lacks puzzles in a rating bucket, redistribute that quota among available buckets. **Never relax the Popularity/NbPlays safety floors** to fill a bucket.
- Report a rating histogram and actual vs desired distribution in console logs; add tests for scarce buckets, overlaps, and deterministic results.

**Before implementing:** use the local Lichess CSV to inspect actual rating histograms. Equal distribution should be an option, not an assumption.

## 2. Stockfish audit of implausible opponent replies — optional

Quality Score does not check whether the opponent's move in the published solution is a strong or realistic defense. Consider optional offline Stockfish analysis on the final candidates, flagging large differences from best defenses for review. Avoid naive centipawn thresholds in already won/lost or forced-mate positions.

## 3. Manually exclude poor puzzles — optional

Allow a small configurable list of puzzle IDs excluded during generation after review. Keep per-browser feedback separate from committed exclusions.

These ideas are **not implemented** in the current PR.
