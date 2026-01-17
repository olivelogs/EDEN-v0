**regions.gpkg + rasters → stats → QA → table**

---
## 1. `clip_rasters.py`
Touches data in `data/raw/`. NLCD and gNATSGO, not `boundaries/`. 
CHELSA-monthly was pulled in `eden.fetch` as COGs, clipped rasters already exist in `data/interim/`.

Uses `regions_v0_bounds.parquet` and/or `regions_v0.gpkg` to clip soil/landcover rasters to a bounding box around selected polygons.
outputs to `interim/rasters/clipped/...`

**Target output:**
- region-scoped rasters
```
data/
	interim/
	└──	rasters/
		└── clipped/
			  ├── nlcd/
			  │   ├── region_uid_nlcd.tif
			  │   └── ...
			  ├── gnatsgo/
			  │   ├── region_uid_gnatsgo.tif
			  │   └── ...
			  └── chelsa-monthly/
				  └── ...
```
example: `l3_025_high_plains_nlcd.tif`

---
## 2. `zonal_stats.py`

**Goal - take:**
- polygons (ecoregions)
- rasters (climate, land cover, soil, etc.)
- Computes summary statistics per region
	- mean, median, min, max
	- std / IQR
	- percent cover (for categorical rasters like NLCD)
	- counts / proportions
- Output in `data/interim/tables/zonal_stats.parquet`
	- tabular
	- one row per region × raster × band
	- ML-friendly

**Example:**
```
region_uid          | source   | variable     | stat   | value
---------------------------------------------------------------
l3_025_high_plains  | CHELSA   | bio01_temp   | mean   | 12.4
l3_025_high_plains  | NLCD     | forest       | pct    | 0.37
l3_025_high_plains  | gNATSGO  | clay_pct     | mean   | 18.2
```

**Will feed into:**
`feature_defs.py`
`build_features.py`
`perturb_features.py`?

---

## 3. `qa_geo.py`
**Goal - look for:**
- missing stats
- impossible values - e.g.:
    - negative precipitation
    - land cover percentages > 1
- CRS mismatches or precision issues
- raster extent gaps
- weird edge cases (tiny polygons, slivers, NaNs)
- regions that shouldn't be merged

**Checks:**
- row counts
- value ranges
- percent-sums ≈ 1
- null-rate thresholds

**Output:**
- pass/fail flags
- warnings
- maybe a lightweight report

---
## v0.1 or v0.2: eden.geo as workflow - snakemake
Once eden.geo works, we do not touch it lightly, and everything downstream trusts it implicitly.
Snakemake?

eden.geo is:
- deterministic
- IO-heavy
- parameterized by:
    - dataset
    - region set
    - resolution
- parallel by region
### Ideal shape
**One public endpoint**, e.g.
```
snakemake eden.geo --config config/geo.yaml
```

Under the hood:
1. clip_rasters (optional, dataset-dependent)
2. zonal_stats
3. qa_geo

Each step:
- cacheable
- resumable
- swappable (CHELSA vs WorldClim, etc.)

This also sets you up for:
- cluster execution later
- partial rebuilds
- reproducibility receipts