"""Build the static Pages directory and a catalog from committed mix HTML files."""

from __future__ import annotations

import argparse
import html
import re
import shutil
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
DEFAULT_OUTPUT = ROOT / "_site"
PLACEHOLDER = "<!-- MIX_CARDS -->"
TITLE_PATTERN = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def page_title(path: Path) -> str:
    # The HTML header is at the beginning; do not load multi-megabyte puzzles.
    with path.open("r", encoding="utf-8") as page:
        head = page.read(32768)
    match = TITLE_PATTERN.search(head)
    return html.unescape(match.group(1).strip()) if match else path.stem


def render_cards(mix_directory: Path) -> str:
    pages = sorted(mix_directory.glob("*.html"), key=lambda path: path.name, reverse=True)
    if not pages:
        return '<p class="empty">Пока нет опубликованных солянок. Сгенерируй первую и добавь её через Pull Request.</p>'
    cards = []
    for page in pages:
        href = "mixes/" + quote(page.name, safe="")
        title = html.escape(page_title(page))
        filename = html.escape(page.name)
        cards.append(
            f'<li class="mix-card"><a href="{href}">{title}</a>'
            f'<span class="filename">{filename}</span></li>'
        )
    return '<ul class="mix-list">\n' + '\n'.join(cards) + '\n</ul>'


def build(output: Path) -> None:
    output = output.resolve()
    source = SITE.resolve()
    if output == source or source in output.parents:
        raise ValueError("Build output cannot be inside the source site directory")
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(SITE, output)

    index = output / "index.html"
    template = index.read_text(encoding="utf-8")
    if template.count(PLACEHOLDER) != 1:
        raise RuntimeError("The catalog template must contain exactly one MIX_CARDS placeholder")
    index.write_text(
        template.replace(PLACEHOLDER, render_cards(output / "mixes")),
        encoding="utf-8",
    )
    print(f"Built GitHub Pages catalog with {len(list((output / 'mixes').glob('*.html')))} mix HTML page(s) at {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build GitHub Pages content")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build(args.output)


if __name__ == "__main__":
    main()
