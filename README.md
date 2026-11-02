# Chess Mixes

Static Lichess puzzle mixes generated from TOML configurations and published with GitHub Pages.

## Generate a mix on Windows

1. Install Python 3.11+ and dependencies: `python -m pip install -r requirements.txt`.
2. Download the [Lichess puzzle database](https://database.lichess.org/#puzzles) into `chess/lichess_db_puzzle.csv.zst` (local only; do not commit it).
3. From the repository root, run one of:

```bat
chess-generate 1
chess-generate 2
chess-generate 3
```

The same Python generator can run without the batch file:

```sh
python chess/generate_mix.py basic
python chess/generate_mix.py deflection-attraction
python chess/generate_mix.py mix3
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
