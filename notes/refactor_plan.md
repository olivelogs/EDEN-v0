## 1. move all packages in src/ to src/eden/?

current structure:
```
EDEN-v0/
	src/
		eden/
			config.py
			fetch.py
			geo.py
		features/
		geo/
		ingest/
		modeling/
```

proposed structure:
```
EDEN-v0/
	...
	src/
		eden/
			config.py
			fetch.py
			geo.py
			registry.py
			features/
				__init__.py
				...
			geo/
				__init__.py
				clip_rasters.py
				zonal_stats.py
				qa_geo.py
			ingest/
				__init__.py
				fetch_chelsa.py
				fetch_nlcd.py
			modeling/
				__init__.py
				...
			registry/
				__init__.py
				fetch_ecoregions.py
				prep_ecoregions.py
```

We'll do this first. move everything into src/eden/, then runt tests/scripts to find what breaks, fix the imports, then move forward.

---
## 2. `eden.registry`

### The goal:
`eden.registry` defines and publishes the canonical set of spatial regions used by EDEN.
It ingests raw region sources, cleans and dissolves geometry, assigns stable IDs, computes bounding boxes, and emits versioned region artifacts.
All downstream modules (`fetch`, `geo`, `features`, `modules`) consume registry outputs and never modify them.
It defines _what exists_ spatially in EDEN.

**we will resolve the standing circular dependency issue with `prep_ecoregions.py` here.**
prep_ecoregions should not be part of `eden.geo` workflow.

### structure:
```
src/
	eden/
		registry.py                     # eden.registry package handler/CLI
		registry/
		  ├── fetch_ecoregions.py       # shapefiles, sources.yaml
		  ├── prep_ecoregions.py        # pull geom, dissolve, compute bounds
```

#### `fetch_ecoregions.py`
- pulls shapefiles from EPA according to URL template in `sources.yaml`
- decompresses .zip

#### `prep_ecoregions.py`
- overall, this does not significantly deviate from the original script. requirements:
- uses `regions_v0.yaml` for IDs, names
- clean geometry (fix invalids, dissolve, simplify if needed)
- reproject to common CRS
- subset/label/version-lock
- assign stable region IDs *from* `regions_v0.yaml`
- compute bounds
- outputs:
	- `data/interim/tables/regions_v0_bounds.parquet` → computed bounds
	- `data/interim/vectors/regions_v0.gpkg` → canonical geometry

---
## 3. `eden_fetch`

### Target Fixes to Current Build
- new argument in `fetch.py` to decompress raw data files
	- `.7z`, `.zip`, `.tar.gz`
- in `fetch_chelsa.py` COG bounds come from `regions_v0_bounds.parquet`, not `regions_v0.yaml`
- potentially add read `regions_v0_bounds.parquet` and read `regions_v0.gpkg` to `config.py`?

```
src/
└──	eden/
	├── config.py        # read regions_v0.yaml. 
	├── fetch.py         # eden.fetch package handler/CLI - scripts from ingest/. handles verify. add decompress
	└── ingest/
		├── fetch_nlcd.py    # fetch chelsa
		└── fetch_chelsa.py  # fetch chelsa via COG windows
```

`verify.py` and `decompress.py` should stay inside `fetch.py` for now.

### Final build should:
- get bounds from registry
- fetch CHELSA-monthly via COG windows
- fetch NLCD
- decompress NLCD, gNATSGO
- verify existence of data all three sources

>***note:*** gNATSGO is externally staged; fetch verifies + decompresses but does not download gNATSGO.

---
## 4.` eden.geo`
- no longer does prep_ecoregions, remove from handler
- clip rasters, zonal stats, qa, output `geo_features.parquet`
	- regions.gpkg + rasters → stats → QA → table
- structure for snakemake workflow
- see `eden_geo_build.md` for the rest of the build