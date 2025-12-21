#!/usr/bin/env python3

"""
prep_ecoregions.py

Turn an EPA Level III (CONUS) ecoregions shapefile into a clean, filtered GeoPackage
based on regions listed in a YAML config (regions_v0.yaml).

Example:
  python src/geo/prep_ecoregions.py \
    --regions-yaml config/regions_v0.yaml \
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


def _normalize_code(x) -> str:
    """Normalize ecoregion code to a comparable string. Handles ints, '07', ' 7 '."""
    if x is None:
        return ""
    s = str(x).strip() # removes whitespaces before regex..
    # pull first alnum token (handles '56h', '07', etc.)
    m = re.search(r"[A-Za-z0-9]+", s)
    if not m:
        return ""
    token = m.group(0)
    # strip leading zeros for purely numeric codes
    if token.isdigit():
        token = str(int(token))
    return token

# scold you for bad config
def _load_regions_yaml(path: Path) -> List[dict]:
    # Path is an argument?
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict) or "regions" not in data or not isinstance(data["regions"], list):
        raise ValueError(f"{path} must be a YAML mapping with a top-level 'regions:' list.")
    return data["regions"]


def _pick_code_field(columns: List[str], preferred: Optional[str] = None) -> str:
    """
    Try to infer which field contains the Level III code.

    If preferred is provided and exists, use it.
    Otherwise, score columns by likely-ness.
    """
    if preferred:
        if preferred in columns:
            return preferred
        raise ValueError(f"--code-field '{preferred}' not found. Available columns: {columns}")

    candidates = [] # making a dict?
    for c in columns:
        cl = c.lower()
        score = 0
        # strong signals
        if "l3" in cl or "level3" in cl or "lvl3" in cl:
            score += 4
        if "code" in cl:
            score += 3
        if "us" in cl and ("l3" in cl or "level3" in cl):
            score += 2
        # weaker signals
        if "eco" in cl or "ecoreg" in cl or "region" in cl:
            score += 1
        # penalties
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
    """Attempt to fix invalid geometries, without being picky about library versions."""
    # geopandas >= 0.13 has GeoSeries.make_valid
    try:
        gdf = gdf.copy()
        if hasattr(gdf.geometry, "make_valid"):
            gdf["geometry"] = gdf.geometry.make_valid()
            return gdf
    except Exception:
        pass

    # shapely 2.0 has shapely.make_valid
    try:
        from shapely import make_valid  # type: ignore

        gdf = gdf.copy()
        gdf["geometry"] = gdf.geometry.apply(lambda geom: make_valid(geom) if geom is not None else geom)
        return gdf
    except Exception:
        pass

    # fallback: buffer(0) trick
    gdf = gdf.copy()
    gdf["geometry"] = gdf.geometry.buffer(0)
    return gdf


def _compute_area_km2(gdf: gpd.GeoDataFrame, area_crs: str = "EPSG:5070") -> List[float]:
    """Compute polygon area in km^2 using an equal-area CRS (default: CONUS Albers)."""
    if gdf.crs is None:
        raise ValueError("Input geometries have no CRS; can't compute area safely.")
    tmp = gdf.to_crs(area_crs)
    return (tmp.geometry.area / 1_000_000.0).astype(float).tolist()

# args
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
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

    if not args.regions_yaml.exists():
        raise SystemExit(f"regions yaml not found: {args.regions_yaml}")
    if not args.ecoregions_shp.exists():
        raise SystemExit(f"ecoregions shapefile not found: {args.ecoregions_shp}")

    regions = _load_regions_yaml(args.regions_yaml)

    # filter requested regions
    wanted = [r for r in regions if r.get("scheme") == args.scheme and int(r.get("level", -1)) == args.level]
    if not wanted:
        raise SystemExit(f"No regions found in YAML for scheme={args.scheme} level={args.level}")

    wanted_by_code: Dict[str, dict] = {}
    for r in wanted:
        code = _normalize_code(r.get("code"))
        if not code:
            raise SystemExit(f"Region missing/invalid code: {r}")
        if code in wanted_by_code:
            raise SystemExit(f"Duplicate code in regions YAML ({code}). Make codes unique per scheme+level.")
        wanted_by_code[code] = r

    wanted_codes = set(wanted_by_code.keys())

    gdf = gpd.read_file(args.ecoregions_shp)

    if gdf.empty:
        raise SystemExit("Loaded shapefile but it contains zero features. Wrong file?")

    if gdf.crs is None:
        raise SystemExit(
            "Shapefile has no CRS (.prj missing or unreadable). "
            "Fix that first; everything downstream depends on CRS."
        )

    code_field = _pick_code_field(list(gdf.columns), preferred=args.code_field)
    gdf["_code_norm"] = gdf[code_field].apply(_normalize_code)

    # show quick mismatch help if nothing matches
    matches = gdf[gdf["_code_norm"].isin(wanted_codes)]
    if matches.empty:
        sample_codes = sorted(set([c for c in gdf["_code_norm"].unique().tolist() if c]))[:25]
        raise SystemExit(
            "None of your requested codes matched the shapefile.\n"
            f"Using code field: {code_field}\n"
            f"Requested codes: {sorted(wanted_codes)}\n"
            f"Sample codes in shapefile: {sample_codes}\n"
            "Try --code-field explicitly if the inferred field is wrong."
        )

    # keep only wanted
    out = matches.copy()

    # attach canonical metadata from YAML
    out["scheme"] = args.scheme
    out["level"] = args.level
    out["code"] = out["_code_norm"]
    out["uid"] = out["_code_norm"].map(lambda c: wanted_by_code[c]["uid"])
    out["name"] = out["_code_norm"].map(lambda c: wanted_by_code[c].get("name", ""))

    # geometry cleanup
    out = _make_valid(out)

    # drop empties post-fix
    out = out[~out.geometry.is_empty & out.geometry.notna()].copy()

    # optional dissolve: one row per uid (with unioned geometry)
    if args.dissolve:
        # dissolve unions geometry; keep metadata as first (they're identical per uid anyway)
        meta_cols = ["uid", "scheme", "level", "code", "name"]
        out = out[meta_cols + ["geometry"]].dissolve(by="uid", as_index=False)

    # compute area for QA / sanity checks
    out["area_km2"] = _compute_area_km2(out, area_crs=args.area_crs)

    # reproject for output (often EPSG:4326 to match climate rasters)
    out = out.to_crs(args.target_crs)

    # arrange columns nicely
    keep_cols = ["uid", "scheme", "level", "code", "name", "area_km2", "geometry"]
    keep_cols = [c for c in keep_cols if c in out.columns]
    out = out[keep_cols].copy()

    # check missing codes after dissolve/fix
    found_codes = set(out["code"].astype(str).tolist())
    missing = wanted_codes - found_codes
    if missing:
        raise SystemExit(
            f"Missing requested codes after processing: {sorted(missing)}\n"
            "This usually means the shapefile doesn't include them, or codes are stored differently."
        )

    # write outputs
    args.out_gpkg.parent.mkdir(parents=True, exist_ok=True)
    out.to_file(args.out_gpkg, layer=args.layer, driver="GPKG")

    if args.qa_csv:
        args.qa_csv.parent.mkdir(parents=True, exist_ok=True)
        # basic QA table
        qa = out.drop(columns="geometry").copy()
        qa.to_csv(args.qa_csv, index=False)

    # stdout summary (human joy)
    print(f"Wrote {len(out)} features → {args.out_gpkg} (layer={args.layer})")
    print("Selected regions:")
    for _, row in out.drop(columns="geometry").sort_values(["code"]).iterrows():
        print(f"  - {row['uid']} | code={row['code']} | area_km2={row['area_km2']:.1f} | {row.get('name','')}")
    print(f"(Used code field: {code_field}; output CRS: {args.target_crs})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())