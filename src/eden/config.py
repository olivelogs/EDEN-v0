#!/usr/bin/env python3
"""eden.config

Shared configuration utilities for EDEN CLI subsystems.

This module provides common helpers used across eden.ingest, eden.geo, etc.
Centralizing these avoids duplication and ensures consistent behavior.

Design notes:
- YAML loading is strict: files must exist and be valid mappings.
- Bbox handling supports both top-level and per-region bounds in regions YAML.
- All functions are pure (no side effects on import).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml


# -----------------------------------------------------------------------------
# YAML loading
# -----------------------------------------------------------------------------

def load_yaml(path: Path) -> Dict[str, Any]:
    """Load a YAML file and return as dict.

    Raises SystemExit on missing file or invalid format (non-mapping).
    This strict behavior is intentional: config errors should fail fast.
    """
    if not path.exists():
        raise SystemExit(f"Config not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise SystemExit(f"Expected YAML mapping at {path}")
    return data


def load_regions_yaml(path: Path) -> List[dict]:
    """Load regions from a regions YAML file.

    Expects structure like:
        regions:
          - uid: "..."
            code: "7"
            ...

    Returns the list of region dicts.
    Raises ValueError if structure is invalid.
    """
    data = load_yaml(path)
    if "regions" not in data or not isinstance(data["regions"], list):
        raise ValueError(f"{path} must have a top-level 'regions:' list.")
    return data["regions"]


# -----------------------------------------------------------------------------
# Bounding box utilities
# -----------------------------------------------------------------------------
# These are used by fetch (for AOI subsetting) and geo (for bounds extraction).

def coerce_bbox(x: Any) -> Optional[Tuple[float, float, float, float]]:
    """Try to coerce [xmin, ymin, xmax, ymax] into a bbox tuple.

    Returns None if input is invalid or missing.
    Accepts lists, tuples, or anything indexable with 4 numeric elements.
    """
    if x is None:
        return None
    if isinstance(x, (list, tuple)) and len(x) == 4:
        try:
            xmin, ymin, xmax, ymax = map(float, x)
            return (xmin, ymin, xmax, ymax)
        except Exception:
            return None
    return None


def union_bbox(
    bboxes: Iterable[Tuple[float, float, float, float]]
) -> Optional[Tuple[float, float, float, float]]:
    """Compute the bounding box that contains all input bboxes.

    Returns None if input is empty.
    """
    bboxes = list(bboxes)
    if not bboxes:
        return None
    xmin = min(b[0] for b in bboxes)
    ymin = min(b[1] for b in bboxes)
    xmax = max(b[2] for b in bboxes)
    ymax = max(b[3] for b in bboxes)
    return (xmin, ymin, xmax, ymax)


def aoi_from_regions_yaml(
    regions_yaml: Dict[str, Any]
) -> Optional[Tuple[float, float, float, float]]:
    """Resolve AOI bbox from a regions YAML dict.

    Accepts either:
    - top-level `bounds: [xmin, ymin, xmax, ymax]`
    - per-region entries with `bounds: [...]` under `regions:`

    If per-region bounds exist, returns their union.
    Returns None if no valid bounds found.
    """
    # Try top-level bounds first
    bbox = coerce_bbox(regions_yaml.get("bounds"))
    if bbox:
        return bbox

    # Fall back to per-region bounds
    regions = regions_yaml.get("regions")
    if isinstance(regions, list):
        bboxes: List[Tuple[float, float, float, float]] = []
        for r in regions:
            if isinstance(r, dict):
                b = coerce_bbox(r.get("bounds"))
                if b:
                    bboxes.append(b)
        return union_bbox(bboxes)

    return None


def format_bbox(b: Tuple[float, float, float, float], precision: int = 5) -> str:
    """Format a bbox tuple as a readable string."""
    return f"[{b[0]:.{precision}f}, {b[1]:.{precision}f}, {b[2]:.{precision}f}, {b[3]:.{precision}f}]"


# -----------------------------------------------------------------------------
# Default paths
# -----------------------------------------------------------------------------
# Centralized so all CLIs use the same defaults.

DEFAULT_SOURCES_YAML = Path("config/sources.yaml")
DEFAULT_REGIONS_YAML = Path("config/regions_v0.yaml")
