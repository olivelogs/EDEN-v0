#!/usr/bin/env python3
"""prep_ecoregions.py

Turn an EPA Level III (CONUS) ecoregions shapefile into a clean, filtered GeoPackage
based on regions listed in a YAML config (regions_v0.yaml).

This module exposes two interfaces:
1. prep_ecoregions() - callable function for programmatic use / CLI dispatch
2. main() - standalone CLI wrapper (for direct invocation)

The split allows eden.geo to import and call prep_ecoregions() directly,
while preserving backwards compatibility for standalone use.

Example (standalone):
  python src/geo/prep_ecoregions.py \
    --regions-yaml config/regions_v0.yaml \
    --ecoregions-shp data/raw/boundaries/epa_ecoregions/us_eco_l3/us_eco_l3.shp \
    --out-gpkg data/interim/vectors/ecoregions_selected.gpkg

Example (via eden.geo):
  python -m eden.geo prep-ecoregions \
    --ecoregions-shp data/raw/boundaries/epa_ecoregions/us_eco_l3/us_eco_l3.shp \
    --out-gpkg data/interim/vectors/ecoregions_selected.gpkg

Notes:
- This script is intentionally defensive about the "Level III code" field name.
- It normalizes codes so "07", 7, and "7" match.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import geopandas as gpd

try:
    import yaml  # pyyaml
except Exception as e:
    raise SystemExit("Missing dependency: pyyaml. Install it (pip/conda) and retry.") from e


# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------
# These are internal utilities. The public interface is prep_ecoregions().

def _normalize_code(x) -> str:
    """Normalize ecoregion code to a comparable string.

    Handles various formats: ints, '07', ' 7 ', '56h', etc.
    Returns empty string for invalid inputs.
    """
    if x is None:
        return ""
    s = str(x).strip()
    # Pull first alphanumeric token (handles '56h', '07', etc.)
    m = re.search(r"[A-Za-z0-9]+", s)
    if not m:
        return ""
    token = m.group(0)
    # Strip leading zeros for purely numeric codes
    if token.isdigit():
        token = str(int(token))
    return token


def _load_regions_yaml(path: Path) -> List[dict]:
    """Load and validate regions YAML.

    Expects:
        regions:
          - uid: "..."
            code: "7"
            scheme: "EPA_US"
            level: 3
            ...
    """
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict) or "regions" not in data or not isinstance(data["regions"], list):
        raise ValueError(f"{path} must be a YAML mapping with a top-level 'regions:' list.")
    return data["regions"]


def _pick_code_field(columns: List[str], preferred: Optional[str] = None) -> str:
    """Infer which shapefile column contains the Level III code.

    If preferred is provided and exists, use it.
    Otherwise, score columns by likelihood (looking for 'l3', 'code', etc.).

    This heuristic exists because EPA shapefiles have inconsistent column names
    across versions (US_L3CODE, L3_CODE, NA_L3CODE, etc.).
    """
    if preferred:
        if preferred in columns:
            return preferred
        raise ValueError(f"--code-field '{preferred}' not found. Available columns: {columns}")

    candidates = []
    for c in columns:
        cl = c.lower()
        score = 0
        # Strong signals for Level III code
        if "l3" in cl or "level3" in cl or "lvl3" in cl:
            score += 4
        if "code" in cl:
            score += 3
        if "us" in cl and ("l3" in cl or "level3" in cl):
            score += 2
        # Weaker signals
        if "eco" in cl or "ecoreg" in cl or "region" in cl:
            score += 1
        # Penalties for clearly non-code fields
        if "name" in cl or "desc" in cl or "label" in cl:
            score -= 2
        candidates.append((score, c))

    candidates.sort(reverse=True)
    best_score, best_col = candidates[0]
    if best_score < 3:
        raise ValueError(
            "Couldn't confidently infer the Level III code column. "
            "Pass --code-field explicitly.\n"
            f"Columns: {columns}\n"
            f"Top guesses: {candidates[:8]}"
        )
    return best_col


def _make_valid(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Attempt to fix invalid geometries.

    Tries multiple approaches for compatibility across geopandas/shapely versions:
    1. geopandas >= 0.13: GeoSeries.make_valid()
    2. shapely 2.0: shapely.make_valid()
    3. Fallback: buffer(0) trick (works but can alter geometry slightly)
    """
    # Try geopandas native method first
    try:
        gdf = gdf.copy()
        if hasattr(gdf.geometry, "make_valid"):
            gdf["geometry"] = gdf.geometry.make_valid()
            return gdf
    except Exception:
        pass

    # Try shapely 2.0 function
    try:
        from shapely import make_valid  # type: ignore

        gdf = gdf.copy()
        gdf["geometry"] = gdf.geometry.apply(lambda geom: make_valid(geom) if geom is not None else geom)
        return gdf
    except Exception:
        pass

    # Fallback: buffer(0) trick
    gdf = gdf.copy()
    gdf["geometry"] = gdf.geometry.buffer(0)
    return gdf


def _compute_area_km2(gdf: gpd.GeoDataFrame, area_crs: str = "EPSG:5070") -> List[float]:
    """Compute polygon area in km² using an equal-area CRS.

    Default CRS is EPSG:5070 (CONUS Albers), appropriate for CONUS ecoregions.
    For other regions, pass a suitable equal-area projection.
    """
    if gdf.crs is None:
        raise ValueError("Input geometries have no CRS; can't compute area safely.")
    tmp = gdf.to_crs(area_crs)
    return (tmp.geometry.area / 1_000_000.0).astype(float).tolist()


# -----------------------------------------------------------------------------
# Core function (called by CLI or eden.geo)
# -----------------------------------------------------------------------------

def prep_ecoregions(
    regions: List[dict],
    ecoregions_shp: Path,
    out_gpkg: Path,
    *,
    layer: str = "ecoregions_selected",
    scheme: str = "EPA_US",
    level: int = 3,
    code_field: Optional[str] = None,
    target_crs: str = "EPSG:4326",
    area_crs: str = "EPSG:5070",
    dissolve: bool = False,
    qa_csv: Optional[Path] = None,
) -> gpd.GeoDataFrame:
    """Process EPA ecoregions shapefile into a filtered, cleaned GeoPackage.

    This is the main workhorse function. It:
    1. Filters the shapefile to only requested regions (by code)
    2. Normalizes codes for consistent matching
    3. Fixes invalid geometries
    4. Optionally dissolves multipart features
    5. Computes areas in km²
    6. Reprojects to target CRS
    7. Writes output GeoPackage (and optional QA CSV)

    Args:
        regions: List of region dicts from regions YAML (must have 'code', 'uid', etc.)
        ecoregions_shp: Path to EPA Level III shapefile
        out_gpkg: Output GeoPackage path
        layer: Layer name in output GeoPackage
        scheme: Which scheme to filter from regions list (e.g., "EPA_US")
        level: Which level to filter (e.g., 3 for Level III)
        code_field: Explicit shapefile column for code (auto-detected if None)
        target_crs: CRS for output geometries (default WGS84)
        area_crs: CRS for area calculations (default CONUS Albers)
        dissolve: If True, dissolve multipart features into one row per uid
        qa_csv: Optional path to write QA summary CSV

    Returns:
        The processed GeoDataFrame (also written to out_gpkg).

    Raises:
        SystemExit: On missing files, no matching regions, or processing errors.
    """
    # --- Validate inputs ---
    if not ecoregions_shp.exists():
        raise SystemExit(f"Ecoregions shapefile not found: {ecoregions_shp}")

    # --- Filter regions by scheme/level ---
    # This allows the same regions YAML to contain multiple schemes (EPA_US, EPA_CEC, etc.)
    wanted = [r for r in regions if r.get("scheme") == scheme and int(r.get("level", -1)) == level]
    if not wanted:
        raise SystemExit(f"No regions found for scheme={scheme} level={level}")

    # Build lookup by normalized code
    wanted_by_code: Dict[str, dict] = {}
    for r in wanted:
        code = _normalize_code(r.get("code"))
        if not code:
            raise SystemExit(f"Region missing/invalid code: {r}")
        if code in wanted_by_code:
            raise SystemExit(f"Duplicate code in regions ({code}). Make codes unique per scheme+level.")
        wanted_by_code[code] = r

    wanted_codes = set(wanted_by_code.keys())

    # --- Load shapefile ---
    gdf = gpd.read_file(ecoregions_shp)

    if gdf.empty:
        raise SystemExit("Loaded shapefile but it contains zero features. Wrong file?")

    if gdf.crs is None:
        raise SystemExit(
            "Shapefile has no CRS (.prj missing or unreadable). "
            "Fix that first; everything downstream depends on CRS."
        )

    # --- Identify and normalize code field ---
    detected_code_field = _pick_code_field(list(gdf.columns), preferred=code_field)
    gdf["_code_norm"] = gdf[detected_code_field].apply(_normalize_code)

    # --- Filter to requested codes ---
    matches = gdf[gdf["_code_norm"].isin(wanted_codes)]
    if matches.empty:
        sample_codes = sorted(set([c for c in gdf["_code_norm"].unique().tolist() if c]))[:25]
        raise SystemExit(
            "None of your requested codes matched the shapefile.\n"
            f"Using code field: {detected_code_field}\n"
            f"Requested codes: {sorted(wanted_codes)}\n"
            f"Sample codes in shapefile: {sample_codes}\n"
            "Try --code-field explicitly if the inferred field is wrong."
        )

    out = matches.copy()

    # --- Attach canonical metadata from YAML ---
    # This ensures output has consistent field names regardless of shapefile schema
    out["scheme"] = scheme
    out["level"] = level
    out["code"] = out["_code_norm"]
    out["uid"] = out["_code_norm"].map(lambda c: wanted_by_code[c]["uid"])
    out["name"] = out["_code_norm"].map(lambda c: wanted_by_code[c].get("name", ""))

    # --- Geometry cleanup ---
    out = _make_valid(out)
    out = out[~out.geometry.is_empty & out.geometry.notna()].copy()

    # --- Optional dissolve ---
    # Useful when shapefile has multiple polygons per ecoregion (e.g., disjoint parts)
    if dissolve:
        meta_cols = ["uid", "scheme", "level", "code", "name"]
        out = out[meta_cols + ["geometry"]].dissolve(by="uid", as_index=False)

    # --- Compute area for QA ---
    out["area_km2"] = _compute_area_km2(out, area_crs=area_crs)

    # --- Reproject to output CRS ---
    # Usually EPSG:4326 to match climate rasters (CHELSA, WorldClim, etc.)
    out = out.to_crs(target_crs)

    # --- Clean up columns ---
    keep_cols = ["uid", "scheme", "level", "code", "name", "area_km2", "geometry"]
    keep_cols = [c for c in keep_cols if c in out.columns]
    out = out[keep_cols].copy()

    # --- Verify all requested codes were found ---
    found_codes = set(out["code"].astype(str).tolist())
    missing = wanted_codes - found_codes
    if missing:
        raise SystemExit(
            f"Missing requested codes after processing: {sorted(missing)}\n"
            "This usually means the shapefile doesn't include them, or codes are stored differently."
        )

    # --- Write outputs ---
    out_gpkg.parent.mkdir(parents=True, exist_ok=True)
    out.to_file(out_gpkg, layer=layer, driver="GPKG")

    if qa_csv:
        qa_csv.parent.mkdir(parents=True, exist_ok=True)
        qa = out.drop(columns="geometry").copy()
        qa.to_csv(qa_csv, index=False)

    # --- Human-friendly summary ---
    print(f"Wrote {len(out)} features -> {out_gpkg} (layer={layer})")
    print("Selected regions:")
    for _, row in out.drop(columns="geometry").sort_values(["code"]).iterrows():
        print(f"  - {row['uid']} | code={row['code']} | area_km2={row['area_km2']:.1f} | {row.get('name','')}")
    print(f"(Used code field: {detected_code_field}; output CRS: {target_crs})")

    return out


# -----------------------------------------------------------------------------
# CLI wrapper (standalone invocation)
# -----------------------------------------------------------------------------
# This is kept for backwards compatibility and direct script usage.
# When called via eden.geo, the CLI there handles arg parsing and calls
# prep_ecoregions() directly.

def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint for standalone use."""
    ap = argparse.ArgumentParser(
        description="Filter EPA ecoregions shapefile to selected regions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/geo/prep_ecoregions.py \\
    --regions-yaml config/regions_v0.yaml \\
    --ecoregions-shp data/raw/boundaries/epa_ecoregions/us_eco_l3/us_eco_l3.shp \\
    --out-gpkg data/interim/vectors/ecoregions_selected.gpkg
        """,
    )
    ap.add_argument("--regions-yaml", required=True, type=Path, help="YAML listing regions to select.")
    ap.add_argument("--ecoregions-shp", required=True, type=Path, help="EPA Level III (CONUS) shapefile path.")
    ap.add_argument("--out-gpkg", required=True, type=Path, help="Output GeoPackage path.")
    ap.add_argument("--layer", default="ecoregions_selected", help="GeoPackage layer name.")
    ap.add_argument("--scheme", default="EPA_US", help="Which scheme to select from regions YAML.")
    ap.add_argument("--level", default=3, type=int, help="Which level to select from regions YAML.")
    ap.add_argument("--code-field", default=None, help="Column in shapefile containing the Level III code.")
    ap.add_argument("--target-crs", default="EPSG:4326", help="CRS for output geometries (default WGS84).")
    ap.add_argument("--area-crs", default="EPSG:5070", help="CRS for area calculations (default CONUS Albers).")
    ap.add_argument("--dissolve", action="store_true", help="Dissolve multipart features into one row per uid.")
    ap.add_argument("--qa-csv", default=None, type=Path, help="Optional path to write a QA CSV summary.")
    args = ap.parse_args(argv)

    # Validate paths
    if not args.regions_yaml.exists():
        raise SystemExit(f"Regions YAML not found: {args.regions_yaml}")

    # Load regions and call core function
    regions = _load_regions_yaml(args.regions_yaml)

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


if __name__ == "__main__":
    raise SystemExit(main())
