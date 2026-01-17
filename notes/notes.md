# Notes  

## Running locally, start environment

```bash
conda activate eden
```
  
## Before starting, in root, run (first install):

```bash
pip install -e .
```
  
to tell python where to find packages. 
  
## Note:  

fixes to address in refactor plan:

- ingest ecoregion shapefile
- prep ecoregion to get bounds
- eliminate circular dependency 

## one more note:

workflow assumes **EPSG:4326** (lon/lat).
  
---

#### `config.py`

one script for shared config utilities.  
YAML loading, bbox handling, centralized path defaults.
new: handle read `regions_v0_bounds.parquet` (bounds) and read `regions_v0.gpkg` (geom), which are produced by eden.registry
  
---

## `eden.registry`

ecoregion handling CLI.

### `registry.py`

dispatcher.
optional arg: l3 or l4 ecoregion. yaml is only prepared for l3 right now.

### `fetch_ecoregions.py`

fetch ecoregion shapefiles and unzip. uses URL template in `sources.yaml`.

### `prep_ecoregions.py`

Load shapefile(s), filter to selected IDs, reproject to a common CRS, save `data/interim/tables/regions_v0_bounds.parquet` with computed bounds and `data/interim/vectors/regions_v0.gpkg`

---

## `eden.fetch`

Data ingestion CLI.
  
### `fetch.py`

args:
`--dry-run`: print what _would_ happen
`--overwrite`: perform fetch even if file exists
`--limit`: mostly for CHELSA download. limits the total number of (`var`, `year`, `month`) combinations processed. For example, with 2 variables and monthly data, `--limit 24` processes one full year.
  
`verify` lives in eden.fetch dispatcher. `verify` will check presence of the file.
`decompress` should live in eden.fetch dispatcher to decompress raw data files.
  
**Usage example:**

```bash
python -m eden.fetch verify --source all
```
  
#### `fetch_nlcd.py`

- Take resolved config (`sources.yaml`) + CLI choices, render one URL, download one ZIP.
- If a key is missing from YAML, hard error.
- Coverage is optional. config can apply defaults, CLI can override. matters for adding outside CONUS.
- `eden.fetch nlcd` will **not** unzip contents, inspect rasters, clip to AOI, infer band names, zonal stats, aggregation, or any modeling.
  
**note**: `--dry-run` is part of `eden.fetch`, needs to be run on fetch; before package.

**Usage example:**
```bash
python -m eden.fetch --dry-run nlcd --year 2016`
```

#### `fetch_chelsa_monthly.py`

> run `eden.geo prep_ecoregions` first, and make sure bounds are in `regions_v0.yaml`! *i'll fix to automate this soon* #TODO 

- Loops over variables (`tas`, `pr`, etc.), years (e.g. `2011–2020`), months (`01–12`).
- Render the URL from `sources.yaml`
- Open the remote COG with GDAL’s `/vsicurl/`, and read *only* the AOI bbox.
- Write a small local GeoTIFF to `data/interim/rasters/clipped/chelsa-monthly/…`.
- Respects `eden.fetch` top-level commands: `--dry-run`, `--overwrite`, `--limit`.
- Resolve output directory, build iterable of (`var`, `year`, `month`), optionally slice by --limit
- `eden.fetch chelsa-monthly` pulls already-clipped rasters, but will **not** do zonal stats, aggregation, or any modeling.

**Usage example:**

```bash
python -m eden.fetch --dry-run chelsa-monthly --start-year 2011 --end-year 2011 --vars tas pr --limit 2
```

---
## `eden.geo`

geospatial processing CLI.
structure for snakemake - will implement in v0.1 or v0.2.

### `geo.py`

dispatcher
  
### `clip_rasters.py`

Uses `regions_v0_bounds.parquet` and/or `regions_v0.gpkg` to clip soil/landcover rasters to a bounding box around selected polygons.
outputs to `interim/rasters/clipped/...`
  
### `zonal_stats.py`

compute per-polygon summaries (mean, sd, min/max, percent cover, etc.). output to `data/interim/tables/zonal_stats.parquet`.

### `qa_geo.py`

quality check on zonal_stats output
  
---

## `eden.features`

tabularization. in progress

### `feature_defs.py`

### `build_features.py`

join everything into `region_features.parquet`

### `perturb_features.py`

### `derived_features.py`

### `validate_features.py`
  
---

### `eden.model`

modeling with random forest
