#!/usr/bin/env python3
"""eden.geo

Geospatial processing CLI for EDEN.

This is one of several EDEN subsystem CLIs:
- eden.fetch  → data ingestion (CHELSA, NLCD, etc.)
- eden.geo    → geospatial processing (this file)
- eden.features → feature engineering (TODO)
- eden.model  → ecosystem modeling (TODO)

Each subsystem owns its domain and can be invoked independently.
This keeps the codebase modular and avoids a monolithic CLI.

Design notes:
- Mirrors the structure of eden.fetch for consistency
- Uses shared config utilities from eden.config
- Lazy-imports geo modules to keep CLI startup fast
- All subcommands support --dry-run for safe exploration

Examples:
  # Prepare ecoregions from EPA shapefile
  python -m eden.geo prep-ecoregions \
    --ecoregions-shp data/raw/boundaries/epa_ecoregions/us_eco_l3/us_eco_l3.shp \
    --out-gpkg data/interim/vectors/ecoregions_selected.gpkg

  # Clip rasters to AOI (TODO)
  python -m eden.geo clip-rasters --source chelsa --year 2022

  # Compute zonal statistics (TODO)
  python -m eden.geo zonal-stats --raster data/interim/rasters/... --zones ...
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

# Import shared config utilities
# These are the same helpers used by eden.fetch, centralized in eden.config
from eden.config import (
    load_yaml,
    load_regions_yaml,
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
    - Subcommands: one per geo operation (prep-ecoregions, clip-rasters, etc.)

    This mirrors eden.fetch's structure for consistency across subsystems.
    """
    ap = argparse.ArgumentParser(
        prog="eden.geo",
        description="Geospatial processing for EDEN",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Subsystem CLIs:
  python -m eden.fetch   # Data ingestion
  python -m eden.geo     # Geospatial processing (this)
  python -m eden.features  # Feature engineering (TODO)
  python -m eden.model   # Ecosystem modeling (TODO)
        """,
    )

    # --- Global args ---
    # These are available for all subcommands
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
    # Note: --overwrite not yet used in geo, but added for consistency
    ap.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files",
    )

    # --- Subcommands ---
    sub = ap.add_subparsers(dest="command", required=True)

    # --- prep-ecoregions ---
    # Filters EPA shapefile to selected regions, outputs clean GeoPackage
    prep = sub.add_parser(
        "prep-ecoregions",
        help="Filter EPA ecoregions shapefile to selected regions",
        description="""
Process an EPA Level III ecoregions shapefile into a clean, filtered GeoPackage.

This command:
1. Reads region definitions from regions YAML
2. Filters the shapefile to only requested regions (by code)
3. Normalizes codes and fixes invalid geometries
4. Computes areas and reprojects to target CRS
5. Writes output GeoPackage

The regions YAML (--regions-yaml) defines which ecoregions to extract.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    prep.add_argument(
        "--ecoregions-shp",
        required=True,
        type=Path,
        help="Path to EPA Level III (CONUS) shapefile",
    )
    prep.add_argument(
        "--out-gpkg",
        required=True,
        type=Path,
        help="Output GeoPackage path",
    )
    prep.add_argument(
        "--layer",
        default="ecoregions_selected",
        help="Layer name in output GeoPackage (default: ecoregions_selected)",
    )
    prep.add_argument(
        "--scheme",
        default="EPA_US",
        help="Region scheme to filter (default: EPA_US)",
    )
    prep.add_argument(
        "--level",
        type=int,
        default=3,
        help="Region level to filter (default: 3 for Level III)",
    )
    prep.add_argument(
        "--code-field",
        default=None,
        help="Shapefile column containing the code (auto-detected if not specified)",
    )
    prep.add_argument(
        "--target-crs",
        default="EPSG:4326",
        help="Output CRS (default: EPSG:4326 / WGS84)",
    )
    prep.add_argument(
        "--area-crs",
        default="EPSG:5070",
        help="CRS for area calculations (default: EPSG:5070 / CONUS Albers)",
    )
    prep.add_argument(
        "--dissolve",
        action="store_true",
        help="Dissolve multipart features into one row per uid",
    )
    prep.add_argument(
        "--qa-csv",
        type=Path,
        default=None,
        help="Optional path to write QA summary CSV",
    )

    # --- clip-rasters (placeholder) ---
    # TODO: Implement when clip_rasters.py is ready
    clip = sub.add_parser(
        "clip-rasters",
        help="Clip rasters to AOI bounds (not yet implemented)",
    )
    clip.add_argument("--source", help="Source to clip (e.g., chelsa, nlcd)")
    clip.add_argument("--year", type=int, help="Year to process")

    # --- zonal-stats (placeholder) ---
    # TODO: Implement when zonal_stats.py is ready
    zonal = sub.add_parser(
        "zonal-stats",
        help="Compute zonal statistics (not yet implemented)",
    )
    zonal.add_argument("--raster", type=Path, help="Input raster")
    zonal.add_argument("--zones", type=Path, help="Zones GeoPackage")

    return ap


# -----------------------------------------------------------------------------
# Command handlers
# -----------------------------------------------------------------------------
# Each subcommand gets a handler function that:
# 1. Validates inputs
# 2. Lazy-imports the implementation module
# 3. Calls the core function with parsed args

def _handle_prep_ecoregions(args: argparse.Namespace) -> int:
    """Handle the prep-ecoregions subcommand.

    Loads regions from YAML, then calls the prep_ecoregions() function
    from geo.prep_ecoregions module.
    """
    # Validate regions YAML exists
    if not args.regions_yaml.exists():
        raise SystemExit(f"Regions YAML not found: {args.regions_yaml}")

    # Dry-run mode: just print what would happen
    if args.dry_run:
        print("[dry-run] Would process ecoregions:")
        print(f"  Input shapefile: {args.ecoregions_shp}")
        print(f"  Output GeoPackage: {args.out_gpkg}")
        print(f"  Regions YAML: {args.regions_yaml}")
        print(f"  Scheme/Level: {args.scheme} / {args.level}")
        return 0

    # Load regions from YAML
    # This is done here (not in prep_ecoregions) so we can use the shared loader
    regions = load_regions_yaml(args.regions_yaml)

    # Lazy import: keeps CLI startup fast, avoids loading geopandas until needed
    from geo.prep_ecoregions import prep_ecoregions

    # Call the core function
    prep_ecoregions(
        regions=regions,
        ecoregions_shp=args.ecoregions_shp,
        out_gpkg=args.out_gpkg,
        layer=args.layer,
        scheme=args.scheme,
        level=args.level,
        code_field=args.code_field,
        target_crs=args.target_crs,
        area_crs=args.area_crs,
        dissolve=args.dissolve,
        qa_csv=args.qa_csv,
    )

    return 0


def _handle_clip_rasters(args: argparse.Namespace) -> int:
    """Handle the clip-rasters subcommand (placeholder)."""
    # TODO: Implement when clip_rasters.py has a callable function
    print("[not implemented] clip-rasters is a placeholder")
    print("Next steps:")
    print("  1. Add a clip_rasters() function to geo/clip_rasters.py")
    print("  2. Wire it up here similar to prep-ecoregions")
    return 1


def _handle_zonal_stats(args: argparse.Namespace) -> int:
    """Handle the zonal-stats subcommand (placeholder)."""
    # TODO: Implement when zonal_stats.py has a callable function
    print("[not implemented] zonal-stats is a placeholder")
    print("Next steps:")
    print("  1. Add a zonal_stats() function to geo/zonal_stats.py")
    print("  2. Wire it up here similar to prep-ecoregions")
    return 1


# -----------------------------------------------------------------------------
# Main entrypoint
# -----------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    """Main entrypoint for eden.geo CLI."""
    ap = build_parser()
    args = ap.parse_args(argv)

    # Dispatch to appropriate handler based on subcommand
    # This pattern keeps main() clean and makes it easy to add new commands
    handlers = {
        "prep-ecoregions": _handle_prep_ecoregions,
        "clip-rasters": _handle_clip_rasters,
        "zonal-stats": _handle_zonal_stats,
    }

    handler = handlers.get(args.command)
    if handler is None:
        raise SystemExit(f"Unknown command: {args.command}")

    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
