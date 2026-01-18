#!/usr/bin/env python3
"""fetch_ecoregions.py

Fetch EPA ecoregion shapefiles.

This handler:
- Renders ZIP URL from sources.yaml config
- Downloads to data/raw/boundaries/epa_ecoregions/
- Extracts the ZIP (shapefile components)
- Respects --dry-run and --overwrite

Called by:
  python -m eden.registry fetch-ecoregions

The downloaded shapefile is then processed by prep_ecoregions.py.
"""

from __future__ import annotations

import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Dict


def _render_url(template: str, context: Dict[str, Any]) -> str:
    """Render URL template with context dict."""
    try:
        return template.format(**context)
    except KeyError as e:
        raise KeyError(f"Missing key for ecoregions url_template: {e.args[0]}") from e


def _ensure_dir(p: Path) -> None:
    """Create directory if it doesn't exist."""
    p.mkdir(parents=True, exist_ok=True)


def _extract_zip(zip_path: Path, extract_to: Path) -> None:
    """Extract ZIP file to target directory.

    Creates a subdirectory named after the ZIP file (without extension)
    to keep shapefile components together.
    """
    # Create subdirectory named after the ZIP (e.g., us_eco_l3/)
    subdir_name = zip_path.stem
    extract_dir = extract_to / subdir_name
    _ensure_dir(extract_dir)

    print(f"[ECOREGIONS] Extracting to: {extract_dir}")

    with zipfile.ZipFile(zip_path, "r") as zf:
        # List contents for visibility
        members = zf.namelist()
        print(f"[ECOREGIONS] ZIP contains {len(members)} files")

        # Extract all
        zf.extractall(extract_dir)

    print(f"[ECOREGIONS] Extraction complete")


def fetch_ecoregions(
    *,
    sources_yaml: Dict[str, Any],
    overwrite: bool = False,
    dry_run: bool = False,
    extract: bool = True,
) -> int:
    """Fetch EPA ecoregion shapefile ZIP and optionally extract.

    Parameters
    ----------
    sources_yaml : dict
        Parsed sources.yaml
    overwrite : bool
        If True, re-download even if file exists
    dry_run : bool
        If True, print planned actions without downloading
    extract : bool
        If True, extract ZIP after download (default: True)

    Returns
    -------
    int
        Exit code (0 = success)
    """
    sources = sources_yaml.get("sources", {})
    cfg = sources.get("ecoregions")
    if not isinstance(cfg, dict):
        raise SystemExit("sources.yaml missing sources: -> ecoregions")

    template = cfg.get("url_template")
    if not template:
        raise SystemExit("ecoregions config missing url_template")

    # Output directory
    cache_dir = Path(cfg.get("cache_dir", "data/raw/boundaries/epa_ecoregions"))
    _ensure_dir(cache_dir)

    # Build URL from template
    context: Dict[str, Any] = {
        "base_url": cfg.get("base_url"),
        "coverage_path": cfg.get("coverage_path"),
        "product": cfg.get("product"),
    }

    url = _render_url(template, context)

    # Output path for ZIP
    zip_name = Path(url).name  # e.g., us_eco_l3.zip
    zip_path = cache_dir / zip_name

    # Check for existing shapefile (extracted)
    # The shapefile directory would be cache_dir/us_eco_l3/
    extracted_dir = cache_dir / zip_path.stem
    shp_files = list(extracted_dir.glob("*.shp")) if extracted_dir.exists() else []

    if shp_files and not overwrite:
        print(f"[SKIP] Ecoregions shapefile already exists: {shp_files[0]}")
        return 0

    if zip_path.exists() and not overwrite:
        print(f"[SKIP] Ecoregions ZIP already exists: {zip_path}")
        # Still extract if needed
        if extract and not shp_files:
            if not dry_run:
                _extract_zip(zip_path, cache_dir)
        return 0

    # Show what we'll do
    print(f"[ECOREGIONS] URL: {url}")
    print(f"[ECOREGIONS] ZIP: {zip_path}")

    if dry_run:
        print("[DRY-RUN] No download performed")
        if extract:
            print(f"[DRY-RUN] Would extract to: {cache_dir / zip_path.stem}")
        return 0

    # Download
    try:
        print("[ECOREGIONS] Downloading...")
        urllib.request.urlretrieve(url, zip_path)
        print("[ECOREGIONS] Download complete")
    except Exception as e:
        raise SystemExit(f"Failed to download ecoregions from {url}: {e}") from e

    # Extract
    if extract:
        _extract_zip(zip_path, cache_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(
        "This module is not meant to be run directly. "
        "Use: python -m eden.registry fetch-ecoregions"
    )
