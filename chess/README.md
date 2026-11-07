# Chess puzzle mixes

One Python generator is shared by all puzzle mixes.

## Quick start

From the repository root in Windows Command Prompt:

```bat
chess-generate 0
chess-generate 1
chess-generate 2
chess-generate 3
chess-generate 4
```

Mix numbers:

- `0` -> all configs in `chess/configs/`, sorted by filename; stop if any generator fails
- `1` -> `1-basic` (Основная солянка)
- `2` -> `2-deflection-attraction` (Завлечение и отвлечение)
- `3` -> `3-interference` (Перекрытие / `interference`; rating 900–1200; 2–4 moves)
- `4` -> `4-clearance` (Освобождение линии или поля / `clearance`; rating 900–1200; 2–4 moves)

If the number is missing or unknown, the batch file prints the available mixes.

## Direct generator usage

```text
python chess/generate_mix.py 1-basic
python chess/generate_mix.py 2-deflection-attraction
python chess/generate_mix.py 3-interference
python chess/generate_mix.py 4-clearance
```

## Per-theme task limit and quality selection

Every mix config includes `max_puzzles_per_theme = 5000`. It limits the **number of IDs for each theme**, not the total across all themes. Use a different non-negative integer to change the limit or `0` for unlimited tasks; omitted keys also default to 5000. Existing `popularity_min`, `min_plays`, the rating range and move-length filters still apply before ranking.

Eligible tasks are ranked by `Popularity` (higher first), `RatingDeviation` (lower first), then `NbPlays` (higher first), with the puzzle ID as a deterministic tie-breaker. A single streaming pass keeps no more than the configured limit per theme **and move count** while counting all eligible rows. Then the final per-theme limit is divided proportionally among active `move_weights` using integer quotas; any shortage for a move count is redistributed to other lengths. For 5000 slots and weights `2 = 20, 3 = 50, 4 = 30`, the targets are 1000/2500/1500 respectively when enough candidates exist.

The selected IDs (and only their Lichess API validation snapshots) are saved into HTML. JavaScript still picks **random, non-repeating tasks** from those IDs when you click. The terminal output reports how many eligible tasks were **found** and how many were **selected** for every theme and move count, so you can check quotas. This changes only newly generated HTML; existing published files stay unchanged until regenerated and published via PR.

Each mix is defined by a TOML file in `chess/configs/`. To add another mix, create another TOML config. Add a numeric mapping to `chess-generate.bat` if you want to launch it by number.

Generated HTML files are written to `site/mixes/` in this repository. They are publishable files: review generated pages and commit only the intended HTML files through a Pull Request. No previously generated HTML pages were migrated. The local puzzle database stays outside Git.

## Using the generated page

The visible page heading is **«Лёха & Папа — шахматная солянка»**. The browser tab title comes only from `[page].title` in the TOML config (including its placeholders); `[page].heading` controls the heading inside the page and is not prepended to the tab title. A compact header and two **collapsed-by-default** instruction sections leave the theme table visible without expanding the tips. Click a section heading to show its reminder:

- **One tab = one puzzle.** Solve the puzzle shown in each Lichess tab. Do not click Lichess's **Next puzzle** button; move to the next browser tab instead.
- **If Chrome blocks the tabs**, return to the mix page, click the blocked-pop-up icon at the right side of the address bar, allow pop-ups for this page, and press the puzzle button again.

These tips do not change the puzzle selection or automatically override Chrome's pop-up settings.

After each click, the page shows **the last selected puzzle IDs** in the same order as the tabs it tried to open. Each ID is a direct link to its Lichess puzzle. Compare the ID with the puzzle number displayed on Lichess: a mismatch means the Lichess tab is showing a different puzzle. The list is saved in browser localStorage (separately for the mix's page title), so it remains visible after reloading the same page. Even if Chrome blocks pop-ups, the selected IDs remain clickable.

The displayed 1000–1400 (or other configured) rating range is based on the **local CSV database snapshot used at generation time**. Lichess puzzle ratings may change later. For a fresher snapshot, replace the local `chess/lichess_db_puzzle.csv.zst` with the [latest Lichess puzzle database](https://database.lichess.org/#puzzles) and regenerate the HTML; no database file is committed to Git. A rating difference alone does not explain an **ID mismatch**.

The `output.filename` pattern supports placeholders such as:

- `{rating_min}`
- `{rating_max}`
- `{theme_numbers}`
- `{moves}` — `3` for an exact 3-move mix, or `1-3` for a 1–3 move range
- `{moves_min}`
- `{moves_max}`
- `{name}`
- `{date}` — current local date in `YY-MM-DD` format (for example, `26-10-27`)
- `{Y}` — last two digits of the year (for example, `26`)
- `{M}` — two-digit month
- `{D}` — two-digit day

Date values are taken once from the computer's local date when the generator runs. To use a compact date without hyphens, combine `{Y}{M}{D}` (for example, `261027`).

Example:

```toml
[output]
filename = "mix1 {date} R{rating_min}-{rating_max} M{moves}.html"
```

The default filename patterns begin with `mix1`, `mix2`, `mix3`, or `mix4`, followed by the date (for example, `mix1 26-10-27 R900-1200 M2-4.html`), so files of the same mix sort together.

The generator expects `lichess_db_puzzle.csv.zst` in the `chess` directory by default. Published HTML files are picked up by the Pages catalog automatically when merged to `main`.

See [`GENERATION_RULES.md`](GENERATION_RULES.md) for filtering, weighted themes, balanced move-count quotas, random ordering, and repetition rules. Existing generated HTML files must be regenerated to use the new selection logic.

Optional HTML selection tests (Node.js): `node --test chess/tests/mix.test.cjs`.

## Structure

```text
chess-mixes/
├── chess-generate.bat
├── chess/
│   ├── generate_mix.py
│   ├── configs/
│   │   ├── 1-basic.toml
│   │   ├── 2-deflection-attraction.toml
│   │   ├── 3-interference.toml
│   │   └── 4-clearance.toml
│   ├── GENERATION_RULES.md
│   ├── templates/
│   │   └── mix.html
│   └── tests/
├── scripts/
│   └── build_site.py
└── site/
    └── mixes/
        └── generated HTML pages for publishing
```
