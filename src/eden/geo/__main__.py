#!/usr/bin/env python3
"""eden.geo

Geospatial processing CLI for EDEN.

This is one of several EDEN subsystem CLIs:
- eden.registry → region definition and bounds (prep_ecoregions, fetch_ecoregions)
- eden.ingest   → data ingestion (CHELSA, NLCD, etc.)
- eden.geo      → geospatial processing (this file)
- eden.features → feature engineering (TODO)
- eden.model    → ecosystem modeling (TODO)

eden.geo handles raster operations on *already-fetched* data:
- Clipping rasters to region bounds
- Computing zonal statistics per region
- QA checks on processed outputs

It does NOT handle region definition (that's eden.registry).

Design notes:
- Consumes outputs from eden.registry (regions_v0.gpkg, bounds parquet)
- Mirrors the structure of eden.ingest for consistency
- Lazy-imports geo modules to keep CLI startup fast
- All subcommands support --dry-run for safe exploration

Examples:
  # Clip rasters to AOI (TODO)
  python -m eden.geo clip-rasters --source chelsa --year 2022

  # Compute zonal statistics (TODO)
  python -m eden.geo zonal-stats --raster data/interim/rasters/... --zones ...
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Optional

# Import shared config utilities from eden.config
from eden.config import (
    load_yaml,
    aoi_from_regions_yaml,
    format_bbox,
    DEFAULT_REGIONS_YAML,
)


# -----------------------------------------------------------------------------
# CLI structure
# -----------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for eden.geo.

    Structure:
    - Global args: apply to all subcommands (--regions-yaml, --dry-run, etc.)
    - Subcommands: one per geo operation (clip-rasters, zonal-stats, etc.)

    Note: prep-ecoregions has moved to eden.registry.
    """
    ap = argparse.ArgumentParser(
        prog="eden.geo",
        description="Geospatial processing for EDEN (raster operations)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Subsystem CLIs:
  python -m eden.registry  # Region definition (prep-ecoregions)
  python -m eden.ingest    # Data ingestion
  python -m eden.geo       # Geospatial processing (this)
  python -m eden.features  # Feature engineering (TODO)
  python -m eden.model     # Ecosystem modeling (TODO)

Note: prep-ecoregions has moved to eden.registry.
        """,
    )

    # --- Global args ---
    ap.add_argument(
        "--regions-yaml",
        type=Path,
        default=DEFAULT_REGIONS_YAML,
        help=f"Path to regions YAML (default: {DEFAULT_REGIONS_YAML})",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without writing files",
    )
    ap.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files",
    )

    # --- Subcommands ---
    sub = ap.add_subparsers(dest="command", required=True)

    # --- clip-rasters ---
    # Clips fetched rasters to region bounds
    # TODO: Implement when clip_rasters.py is ready
    clip = sub.add_parser(
        "clip-rasters",
        help="Clip rasters to region bounds",
        description="""
Clip large rasters to individual region bounds.

Inputs:
- Fetched rasters (from eden.fetch)
- Region bounds (from eden.registry)

Outputs:
- Per-region clipped rasters in data/interim/rasters/
        """,
    )
    clip.add_argument("--source", help="Source to clip (e.g., chelsa, nlcd)")
    clip.add_argument("--year", type=int, help="Year to process")
    clip.add_argument("--var", help="Variable to clip (for multi-var sources like CHELSA)")

    # --- zonal-stats ---
    # Computes per-region statistics from rasters
    # TODO: Implement when zonal_stats.py is ready
    zonal = sub.add_parser(
        "zonal-stats",
        help="Compute zonal statistics per region",
        description="""
Compute summary statistics for each region from raster data.

Inputs:
- Clipped rasters (from clip-rasters)
- Region geometries (from eden.registry)

Outputs:
- geo_features.parquet with per-region statistics
        """,
    )
    zonal.add_argument("--raster", type=Path, help="Input raster path")
    zonal.add_argument("--zones", type=Path, help="Zones GeoPackage (from registry)")
    zonal.add_argument("--stats", nargs="+", default=["mean", "std", "min", "max"],
                       help="Statistics to compute (default: mean std min max)")

    # --- qa ---
    # QA checks on processed geo outputs
    # TODO: Implement when qa_geo.py is ready
    qa = sub.add_parser(
        "qa",
        help="Run QA checks on geo outputs",
    )
    qa.add_argument("--check", choices=["all", "crs", "bounds", "nodata"],
                    default="all", help="Which checks to run")

    return ap


# -----------------------------------------------------------------------------
# Command handlers
# -----------------------------------------------------------------------------

def _handle_clip_rasters(args: argparse.Namespace) -> int:
    """Handle the clip-rasters subcommand."""
    # TODO: Implement when clip_rasters.py has a callable function
    print("[not implemented] clip-rasters")
    print("Next steps:")
    print("  1. Add a clip_rasters() function to eden/geo/clip_rasters.py")
    print("  2. Wire it up here")
    return 1


def _handle_zonal_stats(args: argparse.Namespace) -> int:
    """Handle the zonal-stats subcommand."""
    # TODO: Implement when zonal_stats.py has a callable function
    print("[not implemented] zonal-stats")
    print("Next steps:")
    print("  1. Add a zonal_stats() function to eden/geo/zonal_stats.py")
    print("  2. Wire it up here")
    return 1


def _handle_qa(args: argparse.Namespace) -> int:
    """Handle the qa subcommand."""
    # TODO: Implement when qa_geo.py has a callable function
    print("[not implemented] qa")
    print("Next steps:")
    print("  1. Add QA functions to eden/geo/qa_geo.py")
    print("  2. Wire it up here")
    return 1


# -----------------------------------------------------------------------------
# Main entrypoint
# -----------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    """Main entrypoint for eden.geo CLI."""
    ap = build_parser()
    args = ap.parse_args(argv)

    handlers = {
        "clip-rasters": _handle_clip_rasters,
        "zonal-stats": _handle_zonal_stats,
        "qa": _handle_qa,
    }

    handler = handlers.get(args.command)
    if handler is None:
        raise SystemExit(f"Unknown command: {args.command}")

    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
