#!/usr/bin/env python3
"""eden.registry

Region definition CLI for EDEN.

This is one of several EDEN subsystem CLIs:
- eden.registry → region definition and bounds (this file)
- eden.ingest   → data ingestion (CHELSA, NLCD, etc.)
- eden.geo      → geospatial processing (clip, zonal stats)
- eden.features → feature engineering (TODO)
- eden.model    → ecosystem modeling (TODO)

eden.registry is the source of truth for spatial regions in EDEN.
It defines WHAT EXISTS spatially. All other subsystems consume its outputs.

Responsibilities:
- Fetch region source data (EPA ecoregion shapefiles)
- Clean, dissolve, and normalize region geometries
- Assign stable IDs from regions YAML
- Compute bounding boxes
- Emit versioned artifacts (GeoPackage, bounds parquet)

Outputs:
- data/interim/vectors/regions_v0.gpkg  → canonical geometries
- data/interim/tables/regions_v0_bounds.parquet  → computed bounds

Design notes:
- Registry outputs are read-only for downstream modules
- Bounds come from parquet (computed), not YAML (manual)
- Ecoregions are v0 training wheels; later versions may use different region sources

Examples:
  # Fetch EPA ecoregion shapefiles
  python -m eden.registry fetch-ecoregions

  # Prepare regions (filter, clean, compute bounds)
  python -m eden.registry prep-ecoregions \
    --ecoregions-shp data/raw/boundaries/epa_ecoregions/us_eco_l3/us_eco_l3.shp
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Optional

from eden.config import (
    load_yaml,
    load_regions_yaml,
    DEFAULT_REGIONS_YAML,
    DEFAULT_SOURCES_YAML,
)


# -----------------------------------------------------------------------------
# Default output paths
# -----------------------------------------------------------------------------
# These are the canonical output locations for registry artifacts.
# Downstream modules should read from these paths.

DEFAULT_REGIONS_GPKG = Path("data/interim/vectors/regions_v0.gpkg")
DEFAULT_BOUNDS_PARQUET = Path("data/interim/tables/regions_v0_bounds.parquet")


# -----------------------------------------------------------------------------
# CLI structure
# -----------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for eden.registry."""
    ap = argparse.ArgumentParser(
        prog="eden.registry",
        description="Region definition for EDEN (source of truth for spatial units)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Subsystem CLIs:
  python -m eden.registry  # Region definition (this)
  python -m eden.ingest    # Data ingestion
  python -m eden.geo       # Geospatial processing
  python -m eden.features  # Feature engineering (TODO)
  python -m eden.model     # Ecosystem modeling (TODO)

Registry outputs:
  data/interim/vectors/regions_v0.gpkg        # Canonical geometries
  data/interim/tables/regions_v0_bounds.parquet  # Computed bounds
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
        "--sources-yaml",
        type=Path,
        default=DEFAULT_SOURCES_YAML,
        help=f"Path to sources YAML (default: {DEFAULT_SOURCES_YAML})",
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

    # --- fetch-ecoregions ---
    # Downloads EPA ecoregion shapefiles
    fetch = sub.add_parser(
        "fetch-ecoregions",
        help="Download EPA ecoregion shapefiles",
        description="""
Download EPA Level III ecoregion shapefiles from EPA servers.

Uses URL template from sources.yaml to construct download URL.
Downloads and extracts ZIP to data/raw/boundaries/epa_ecoregions/.
        """,
    )
    fetch.add_argument(
        "--level",
        type=int,
        default=3,
        choices=[3, 4],
        help="Ecoregion level to fetch (default: 3)",
    )

    # --- prep-ecoregions ---
    # Processes shapefiles into canonical registry outputs
    prep = sub.add_parser(
        "prep-ecoregions",
        help="Prepare regions from EPA shapefile",
        description="""
Process EPA ecoregions shapefile into canonical registry outputs.

This command:
1. Reads region definitions from regions YAML
2. Filters shapefile to requested regions
3. Cleans and dissolves geometries
4. Computes bounding boxes
5. Writes canonical outputs

Outputs:
- regions_v0.gpkg: Canonical geometries (WGS84)
- regions_v0_bounds.parquet: Computed bounds for each region
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
        type=Path,
        default=DEFAULT_REGIONS_GPKG,
        help=f"Output GeoPackage path (default: {DEFAULT_REGIONS_GPKG})",
    )
    prep.add_argument(
        "--out-bounds",
        type=Path,
        default=DEFAULT_BOUNDS_PARQUET,
        help=f"Output bounds parquet (default: {DEFAULT_BOUNDS_PARQUET})",
    )
    prep.add_argument(
        "--layer",
        default="regions",
        help="Layer name in output GeoPackage (default: regions)",
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
        default=True,
        help="Dissolve multipart features (default: True)",
    )
    prep.add_argument(
        "--no-dissolve",
        action="store_false",
        dest="dissolve",
        help="Don't dissolve multipart features",
    )

    return ap


# -----------------------------------------------------------------------------
# Command handlers
# -----------------------------------------------------------------------------

def _handle_fetch_ecoregions(args: argparse.Namespace) -> int:
    """Handle the fetch-ecoregions subcommand.

    Downloads EPA ecoregion shapefiles and extracts the ZIP.
    """
    # Load sources config
    sources_yaml = load_yaml(args.sources_yaml)

    # Lazy import
    from eden.registry.fetch_ecoregions import fetch_ecoregions

    return fetch_ecoregions(
        sources_yaml=sources_yaml,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
        extract=True,
    )


def _handle_prep_ecoregions(args: argparse.Namespace) -> int:
    """Handle the prep-ecoregions subcommand.

    This processes EPA shapefiles into canonical registry outputs:
    - regions_v0.gpkg: Clean geometries with stable IDs
    - regions_v0_bounds.parquet: Computed bounds for each region
    """
    # Validate inputs
    if not args.regions_yaml.exists():
        raise SystemExit(f"Regions YAML not found: {args.regions_yaml}")

    if args.dry_run:
        print("[dry-run] Would prepare regions:")
        print(f"  Input shapefile: {args.ecoregions_shp}")
        print(f"  Output GeoPackage: {args.out_gpkg}")
        print(f"  Output bounds: {args.out_bounds}")
        print(f"  Regions YAML: {args.regions_yaml}")
        print(f"  Scheme/Level: {args.scheme} / {args.level}")
        print(f"  Dissolve: {args.dissolve}")
        return 0

    # Load regions from YAML
    regions = load_regions_yaml(args.regions_yaml)

    # Lazy import to keep CLI startup fast
    from eden.registry.prep_ecoregions import prep_ecoregions

    # Call the core function
    # This returns the processed GeoDataFrame
    gdf = prep_ecoregions(
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
        qa_csv=None,  # Registry doesn't need separate QA CSV
    )

    # --- Compute and write bounds parquet ---
    # This is the key addition: bounds are computed here, not manually in YAML
    _write_bounds_parquet(gdf, args.out_bounds)

    return 0


def _write_bounds_parquet(gdf, out_path: Path) -> None:
    """Compute bounds for each region and write to parquet.

    This is the canonical source of bounds for downstream modules.
    eden.ingest should read from this, not from regions YAML.
    """
    import pandas as pd

    # Compute bounds for each region
    bounds_records = []
    for _, row in gdf.iterrows():
        minx, miny, maxx, maxy = row.geometry.bounds
        bounds_records.append({
            "uid": row["uid"],
            "code": row["code"],
            "name": row.get("name", ""),
            "xmin": minx,
            "ymin": miny,
            "xmax": maxx,
            "ymax": maxy,
            "area_km2": row.get("area_km2", None),
        })

    df = pd.DataFrame(bounds_records)

    # Write parquet
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)

    print(f"Wrote bounds -> {out_path}")
    print(f"  {len(df)} regions with computed bounds")


# -----------------------------------------------------------------------------
# Main entrypoint
# -----------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    """Main entrypoint for eden.registry CLI."""
    ap = build_parser()
    args = ap.parse_args(argv)

    handlers = {
        "fetch-ecoregions": _handle_fetch_ecoregions,
        "prep-ecoregions": _handle_prep_ecoregions,
    }

    handler = handlers.get(args.command)
    if handler is None:
        raise SystemExit(f"Unknown command: {args.command}")

    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
