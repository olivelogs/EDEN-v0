#!/usr/bin/env python3
"""
fetch_nlcd.py

Fetch NLCD Annual data bundles from MRLC.

This handler is intentionally simple for v0:
- Renders a single ZIP URL from sources.yaml + CLI args
- Downloads to data/raw/nlcd/
- Respects --dry-run and --overwrite
- Does NOT yet extract or clip rasters (that comes later)

Called by:
  python -m eden.fetch nlcd --year 2016
"""

from __future__ import annotations

import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional


def _render_url(template: str, context: Dict[str, Any]) -> str:
    try:
        return template.format(**context)
    except KeyError as e:
        raise KeyError(f"Missing key for NLCD url_template: {e.args[0]}") from e


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def fetch_nlcd(
    *,
    sources_yaml: Dict[str, Any],
    year: int,
    product: str,
    coverage: Optional[str],
    overwrite: bool = False,
    dry_run: bool = False,
) -> int:
    """
    Fetch an NLCD Annual ZIP bundle.

    Parameters
    ----------
    sources_yaml : dict
        Parsed sources.yaml
    year : int
        Year to fetch (e.g., 2016)
    product : str
        Product code (e.g., LndCov)
    coverage : str or None
        Coverage code (e.g., CU). If None, omit from template context.
    overwrite : bool
        If True, re-download even if file exists
    dry_run : bool
        If True, print planned URL and output path without downloading
    """

    sources = sources_yaml.get("sources", {})
    cfg = sources.get("nlcd")
    if not isinstance(cfg, dict):
        raise SystemExit("sources.yaml missing sources: -> nlcd")

    template = cfg.get("url_template")
    if not template:
        raise SystemExit("NLCD config missing url_template")

    base_dir = Path(cfg.get("cache_dir", "data/raw/nlcd"))
    _ensure_dir(base_dir)

    context: Dict[str, Any] = {
        "base_url": cfg.get("base_url"),
        "temporal_path": cfg.get("temporal_path"),
        "product": product,
        "year": year,
        "collection": cfg.get("collection"),
        "version": cfg.get("version"),
    }

    if coverage:
        context["coverage_code"] = coverage

    url = _render_url(template, context)

    out_name = Path(url).name
    out_path = base_dir / out_name

    if out_path.exists() and not overwrite:
        print(f"[SKIP] NLCD already exists: {out_path}")
        return 0

    print(f"[NLCD] URL: {url}")
    print(f"[NLCD] OUT: {out_path}")

    if dry_run:
        print("[DRY-RUN] No download performed")
        return 0

    try:
        print("[NLCD] Downloading...")
        urllib.request.urlretrieve(url, out_path)
    except Exception as e:
        raise SystemExit(f"Failed to download NLCD from {url}: {e}") from e

    print("[NLCD] Download complete")
    return 0


if __name__ == "__main__":
    raise SystemExit("This module is not meant to be run directly. Use: python -m eden.fetch nlcd ...")