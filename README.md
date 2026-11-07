# Chess Mixes

Static Lichess puzzle mixes generated from TOML configurations and published with GitHub Pages.

## Generate a mix on Windows

1. Install Python 3.11+ and dependencies: `python -m pip install -r requirements.txt`.
2. Download the [Lichess puzzle database](https://database.lichess.org/#puzzles) into `chess/lichess_db_puzzle.csv.zst` (local only; do not commit it).
3. From the repository root, run one of:

```bat
chess-generate
chess-generate 1
chess-generate 2
chess-generate 3
chess-generate 4
```

Run `chess-generate` **without arguments** to regenerate all numbered mixes in filename order. `0` is not a batch argument. The shared `0-defaults.toml` is skipped, and the batch stops on the first failed generation.

All mixes inherit common settings from `chess/configs/0-defaults.toml`. The default per-theme limit is `max_puzzles_per_theme = 1000` (0 disables the limit), so weights 20/50/30 target 200/500/300 tasks for 2/3/4 moves. The generator filters by rating, popularity, number of attempts and move length, then ranks candidates by a combined **Quality Score (0–100)**: 80% Popularity, 15% attempt count (log-scaled, saturated at 2,000), and 5% low RatingDeviation (best at 0, no bonus from 200 onwards). Weights live in `[quality_weights]` in shared TOML and are automatically normalized. Default safety floors are `popularity_min = 85` and `min_plays = 200`, even when a theme cannot fill all 1,000 slots. Quality Score is a heuristic, not chess-engine analysis. Missing tasks in one length redistribute their slots to the others. The HTML still picks randomly from selected IDs, and logs show found/selected counts for every theme and move length.

For global changes, edit `0-defaults.toml`; a numbered mix can override individual values, including specific nested values such as `[rating].min` or `[move_weights]."2"`. Common `source`, `template`, `puzzles_per_click`, `popularity_min`, `min_plays`, `quality_weights`, ratings, moves and page heading live in the shared config. Mix-specific names, themes, output filenames and tab titles stay in numbered configs. The shared file is **not** a standalone mix. For examples and merge rules, see [chess/README.md](chess/README.md) and [generation rules](chess/GENERATION_RULES.md).

The same Python generator can run without the batch file:

```sh
python chess/generate_mix.py 1-basic
python chess/generate_mix.py 2-deflection-attraction
python chess/generate_mix.py 3-interference
python chess/generate_mix.py 4-clearance
```

Generated HTML files appear in `site/mixes/`. The generator keeps theme/move quotas, recent IDs, and browser localStorage history; the candidate ranking and default safety floors change.

## Publish

Only the newly generated HTML files you explicitly commit to `site/mixes/` are published. The old generated pages from `personal-lab` are **not** migrated.

1. Review the generated HTML. Remove old published variants if they should no longer appear in the catalog.
2. Create a feature branch and a Pull Request for the intended `site/mixes/*.html` files (never commit directly to `main`).
3. After the PR is merged, the Pages workflow builds an automatic catalog of committed HTML files and deploys the `site/` contents.

One-time GitHub setting: **Settings → Pages → Build and deployment → Source → GitHub Actions**. The site URL will be **https://illia-yehorov.github.io/chess-mixes/** after the first successful deployment. No Lichess CSV download is needed in the deployment workflow.

## Run tests and preview the site

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s chess/tests -p "test_*.py" -v
node --test chess/tests/mix.test.cjs
python scripts/build_site.py
```

Serve the `_site/` folder with any local HTTP server, for example `python -m http.server 8000 --directory _site`, then open http://localhost:8000/.

The initial catalog is intentionally empty until new HTML pages are generated and committed. It does not pretend that unverified pages are current.

## Layout

```text
chess-mixes/
├── .github/workflows/
│   ├── ci.yml              # Generator and HTML selection tests
│   └── pages.yml           # Build and deploy static site
├── chess/
│   ├── configs/            # 0-defaults.toml plus numbered TOML mixes
│   ├── templates/          # Self-contained HTML template
│   ├── tests/              # Python and JavaScript regression tests
│   ├── generate_mix.py
│   └── GENERATION_RULES.md
├── scripts/
│   └── build_site.py       # Build the catalog from published HTML
├── site/
│   ├── index.html          # Catalog template
│   ├── mixes/              # New published HTML (empty at migration)
│   └── data/               # Reserved for future validation output
├── chess-generate.bat
└── requirements.txt
```

Selected puzzles are checked against the current Lichess API in the browser after each click. This integrity check does not evaluate whether the opponent's defensive moves are realistic.

For detailed generation rules, see [chess/GENERATION_RULES.md](chess/GENERATION_RULES.md) and [chess/README.md](chess/README.md). For the next proposed improvement (balanced difficulty), see [NEXT_IMPROVEMENTS.md](NEXT_IMPROVEMENTS.md).
