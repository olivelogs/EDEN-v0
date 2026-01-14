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

These are fixes I need to make, since this isn't very smooth:

- In order to run `fetch_chelsa_monthly.py`, you will need to run `eden.geo prep_ecoregions` to get the AOI bounds.
  - Then you gotta run 01_region_selection.ipynb to consolidate bounds, and manually add these bounds to the YAML. **Fix for this coming**.
- I neglected to include the ecoregion shapefile download in `eden.fetch`, so that's manual right now. **Fix for this coming**.

## one more note:

workflow assumes **EPSG:4326** (lon/lat).
  
---

#### `config.py`

one script for shared config utilities.  
YAML loading, bbox handling, centralized path defaults.
  
---

## `eden.fetch`

Data ingestion CLI.
  
### `fetch.py`

args:
`--dry-run`: print what _would_ happen
`--overwrite`: perform fetch even if file exists
`--limit`: mostly for CHELSA download. limits the total number of (`var`, `year`, `month`) combinations processed. For example, with 2 variables and monthly data, `--limit 24` processes one full year.
  
`verify` lives in eden.fetch dispatcher. `verify` will check presence of the file.
  
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
  
### `prep_ecoregions.py`

Load shapefile(s), filter to selected IDs, reproject to a common CRS, save ecoregions_selected.gpkg.
  
### `clip_rasters.py`

clip soil/landcover rasters to a bounding box around selected polygons (faster)
computes a CONUS bbox from your selected ecoregions
  
### `zonal_stats.py`

compute per-polygon summaries (mean, sd, min/max, percent cover, etc.)
  
### `build_features.py`

join everything into `region_features.parquet`
  
---

### `eden.features`

tabularization
  
---

### `eden.model`

modeling
random forest could be small...
do i have the gall for a differentiable ecosystem model?