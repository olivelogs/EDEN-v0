
#!/usr/bin/env python3
"""fetch_chelsa_monthly.py

Fetch CHELSA monthly v2.x Cloud Optimized GeoTIFFs (COGs) by reading ONLY an AOI window
and writing a small local GeoTIFF subset ("COG strategy 1").

This module is called by `python -m eden.fetch chelsa-monthly ...` via a thin dispatcher.

V0 scope (intentionally restrained):
- Render URL from sources.yaml + loop vars (var/year/month)
- Remote window read from COG over HTTP (via GDAL /vsicurl/)
- Write AOI subset GeoTIFF to data/interim/...
- Respect dry_run / overwrite / limit
- No aggregation, no zonal stats, no time summaries

Required deps (typical conda geo stack): rasterio, numpy
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds


BBox = Tuple[float, float, float, float]


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _render_url(template: str, context: Dict[str, Any]) -> str:
    try:
        return template.format(**context)
    except KeyError as e:
        missing = e.args[0]
        raise KeyError(f"Missing key for CHELSA url_template: {missing}") from e


def _vsi_url(url: str) -> str:
    """Force GDAL to use HTTP range requests (important for COG window reads)."""
    if url.startswith("/vsicurl/"):
        return url
    return f"/vsicurl/{url}"


def _safe_round_window(win):
    """Round window offsets/lengths to integers (GDAL prefers integer windows)."""
    return win.round_offsets().round_lengths()


def fetch_chelsa_monthly(
    *,
    sources_yaml: Dict[str, Any],
    aoi_bbox: BBox,
    vars_to_get: Sequence[str],
    start_year: int,
    end_year: int,
    months: Sequence[str],
    overwrite: bool = False,
    dry_run: bool = False,
    limit: Optional[int] = None,
) -> int:
    """Fetch AOI subsets for CHELSA monthly COGs.

    Parameters
    ----------
    sources_yaml : dict
        Parsed sources.yaml.
    aoi_bbox : (xmin, ymin, xmax, ymax)
        AOI bounds. Assumed EPSG:4326 (lon/lat) unless you later extend config.
    vars_to_get : list[str]
        Variables to fetch (e.g., ["tas", "pr"]).
    start_year, end_year : int
        Inclusive year range.
    months : list[str]
        Months as zero-padded strings: ["01", ..., "12"].
    overwrite : bool
        If False, skip outputs that already exist.
    dry_run : bool
        If True, print planned actions without reading/writing.
    limit : int | None
        Debug: only process first N items (counts both skipped and written).
    """

    sources = sources_yaml.get("sources", {})
    cfg = sources.get("chelsa-monthly")
    if not isinstance(cfg, dict):
        raise SystemExit("sources.yaml missing sources: -> chelsa-monthly")

    template = cfg.get("url_template")
    if not template:
        raise SystemExit("CHELSA config missing url_template")

    # Output directory for AOI subsets (separate from raw downloads)
    out_dir = Path(cfg.get("subset_dir", "data/interim/rasters/clipped/chelsa-monthly"))
    _ensure_dir(out_dir)

    version = str(cfg.get("version", "2.1"))

    # Base template context (everything that should not change per file)
    base_ctx: Dict[str, Any] = {
        "base_url": cfg.get("base_url"),
        "coverage_path": cfg.get("coverage_path"),
        "temporal_path": cfg.get("temporal_path"),
        "version": version,
    }

    # Basic guardrails
    if start_year > end_year:
        raise SystemExit(f"start_year ({start_year}) must be <= end_year ({end_year})")
    months_norm = [str(m).zfill(2) for m in months]

    # Planning loop
    n_planned = 0
    for var in vars_to_get:
        for year in range(int(start_year), int(end_year) + 1):
            for month in months_norm:
                n_planned += 1
                if limit is not None and n_planned > int(limit):
                    print(f"[CHELSA] Reached --limit {limit}; stopping")
                    return 0

                ctx = dict(base_ctx)
                ctx.update({"var": str(var), "year": int(year), "month": str(month)})

                url = _render_url(str(template), ctx)
                vsi = _vsi_url(url)

                # Deterministic filename (mirrors the upstream name, with AOI suffix)
                # Example upstream: CHELSA_clt_01_1979_V.2.1.tif
                # Local output:     CHELSA_clt_01_1979_V.2.1_AOI.tif
                upstream_name = Path(url).name
                out_path = out_dir / upstream_name.replace(".tif", "_AOI.tif")

                if out_path.exists() and not overwrite:
                    print(f"[SKIP] {out_path.name}")
                    continue

                print(f"[CHELSA] {var} {year}-{month}")
                print(f"  - url: {url}")
                print(f"  - out: {out_path}")

                if dry_run:
                    continue

                # Remote COG window-read
                # Use GDAL_DISABLE_READDIR_ON_OPEN to avoid expensive directory listings on remote stores.
                env_opts = {
                    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
                    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
                }

                try:
                    with rasterio.Env(**env_opts):
                        with rasterio.open(vsi) as src:
                            if src.crs is None:
                                raise SystemExit(f"Remote raster has no CRS: {url}")

                            # AOI bbox is EPSG:4326 by convention in this project (lon/lat)
                            bbox_src = aoi_bbox
                            bbox_in_raster_crs = bbox_src

                            # Transform bounds into raster CRS if needed
                            raster_crs = src.crs
                            if str(raster_crs).upper() not in ("EPSG:4326", "WGS84"):
                                # rasterio.warp.transform_bounds handles densification to avoid weird edge warps
                                bbox_in_raster_crs = transform_bounds(
                                    "EPSG:4326",
                                    raster_crs,
                                    bbox_src[0],
                                    bbox_src[1],
                                    bbox_src[2],
                                    bbox_src[3],
                                    densify_pts=21,
                                )

                            win = from_bounds(
                                *bbox_in_raster_crs,
                                transform=src.transform,
                            )
                            win = _safe_round_window(win)

                            # Read all bands (most CHELSA layers are single-band, but keep it general)
                            data = src.read(window=win, boundless=True)

                            # If boundless read produced all-nodata (e.g., bbox totally outside), warn and skip
                            nodata = src.nodata
                            if nodata is not None:
                                # check if everything equals nodata (allow NaN nodata too)
                                if np.issubdtype(data.dtype, np.floating) and np.isnan(nodata):
                                    all_nodata = np.isnan(data).all()
                                else:
                                    all_nodata = (data == nodata).all()
                                if all_nodata:
                                    print("  - warning: AOI window is all nodata; skipping write")
                                    continue

                            profile = src.profile.copy()
                            profile.update(
                                driver="GTiff",
                                height=data.shape[1],
                                width=data.shape[2],
                                transform=src.window_transform(win),
                                count=data.shape[0],
                                tiled=True,
                                compress="deflate",
                            )

                    # Write outside of the rasterio.open(vsi) context
                    _ensure_dir(out_path.parent)
                    with rasterio.open(out_path, "w", **profile) as dst:
                        dst.write(data)

                except Exception as e:
                    raise SystemExit(f"CHELSA fetch failed for {url}: {e}") from e

    print("[CHELSA] Done")
    return 0


if __name__ == "__main__":
    raise SystemExit(
        "This module is not meant to be run directly. "
        "Use: python -m eden.fetch chelsa-monthly --start-year ... --end-year ..."
    )
