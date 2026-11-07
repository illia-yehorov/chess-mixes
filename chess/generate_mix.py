from __future__ import annotations

import argparse
import csv
import html
import io
import json
import re
from heapq import heappush, heapreplace
from math import floor, isfinite, log1p
import tomllib
from datetime import date
from pathlib import Path

import zstandard as zstd


BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "configs"
TEMPLATE_DIR = BASE_DIR / "templates"
OUTPUT_DIR = BASE_DIR.parent / "site" / "mixes"
DEFAULT_CONFIG_PATH = CONFIG_DIR / "0-defaults.toml"
DEFAULT_MAX_PUZZLES_PER_THEME = 1000
QUALITY_PLAYS_SATURATION = 2000
QUALITY_DEVIATION_CEILING = 200
QUALITY_WEIGHT_KEYS = {"popularity", "plays", "rating_deviation"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Lichess puzzle mix from a TOML config."
    )
    parser.add_argument(
        "config",
        help=(
            "Config name from configs/ (for example: basic) "
            "or a path to a TOML file."
        ),
    )
    return parser.parse_args()


def resolve_config_path(value: str) -> Path:
    path = Path(value)

    # Explicit paths are resolved from the caller's working directory.
    if path.is_absolute() or path.parent != Path("."):
        return path.resolve()

    # Short names are resolved from the generator's configs directory.
    name = path.name if path.suffix == ".toml" else f"{path.name}.toml"
    return CONFIG_DIR / name


def merge_config(defaults: dict, overrides: dict) -> dict:
    """Override individual fields; nested TOML tables merge recursively.

    Lists such as [[themes]] replace the complete inherited list.
    """
    merged = defaults.copy()
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_config(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(path: Path) -> dict:
    if path.resolve() == DEFAULT_CONFIG_PATH.resolve():
        raise RuntimeError(
            "0-defaults.toml contains shared settings, not a mix"
        )
    if not path.is_file():
        raise RuntimeError(f"Config file not found: {path}")
    if not DEFAULT_CONFIG_PATH.is_file():
        raise RuntimeError(f"Shared config file not found: {DEFAULT_CONFIG_PATH}")

    with DEFAULT_CONFIG_PATH.open("rb") as file:
        defaults = tomllib.load(file)
    with path.open("rb") as file:
        overrides = tomllib.load(file)

    config = merge_config(defaults, overrides)
    validate_config(config)
    return config


def validate_config(config: dict) -> None:
    required = {
        "name",
        "source",
        "template",
        "puzzles_per_click",
        "popularity_min",
        "min_plays",
        "quality_weights",
        "rating",
        "moves",
        "move_weights",
        "output",
        "page",
        "themes",
    }

    missing = required - config.keys()
    if missing:
        raise RuntimeError(
            "Missing config keys: "
            + ", ".join(sorted(missing))
        )

    weights = config["quality_weights"]
    if not isinstance(weights, dict) or set(weights) != QUALITY_WEIGHT_KEYS:
        raise RuntimeError(
            "quality_weights must define popularity, plays, rating_deviation"
        )
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
        or value < 0
        for value in weights.values()
    ) or sum(weights.values()) <= 0:
        raise RuntimeError(
            "quality_weights must be finite non-negative numbers "
            "with a positive sum"
        )

    rating_min = config["rating"]["min"]
    rating_max = config["rating"]["max"]

    if rating_max < rating_min:
        raise RuntimeError(
            "rating.max cannot be lower than rating.min"
        )

    min_moves = config["moves"]["min"]
    max_moves = config["moves"]["max"]

    if min_moves < 1:
        raise RuntimeError("moves.min must be >= 1")

    if max_moves < min_moves:
        raise RuntimeError(
            "moves.max cannot be lower than moves.min"
        )

    if config["puzzles_per_click"] < 1:
        raise RuntimeError(
            "puzzles_per_click must be >= 1"
        )

    limit = config.get("max_puzzles_per_theme", DEFAULT_MAX_PUZZLES_PER_THEME)
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
        raise RuntimeError("max_puzzles_per_theme must be an integer >= 0")

    if not config["themes"]:
        raise RuntimeError(
            "At least one [[themes]] entry is required"
        )

    theme_ids = [
        theme["id"]
        for theme in config["themes"]
    ]

    if len(theme_ids) != len(set(theme_ids)):
        raise RuntimeError("Theme ids must be unique")

    if any(
        theme.get("weight", 1) < 0
        for theme in config["themes"]
    ):
        raise RuntimeError(
            "Theme weight cannot be negative"
        )

    if all(
        theme.get("weight", 1) == 0
        for theme in config["themes"]
    ):
        raise RuntimeError("All theme weights are 0")

    move_weights = parse_move_weights(config)

    if any(weight < 0 for weight in move_weights.values()):
        raise RuntimeError(
            "Move weight cannot be negative"
        )

    if not get_active_move_counts(config, move_weights):
        raise RuntimeError(
            "No move count in the configured range has weight > 0"
        )


def parse_move_weights(config: dict) -> dict[int, float]:
    try:
        return {
            int(move_count): weight
            for move_count, weight
            in config["move_weights"].items()
        }
    except ValueError as exc:
        raise RuntimeError(
            "move_weights keys must be integer values"
        ) from exc


def get_active_move_counts(
    config: dict,
    move_weights: dict[int, float],
) -> list[int]:
    return [
        move_count
        for move_count in range(
            config["moves"]["min"],
            config["moves"]["max"] + 1,
        )
        if move_weights.get(move_count, 0) > 0
    ]


def build_validation_record(row: list[str], moves: list[str], rating: int) -> list:
    """Compact CSV snapshot used to verify a selected puzzle in the browser."""
    game_url = row[8] if len(row) > 8 else ""
    game_match = re.match(
        r"^https://lichess\.org/([A-Za-z0-9]{8})(?:[/?#]|$)",
        game_url,
    )
    game_id = game_match.group(1) if game_match else ""
    # CSV includes the opponent's setup move; the API solution excludes it.
    return [rating, game_id, moves[0], " ".join(moves[1:])]


def proportional_quotas(
    total: int,
    move_weights: dict[int, float],
) -> dict[int, int]:
    """Split an integer total by weights, using largest remainders."""
    weight_sum = sum(move_weights.values())
    if total == 0 or weight_sum <= 0:
        return {move_count: 0 for move_count in move_weights}

    shares = {
        move_count: total * weight / weight_sum
        for move_count, weight in move_weights.items()
    }
    quotas = {
        move_count: floor(share)
        for move_count, share in shares.items()
    }
    remainder = total - sum(quotas.values())
    order = sorted(
        shares,
        key=lambda move_count: (
            -(shares[move_count] - quotas[move_count]),
            move_count,
        ),
    )
    for move_count in order[:remainder]:
        quotas[move_count] += 1
    return quotas


def allocate_move_quotas(
    limit: int,
    available: dict[int, int],
    move_weights: dict[int, float],
) -> dict[int, int]:
    """Respect the weighted move split, redistributing unavailable slots."""
    if limit == 0:  # Explicitly unlimited.
        return available.copy()

    quotas = {move_count: 0 for move_count in available}
    remaining = min(limit, sum(available.values()))

    while remaining:
        eligible = {
            move_count: move_weights[move_count]
            for move_count, capacity in available.items()
            if capacity > quotas[move_count] and move_weights[move_count] > 0
        }
        if not eligible:
            break

        requested = proportional_quotas(remaining, eligible)
        added = 0
        for move_count, count in requested.items():
            count = min(count, available[move_count] - quotas[move_count])
            quotas[move_count] += count
            added += count
        if not added:
            break
        remaining -= added

    return quotas


def quality_score(
    popularity: int,
    rating_deviation: int,
    nb_plays: int,
    weights: dict[str, float],
) -> float:
    """0–100 statistical quality heuristic, not chess-engine validation."""
    popularity_part = min(1.0, max(0.0, popularity / 100))
    plays_part = min(
        1.0, log1p(max(0, nb_plays)) / log1p(QUALITY_PLAYS_SATURATION)
    )
    deviation_part = max(
        0.0, 1.0 - rating_deviation / QUALITY_DEVIATION_CEILING
    )
    total_weight = sum(weights.values())
    return 100.0 * (
        weights["popularity"] * popularity_part
        + weights["plays"] * plays_part
        + weights["rating_deviation"] * deviation_part
    ) / total_weight


def read_puzzles(
    source_path: Path,
    config: dict,
    theme_ids: list[str],
    active_move_counts: list[int],
) -> tuple[
    dict[str, dict[int, list[str]]],
    dict[str, list],
    dict[str, dict[int, int]],
    dict[str, float],
]:
    """Read the CSV once, keeping best-quality candidates in bounded heaps."""
    if not source_path.is_file():
        raise RuntimeError(
            f"Lichess puzzle database not found: {source_path}"
        )

    limit = config.get("max_puzzles_per_theme", DEFAULT_MAX_PUZZLES_PER_THEME)
    move_weights = parse_move_weights(config)
    quality_weights = config["quality_weights"]
    candidates = {
        theme_id: {move_count: [] for move_count in active_move_counts}
        for theme_id in theme_ids
    }
    found_counts = {
        theme_id: {move_count: 0 for move_count in active_move_counts}
        for theme_id in theme_ids
    }

    with source_path.open("rb") as compressed:
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(compressed) as reader:
            text_stream = io.TextIOWrapper(reader, encoding="utf-8")
            for row in csv.reader(text_stream):
                if len(row) < 8:
                    continue

                moves = row[2].split()
                if len(moves) % 2 != 0:
                    continue

                solver_moves = len(moves) // 2
                if solver_moves not in active_move_counts:
                    continue

                try:
                    rating = int(row[3])
                    rating_deviation = int(row[4])
                    popularity = int(row[5])
                    nb_plays = int(row[6])
                except ValueError:
                    continue

                if rating_deviation < 0:
                    continue
                if not (
                    config["rating"]["min"]
                    <= rating
                    <= config["rating"]["max"]
                ):
                    continue
                if popularity < config["popularity_min"]:
                    continue
                if nb_plays < config["min_plays"]:
                    continue

                puzzle_id = row[0]
                puzzle_themes = set(row[7].split())
                # Combined score is primary; other fields break exact ties.
                # Puzzle ID makes selection independent of CSV row order.
                score = quality_score(
                    popularity, rating_deviation, nb_plays, quality_weights
                )
                rank = (
                    score, popularity, -rating_deviation, nb_plays, puzzle_id
                )
                snapshot = None

                for theme_id in theme_ids:
                    if theme_id not in puzzle_themes:
                        continue

                    found_counts[theme_id][solver_moves] += 1
                    heap = candidates[theme_id][solver_moves]
                    if limit > 0 and len(heap) >= limit and rank <= heap[0][0]:
                        continue

                    if snapshot is None:
                        snapshot = build_validation_record(row, moves, rating)
                    entry = (rank, snapshot)
                    if limit == 0:
                        heap.append(entry)
                    elif len(heap) < limit:
                        heappush(heap, entry)
                    else:
                        heapreplace(heap, entry)

    puzzles = {
        theme_id: {move_count: [] for move_count in active_move_counts}
        for theme_id in theme_ids
    }
    validation_data: dict[str, list] = {}
    selected_scores: dict[str, float] = {}

    for theme_id in theme_ids:
        available = {
            move_count: len(candidates[theme_id][move_count])
            for move_count in active_move_counts
        }
        quotas = allocate_move_quotas(limit, available, move_weights)
        for move_count in active_move_counts:
            # Heap entries are ranked, but browser selection stays random.
            best = sorted(
                candidates[theme_id][move_count], reverse=True
            )[:quotas[move_count]]
            for rank, snapshot in best:
                puzzle_id = rank[4]
                puzzles[theme_id][move_count].append(puzzle_id)
                validation_data[puzzle_id] = snapshot
                selected_scores[puzzle_id] = rank[0]

    return puzzles, validation_data, found_counts, selected_scores


def filter_available(
    config: dict,
    puzzles: dict[str, dict[int, list[str]]],
    active_move_counts: list[int],
) -> tuple[list[dict], list[int]]:
    themes = [
        theme
        for theme in config["themes"]
        if any(
            puzzles[theme["id"]][move_count]
            for move_count in active_move_counts
        )
    ]

    if not themes:
        raise RuntimeError(
            "No puzzles found for the configured filters"
        )

    if all(theme.get("weight", 1) == 0 for theme in themes):
        raise RuntimeError(
            "All themes with available puzzles have weight = 0"
        )

    move_counts = [
        move_count
        for move_count in active_move_counts
        if any(
            puzzles[theme["id"]][move_count]
            for theme in themes
        )
    ]

    if not move_counts:
        raise RuntimeError(
            "No puzzles found for the configured move counts"
        )

    return themes, move_counts


def moves_text(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return f"{count} ход"

    if (
        count % 10 in (2, 3, 4)
        and count % 100 not in (12, 13, 14)
    ):
        return f"{count} хода"

    return f"{count} ходов"


def moves_range_text(config: dict) -> str:
    min_moves = config["moves"]["min"]
    max_moves = config["moves"]["max"]

    if min_moves == max_moves:
        return f"ровно {moves_text(min_moves)}"

    return f"{min_moves}–{max_moves} ходов"


def build_pattern_values(
    config: dict,
    theme_numbers: str,
    moves_value: str,
    current_date: date | None = None,
) -> dict[str, object]:
    current_date = current_date or date.today()
    year = current_date.strftime("%y")

    return {
        "name": config["name"],
        "rating_min": config["rating"]["min"],
        "rating_max": config["rating"]["max"],
        "theme_numbers": theme_numbers,
        "moves": moves_value,
        "moves_min": config["moves"]["min"],
        "moves_max": config["moves"]["max"],
        "date": current_date.strftime("%y-%m-%d"),
        "Y": year,
        "M": f"{current_date.month:02d}",
        "D": f"{current_date.day:02d}",
    }


def format_pattern(
    pattern: str,
    values: dict[str, object],
    field_name: str,
) -> str:
    try:
        return pattern.format(**values)
    except KeyError as exc:
        raise RuntimeError(
            f"Unknown placeholder {{{exc.args[0]}}} "
            f"in {field_name}"
        ) from exc


def render_template(
    template_path: Path,
    replacements: dict[str, str],
) -> str:
    if not template_path.is_file():
        raise RuntimeError(
            f"HTML template not found: {template_path}"
        )

    result = template_path.read_text(encoding="utf-8")

    for key, value in replacements.items():
        result = result.replace(
            "{{" + key + "}}",
            value,
        )

    return result


def print_statistics(
    config: dict,
    themes: list[dict],
    move_counts: list[int],
    puzzles: dict[str, dict[int, list[str]]],
    move_weights: dict[int, float],
    output_path: Path,
    found_counts: dict[str, dict[int, int]] | None = None,
    selected_scores: dict[str, float] | None = None,
) -> None:
    print(f"Набор: {config['name']}")
    print()
    print(
        f"Найдено и отобрано задач (рейтинг "
        f"{config['rating']['min']}–{config['rating']['max']}):"
    )

    for theme in themes:
        theme_id = theme["id"]
        selected_by_move = puzzles[theme_id]
        found_by_move = (
            found_counts[theme_id] if found_counts is not None
            else {move: len(selected_by_move[move]) for move in move_counts}
        )
        found_total = sum(found_by_move[move] for move in move_counts)
        selected_total = sum(len(selected_by_move[move]) for move in move_counts)
        print(
            f"{theme['name']:30} ({theme_id:20}): "
            f"найдено {found_total}, отобрано {selected_total}; "
            f"вес темы = {theme.get('weight', 1)}"
        )
        for move_count in move_counts:
            print(
                f"    {move_count} ход.: "
                f"найдено {found_by_move[move_count]}, "
                f"отобрано {len(selected_by_move[move_count])}"
            )

    limit = config.get("max_puzzles_per_theme", DEFAULT_MAX_PUZZLES_PER_THEME)
    print()
    print(
        f"Лимит на тему: {limit if limit else 'без ограничения'}"
    )
    unique_ids = {
        puzzle_id
        for theme in themes
        if theme.get("weight", 1) > 0
        for ids in puzzles[theme["id"]].values()
        for puzzle_id in ids
    }
    print(f"Уникальных задач: {len(unique_ids)}")
    if selected_scores is not None and unique_ids:
        scores = [selected_scores[puzzle_id] for puzzle_id in unique_ids]
        print(
            "Quality Score (0–100, уникальные задачи): "
            f"min {min(scores):.2f}, "
            f"среднее {sum(scores) / len(scores):.2f}, "
            f"max {max(scores):.2f}"
        )
    print(
        f"Создан файл: "
        f"{output_path.relative_to(BASE_DIR.parent)}"
    )
    print()
    print(
        f"Рейтинг: "
        f"{config['rating']['min']}–{config['rating']['max']}"
    )
    print(
        f"Количество ходов решающего: "
        f"{moves_range_text(config)}"
    )
    print(
        f"Задач за одно нажатие: "
        f"{config['puzzles_per_click']}"
    )
    print()
    print("Активные темы:")

    for theme in themes:
        if theme.get("weight", 1) > 0 and any(
            puzzles[theme["id"]][move] for move in move_counts
        ):
            print(
                f" - {theme['name']} "
                f"(вес: {theme.get('weight', 1)})"
            )

    print()
    print("Количество ходов:")
    for move_count in move_counts:
        print(
            f" - {moves_text(move_count)} "
            f"(вес: {move_weights[move_count]})"
        )


def main() -> None:
    args = parse_args()
    config_path = resolve_config_path(args.config)
    config = load_config(config_path)

    move_weights = parse_move_weights(config)
    active_move_counts = get_active_move_counts(
        config,
        move_weights,
    )

    theme_ids = [
        theme["id"]
        for theme in config["themes"]
    ]

    source_path = (
        BASE_DIR / config["source"]
    ).resolve()

    template_path = (
        TEMPLATE_DIR / config["template"]
    ).resolve()

    puzzles, validation_data, found_counts, selected_scores = read_puzzles(
        source_path,
        config,
        theme_ids,
        active_move_counts,
    )

    available_themes, available_move_counts = (
        filter_available(
            config,
            puzzles,
            active_move_counts,
        )
    )

    theme_numbers = "".join(
        str(index)
        for index, _theme
        in enumerate(
            config["themes"],
            start=1,
        )
    )

    moves_value = (
        str(config["moves"]["min"])
        if config["moves"]["min"] == config["moves"]["max"]
        else (
            f"{config['moves']['min']}"
            f"-{config['moves']['max']}"
        )
    )

    pattern_values = build_pattern_values(
        config,
        theme_numbers,
        moves_value,
    )

    output_filename = format_pattern(
        config["output"]["filename"],
        pattern_values,
        "output.filename",
    )

    output_filename_path = Path(output_filename)

    if (
        output_filename_path.is_absolute()
        or len(output_filename_path.parts) != 1
    ):
        raise RuntimeError(
            "output.filename must be a file name, not a path"
        )

    page_title = format_pattern(
        config["page"]["title"],
        pattern_values,
        "page.title",
    )

    available_ids = {
        theme["id"]
        for theme in available_themes
    }

    app_data = {
        "puzzles": puzzles,
        "validationData": validation_data,
        "ratingMin": config["rating"]["min"],
        "ratingMax": config["rating"]["max"],
        "themes": [
            {
                "id": theme["id"],
                "number": index,
                "name": theme["name"],
                "weight": theme.get("weight", 1),
            }
            for index, theme
            in enumerate(
                config["themes"],
                start=1,
            )
            if theme["id"] in available_ids
        ],
        "themeWeights": {
            theme["id"]: theme.get("weight", 1)
            for theme in available_themes
        },
        "moveWeights": {
            move_count: move_weights[move_count]
            for move_count in available_move_counts
        },
        "puzzlesPerClick": config["puzzles_per_click"],
        "storageKey": f"usedPuzzles:{config_path.stem}",
    }

    rendered_html = render_template(
        template_path,
        {
            "PAGE_TITLE": html.escape(page_title),
            "HEADING": html.escape(
                config["page"]["heading"]
            ),
            "RATING_MIN": str(
                config["rating"]["min"]
            ),
            "RATING_MAX": str(
                config["rating"]["max"]
            ),
            "MOVES_DESCRIPTION": html.escape(
                moves_range_text(config)
            ),
            "PUZZLES_PER_CLICK": str(
                config["puzzles_per_click"]
            ),
            "MAX_PUZZLES_PER_THEME": (
                str(config.get("max_puzzles_per_theme", DEFAULT_MAX_PUZZLES_PER_THEME))
                if config.get("max_puzzles_per_theme", DEFAULT_MAX_PUZZLES_PER_THEME)
                else "без ограничения"
            ),
            "APP_DATA_JSON": json.dumps(
                app_data,
                ensure_ascii=False,
            ),
        },
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = OUTPUT_DIR / output_filename
    output_path.write_text(
        rendered_html,
        encoding="utf-8",
    )

    print_statistics(
        config,
        config["themes"],
        active_move_counts,
        puzzles,
        move_weights,
        output_path,
        found_counts,
        selected_scores,
    )


if __name__ == "__main__":
    main()
