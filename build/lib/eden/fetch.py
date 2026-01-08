#!/usr/bin/env python3
"""eden.fetch

Small, v0-friendly fetch CLI.

Design goals:
- One entrypoint for ingestion only (not geo/features/model yet)
- One level of subcommands (dataset names)
- Config-driven defaults via YAML
- Optional verify mode that can check *all* sources (or one)

Examples:
  # CHELSA monthly (COG window-read + write AOI subset)
  python -m eden.fetch chelsa-monthly --aoi config --start-year 2011 --end-year 2020 --vars tas pr

  # NLCD Annual bundle
  python -m eden.fetch nlcd --year 2016 --coverage conus --product LndCov

  # Verify that cached/manual inputs exist
  python -m eden.fetch verify --source all
  python -m eden.fetch verify --source gnatsgo
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml


# -----------------------------
# YAML + AOI helpers
# -----------------------------

def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Config not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise SystemExit(f"Expected YAML mapping at {path}")
    return data


def _coerce_bbox(x: Any) -> Optional[Tuple[float, float, float, float]]:
    """Try to coerce [xmin, ymin, xmax, ymax] into a bbox tuple."""
    if x is None:
        return None
    if isinstance(x, (list, tuple)) and len(x) == 4:
        try:
            xmin, ymin, xmax, ymax = map(float, x)
            return (xmin, ymin, xmax, ymax)
        except Exception:
            return None
    return None


def _union_bbox(bboxes: Iterable[Tuple[float, float, float, float]]) -> Optional[Tuple[float, float, float, float]]:
    bboxes = list(bboxes)
    if not bboxes:
        return None
    xmin = min(b[0] for b in bboxes)
    ymin = min(b[1] for b in bboxes)
    xmax = max(b[2] for b in bboxes)
    ymax = max(b[3] for b in bboxes)
    return (xmin, ymin, xmax, ymax)


def _aoi_from_regions_yaml(regions_yaml: Dict[str, Any]) -> Optional[Tuple[float, float, float, float]]:
    """Resolve AOI bbox from a regions YAML.

    Accepts either:
    - top-level `bounds: [xmin, ymin, xmax, ymax]`
    - per-region entries with `bounds: [...]` under `regions:`

    Returns bbox in the same CRS you computed it in (likely EPSG:4326).
    """
    # Top-level bounds
    bbox = _coerce_bbox(regions_yaml.get("bounds"))
    if bbox:
        return bbox

    # Per-region bounds
    regions = regions_yaml.get("regions")
    if isinstance(regions, list):
        bboxes: List[Tuple[float, float, float, float]] = []
        for r in regions:
            if isinstance(r, dict):
                b = _coerce_bbox(r.get("bounds"))
                if b:
                    bboxes.append(b)
        return _union_bbox(bboxes)

    return None


def _format_bbox(b: Tuple[float, float, float, float]) -> str:
    return f"[{b[0]:.5f}, {b[1]:.5f}, {b[2]:.5f}, {b[3]:.5f}]"


# -----------------------------
# Verify helpers (lightweight)
# -----------------------------

def _verify_source(source_id: str, sources_yaml: Dict[str, Any]) -> Dict[str, Any]:
    """Best-effort verification.

    Rules:
    - If a source has `local_glob`, ensure it matches at least one file.
    - Else if it has `cache_dir`, ensure the directory exists and is non-empty.
    - Else: report "no verify rule".

    This is intentionally conservative: it won't claim correctness, just presence.
    """
    sources = sources_yaml.get("sources")
    if not isinstance(sources, dict) or source_id not in sources:
        return {"source": source_id, "ok": False, "reason": "unknown source"}

    cfg = sources[source_id]
    if not isinstance(cfg, dict):
        return {"source": source_id, "ok": False, "reason": "bad config block"}

    # Manual download sources (e.g., Box) can be handled via local_glob
    local_glob = cfg.get("local_glob")
    if isinstance(local_glob, str) and local_glob.strip():
        matches = sorted(Path().glob(local_glob))
        return {
            "source": source_id,
            "ok": len(matches) > 0,
            "rule": "local_glob",
            "count": len(matches),
            "sample": [str(p) for p in matches[:5]],
        }

    cache_dir = cfg.get("cache_dir")
    if isinstance(cache_dir, str) and cache_dir.strip():
        p = Path(cache_dir)
        if not p.exists() or not p.is_dir():
            return {"source": source_id, "ok": False, "rule": "cache_dir", "reason": f"missing dir: {p}"}
        # count a few files
        files = [x for x in p.rglob("*") if x.is_file()]
        return {"source": source_id, "ok": len(files) > 0, "rule": "cache_dir", "count": len(files), "sample": [str(x) for x in files[:5]]}

    return {"source": source_id, "ok": True, "rule": "none", "note": "no verify rule (skipped)"}


# -----------------------------
# CLI
# -----------------------------

@dataclass
class GlobalConfig:
    sources_path: Path
    regions_path: Path


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="eden.fetch", description="Fetch/verify datasets for EDEN-v0")

    # Global args (available for all subcommands)
    ap.add_argument("--sources-yaml", type=Path, default=Path("config/sources.yaml"), help="Path to sources.yaml")
    ap.add_argument("--regions-yaml", type=Path, default=Path("config/regions_v0.yaml"), help="Path to regions YAML (for AOI bounds)")
    ap.add_argument("--overwrite", action="store_true", help="Ignore cache and re-download/rewrite outputs")
    ap.add_argument("--dry-run", action="store_true", help="Print planned actions without downloading/writing")
    ap.add_argument("--limit", type=int, default=None, help="Debug: only process first N items")

    sub = ap.add_subparsers(dest="command", required=True)

    # --- chelsa-monthly ---
    chelsa = sub.add_parser("chelsa-monthly", help="Fetch CHELSA monthly (COG) subsets")
    chelsa.add_argument("--vars", nargs="+", default=None, help="Variables to fetch (default: vars_active from sources.yaml)")
    chelsa.add_argument("--start-year", type=int, required=True)
    chelsa.add_argument("--end-year", type=int, required=True)
    chelsa.add_argument("--months", nargs="+", default=None, help="Months to fetch like 01 02 ... (default from sources.yaml)")
    chelsa.add_argument("--aoi", default="config", choices=["config"], help="AOI selector (v0: only 'config' bbox from regions YAML)")

    # --- nlcd ---
    nlcd = sub.add_parser("nlcd", help="Fetch NLCD data bundles")
    nlcd.add_argument("--year", type=int, required=True)
    nlcd.add_argument("--product", default=None, help="Product code (default from sources.yaml, e.g. LndCov)")
    nlcd.add_argument("--coverage", choices=["conus", "ak", "hi"], default=None, help="Coverage (default from sources.yaml)")

    # --- verify ---
    ver = sub.add_parser("verify", help="Verify that required/local cached inputs exist")
    ver.add_argument("--source", default="all", help="Source id to verify (or 'all')")
    ver.add_argument("--json", action="store_true", help="Emit JSON to stdout")

    return ap


def main(argv: Optional[List[str]] = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)

    # Load YAMLs only once, inside main (so import doesn't have side effects)
    sources_yaml = _load_yaml(args.sources_yaml)
    regions_yaml = _load_yaml(args.regions_yaml)

    # Resolve AOI bbox (for commands that need it)
    aoi_bbox = _aoi_from_regions_yaml(regions_yaml)
    if args.command == "chelsa-monthly":
        if not aoi_bbox:
            raise SystemExit(
                f"Could not resolve AOI bounds from {args.regions_yaml}. "
                "Add top-level 'bounds: [xmin,ymin,xmax,ymax]' or per-region bounds under 'regions:'"
            )

    # Dispatch
    if args.command == "verify":
        sources = sources_yaml.get("sources")
        if not isinstance(sources, dict):
            raise SystemExit("sources.yaml must contain top-level 'sources:' mapping")

        if args.source == "all":
            results = [_verify_source(sid, sources_yaml) for sid in sorted(sources.keys())]
        else:
            results = [_verify_source(args.source, sources_yaml)]

        ok = all(r.get("ok") for r in results)
        if args.json:
            print(json.dumps({"ok": ok, "results": results}, indent=2))
        else:
            for r in results:
                status = "OK" if r.get("ok") else "MISSING"
                print(f"[{status}] {r['source']} ({r.get('rule','?')})")
                if "reason" in r:
                    print(f"  - reason: {r['reason']}")
                if "count" in r:
                    print(f"  - count: {r['count']}")
                if "sample" in r and r["sample"]:
                    for s in r["sample"]:
                        print(f"    - {s}")
            print(f"Overall: {'OK' if ok else 'NOT OK'}")
        return 0 if ok else 2

    if args.command == "chelsa-monthly":
        # Pull defaults from sources.yaml
        src_cfg = sources_yaml.get("sources", {}).get("chelsa-monthly")
        if not isinstance(src_cfg, dict):
            raise SystemExit("sources.yaml missing sources: -> chelsa-monthly")

        vars_active = src_cfg.get("vars_active")
        if args.vars is None:
            if isinstance(vars_active, list) and vars_active:
                vars_to_get = [str(v) for v in vars_active]
            else:
                raise SystemExit("No --vars provided and sources.yaml has no vars_active for chelsa-monthly")
        else:
            vars_to_get = args.vars

        months = args.months
        if months is None:
            # try config temporal.months
            temporal = src_cfg.get("temporal", {})
            cfg_months = temporal.get("months") if isinstance(temporal, dict) else None
            if isinstance(cfg_months, list) and cfg_months:
                months = [str(m).zfill(2) for m in cfg_months]
            else:
                months = [f"{m:02d}" for m in range(1, 13)]
        else:
            months = [str(m).zfill(2) for m in months]

        # Lazy import handler (keeps CLI import fast and avoids heavy deps unless used)
        from ingest.fetch_chelsa_monthly import fetch_chelsa_monthly  # type: ignore

        print(f"AOI bbox from config: {_format_bbox(aoi_bbox)}")
        return fetch_chelsa_monthly(
            sources_yaml=sources_yaml,
            aoi_bbox=aoi_bbox,  # type: ignore
            vars_to_get=vars_to_get,
            start_year=args.start_year,
            end_year=args.end_year,
            months=months,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
            limit=args.limit,
        )

    if args.command == "nlcd":
        src_cfg = sources_yaml.get("sources", {}).get("nlcd")
        if not isinstance(src_cfg, dict):
            raise SystemExit("sources.yaml missing sources: -> nlcd")

        product = args.product or src_cfg.get("product")
        if not product:
            raise SystemExit("NLCD requires --product or sources.yaml sources.nlcd.product")

        coverage = args.coverage or src_cfg.get("default_coverage") or src_cfg.get("coverage")
        # Allow coverage_map (conus -> CU)
        coverage_map = src_cfg.get("coverage_map") if isinstance(src_cfg.get("coverage_map"), dict) else {}
        coverage_code = coverage_map.get(coverage, coverage) if coverage else coverage

        from ingest.fetch_nlcd import fetch_nlcd  # type: ignore

        return fetch_nlcd(
            sources_yaml=sources_yaml,
            year=args.year,
            product=str(product),
            coverage=str(coverage_code) if coverage_code else None,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
        )

    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())