# Notes  

## overview

**in-progress task:** fetch scripts -> CLI

v0 reconstructs ecoregions from public data: soil, climate, landcover... once that is done we will build a model to infer ecosystem dynamics. goal: get it to report soil moisture changes after rain. that is all.

CLI will call other scripts... should check if file structure is good.

## general

use conda env eden
note to self: always branch before edits, or cry later.

## Data  

Data fetch:  
- `src/ingest/fetch.py`
- `src/ingest/sources/chelsa.py`, `src/ingest/sources/nlcd.py` = source-specific logic  
- `config/sources.yaml` = metadata registry (URLs/templates, versions, variables, caching rules, etc.)  
- one command style (python -m src.ingest.fetch ...)  
- shared caching/logging/path handling  
- source modules stay isolated (so CHELSA changes don’t break soils)  
usage:
`python -m src.ingest.fetch chelsa-monthly --vars tas pr --start 2011 --end 2020 --aoi conus`   
`python -m src.ingest.fetch nlcd --year 2016 --aoi conus`  

### Ecoregions  

Sticking to L3. North America CEC codes use hierarchal dotted codes (8 -> 8.1 -> 8.1.6); these only go to level III. CONUS EPA codes for level III and IV use alphanumeric (56 at level III or 56h at level IV). In regions_v0.yaml, I'm using the EPA alphanumeric codes in UID. Scheme: EPA_US. When I add in North America (in v1) scheme will change to EPA_CEC for the rest of the codes.  

### Soil  

SSURGO: gNATSGO
This seems to contain 2025 data only?  
Manual download  

### Climate  

CHELSA  
bioclim: 1981-2010 timestep; global.  
CHANGE (12-14-25): use CHELSA-monthly.  
CHELSA data are COGs. Use that.

### Landcover  

Multi-Resolution Land Characteristics (MRLC)  
Select a year, maybe two. Recent will be higher-res, i assume.  

## Scripts

this has gotten out of hand. need to update.

`prep_ecoregions.py`  

- reads `regions.yaml` (scheme/level/code + scheme-agnostic `uid`)  
- loads the EPA CONUS Level III shapefile (`data/raw/boundaries/epa_ecoregions/conus_level3.shp`)  
- auto-detects the “Level III code” column  
- normalizes codes ("07", 7, "7" all match)
- fixes invalid geometries
- optionally dissolves to 1 row per ecoregion
- writes `ecoregions_selected.gpkg`
- optionally writes a QA CSV (areas, etc.)

`01_region_selection.ipynb`  
pulls those bounds so i can read them, then use them in regions_v0.yaml for fetch scripts. todo: add this to prep_ecoregions to get it done in one go.  

`fetch.py`
it follows a URL template, using sources.yaml, and pulls the data from those sources. each data source has its own quirks,

`clip_rasters.py`  
make CHELSA/NLCD/soils stop being enormous. may be good to tie this into the fetch scripts, get it done right away.

`zonal_stats.py`  
turn pixels into features
