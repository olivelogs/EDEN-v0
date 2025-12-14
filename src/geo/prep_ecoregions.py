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