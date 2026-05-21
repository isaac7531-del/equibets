"""Consolidate FEI and national-event result stores into one public data file."""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from equibets.national_events import load_national_federations
from equibets.results import EventingResult, ResultStore, consolidate_results, load_results


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEFAULT_FEI_RESULTS_FILE = DATA_DIR / "fei_results.json"
DEFAULT_NATIONAL_RESULTS_DIR = DATA_DIR / "national"
DEFAULT_CONSOLIDATED_RESULTS_FILE = DATA_DIR / "consolidated_results.json"
CONSOLIDATED_SOURCE_ID = "consolidated_public_results"


@dataclass(frozen=True)
class PublicDataSummary:
    """Coverage summary for one public-data consolidation run."""

    input_files: tuple[Path, ...]
    total_results: int
    countries: tuple[str, ...]
    levels: tuple[str, ...]
    source_ids: tuple[str, ...]
    configured_national_federations: int


def discover_result_files(
    explicit_paths: Iterable[Path | str] = (),
    *,
    include_default_fei: bool = True,
    national_results_dir: Path | str = DEFAULT_NATIONAL_RESULTS_DIR,
) -> tuple[Path, ...]:
    """Return existing result-store files to include in public consolidation."""

    candidates: list[Path] = []
    if include_default_fei:
        candidates.append(DEFAULT_FEI_RESULTS_FILE)

    national_dir = Path(national_results_dir)
    if national_dir.exists():
        candidates.extend(sorted(national_dir.glob("*.json")))

    for explicit_path in explicit_paths:
        path = Path(explicit_path)
        if path.is_dir():
            candidates.extend(sorted(path.glob("*.json")))
        else:
            candidates.append(path)

    existing = [path for path in candidates if path.exists()]
    return tuple(dict.fromkeys(existing))


def consolidate_public_results(input_files: Iterable[Path | str]) -> tuple[list[EventingResult], PublicDataSummary]:
    """Load, deduplicate, and summarize FEI plus national-event result stores."""

    paths = tuple(Path(path) for path in input_files)
    all_results: list[EventingResult] = []
    for path in paths:
        all_results.extend(load_results(path))

    consolidated = consolidate_results(all_results)
    summary = PublicDataSummary(
        input_files=paths,
        total_results=len(consolidated),
        countries=tuple(sorted({result.country for result in consolidated})),
        levels=tuple(sorted({result.level for result in consolidated})),
        source_ids=tuple(sorted({result.source_id for result in consolidated})),
        configured_national_federations=len(load_national_federations()),
    )
    return consolidated, summary


def write_consolidated_results(
    results: Sequence[EventingResult],
    output: Path | str = DEFAULT_CONSOLIDATED_RESULTS_FILE,
) -> None:
    """Write consolidated public results while preserving original source IDs."""

    ResultStore(output, source_id=CONSOLIDATED_SOURCE_ID).save(results)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Consolidate FEI and national eventing result stores")
    parser.add_argument("--input", action="append", default=[], help="Result JSON file or directory to include")
    parser.add_argument(
        "--national-dir",
        type=Path,
        default=DEFAULT_NATIONAL_RESULTS_DIR,
        help="Directory containing per-national-source JSON result stores",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_CONSOLIDATED_RESULTS_FILE,
        help="Consolidated public result JSON path",
    )
    parser.add_argument("--skip-default-fei", action="store_true", help="Do not include data/fei_results.json")
    parser.add_argument("--allow-empty", action="store_true", help="Write an empty consolidated file if no inputs exist")
    args = parser.parse_args(argv)

    input_files = discover_result_files(
        args.input,
        include_default_fei=not args.skip_default_fei,
        national_results_dir=args.national_dir,
    )
    if not input_files and not args.allow_empty:
        print("No FEI or national result stores found; use --allow-empty to write an empty file.")
        return 1

    results, summary = consolidate_public_results(input_files)
    write_consolidated_results(results, args.output)
    print(
        "Wrote "
        f"{summary.total_results} consolidated results from {len(summary.input_files)} files "
        f"to {args.output}"
    )
    print(
        "Coverage: "
        f"{len(summary.countries)} countries, {len(summary.levels)} levels, "
        f"{len(summary.source_ids)} sources, "
        f"{summary.configured_national_federations} configured national federations"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
