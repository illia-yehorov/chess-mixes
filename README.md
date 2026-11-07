# Chess Mixes

Static Lichess puzzle mixes generated from TOML configurations and published with GitHub Pages.

## Generate a mix on Windows

1. Install Python 3.11+ and dependencies: `python -m pip install -r requirements.txt`.
2. Download the [Lichess puzzle database](https://database.lichess.org/#puzzles) into `chess/lichess_db_puzzle.csv.zst` (local only; do not commit it).
3. From the repository root, run one of:

```bat
chess-generate 0
chess-generate 1
chess-generate 2
chess-generate 3
chess-generate 4
```

Run `chess-generate 0` to regenerate every `chess/configs/*.toml` mix in filename order. The batch stops on the first failed generation.

Each TOML config sets `max_puzzles_per_theme = 5000` (0 means unlimited). After the existing rating, popularity, minimum plays and move-length filters, the generator keeps the best candidates per theme: higher `Popularity`, then lower `RatingDeviation`, then higher `NbPlays`. Its 5000 slots are split by active `move_weights` (for example, weights 20/50/30 yield 1000/2500/1500 tasks for 2/3/4 moves). Missing tasks in one length redistribute their slots to the others. The HTML still chooses randomly from the selected set. Generation logs show found and selected counts per theme and move length. The API validation snapshot contains only the final selected IDs. See [generation rules](chess/GENERATION_RULES.md) for details.

The same Python generator can run without the batch file:

```sh
python chess/generate_mix.py 1-basic
python chess/generate_mix.py 2-deflection-attraction
python chess/generate_mix.py 3-interference
python chess/generate_mix.py 4-clearance
```

Generated HTML files appear in `site/mixes/`. The generator retains the existing puzzle filters, theme and move weights, selection logic, recent IDs, and browser localStorage history.

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
│   ├── configs/            # TOML mix definitions
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

Future puzzle integrity verification will live in `scripts/` and separate `.github/workflows/` definitions. It can publish `status.json` to Pages without regenerating mixes. Verification is **not** implemented in this migration.

For detailed generation rules, see [chess/GENERATION_RULES.md](chess/GENERATION_RULES.md) and [chess/README.md](chess/README.md).
