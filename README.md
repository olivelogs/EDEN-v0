# EDEN v0

Ecological Digital Earth Network (thank you, Claude). This is a toy ecological modeling project.  
  
As it stands, EDEN-v0 is a modular, config-driven pipeline for assembling environmental datasets at the ecoregion scale, with an emphasis on reproducibility and laptop-friendly workflows (which is a more sophisticated way of saying, I'm doing this on a laptop).  
  
The current focus of v0 is data ingestion and spatial subsetting, not modeling - yet 😉.  
  
The base model is inspired by EPA ecoregion mapping, using the defining features of the region. Additional features are to be added as modules. Currently, only data for the Continental US (CONUS) is used.
  
---

## Status

This project is under active development (yay)!  
Current focus is on ingestion, AOI definition, and spatial preprocessing. Modeling and feature engineering are planned but not yet implemented.  
  
### Current Capabilities (01-13-2026)

EDEN-v0 currently supports:

- **Config-driven data ingestion**  
  - Data sources are defined in `sources.yaml`  
  - Ecoregions and AOIs are defined in `regions_v0.yaml`  
  
- **CHELSA Monthly Climate Data**  
  - Remote Cloud-Optimized GeoTIFFs (COGs)  
  - AOI-only window reads (no global downloads)  
  - Outputs clipped monthly rasters per variable  
  
- **NLCD Land Cover**  
  - Annual land cover bundles (ZIP)  
  - Downloaded as-is for later processing  

- **gNATSGO Soils**  
  - Manual download supported  
  - Local presence verified via config  
  
*Plans for v0.1*: elevation from NASADEM, hydrography from...?  
  
---

## Project Structure

```bash
EDEN-v0/
├── config/           # YAML configs (sources, regions)
├── src/
│   ├── eden/         # CLI entrypoints (fetch, geo, config)
│   ├── ingest/       # Fetch implementations
│   └── geo/          # Geo processing implementations
├── data/             # raw → interim → processed
└── notebooks/        # Exploration/QC
```

---

## Using EDEN

EDEN-v0 uses a standard src/ layout and editable installs. From the project root:  

```bash
pip install -e .
```
  
Dependencies can be found in `environment.yml`.  
  
#### Notes before usage: 

These are planned fixes, since this isn't very *smooth*:  

- In order to get the AOI bounds needed for `fetch_chelsa_monthly.py`, you will need to run `eden.geo prep_ecoregions`.  
  - Combine the bounds using `01_region_selection.ipynb`, then add them to `regions_v0.yaml`. Planning to add this step to `prep_ecoregions.py` soon! It is clunky!  
- I neglected to include the ecoregion shapefile download in `eden.fetch`, so that's also a manual download right now. Will add at a later date.  
  
Now, usage! The only thing that works so far is the data ingestion CLI, plus prep_ecoregions.  
  
**Handle ecoregions shapefiles:**

```bash
python -m eden.geo prep-ecoregions \
  --ecoregions-shp data/raw/boundaries/epa_ecoregions/us_eco_l3/us_eco_l3.shp \
  --out-gpkg data/interim/vectors/ecoregions_selected.gpkg
```

**To verify datasets exist:**
  
```bash
python -m eden.fetch verify --source all
```

**Fetch NLCD (landcover) data - 2016 in this example:**

```bash
python -m eden.fetch nlcd --year 2016
```
  
**Fetch CHELSA monthly climate data (AOI-clipped)**:

```bash
python -m eden.fetch chelsa-monthly \
  --vars tas pr \
  --start-year 2011 \
  --end-year 2011
```
  
Use --dry-run to preview URLs and outputs without downloading.  
  
---

## Design Notes  

- Ingestion is intentionally decoupled from spatial analysis and modeling.  
- Remote COG access is used to avoid large downloads.  
- Each module is designed to be runnable and testable in isolation.  
- Higher-level orchestration will be added later only if needed.  
- Shared config utilities are handled in config.py.
  
### CLI Subsystems

EDEN uses separate CLIs per domain:

- `python -m eden.fetch` - Data ingestion
- `python -m eden.geo` - Geospatial processing
- `python -m eden.features` - (planned)
- `python -m eden.model` - (planned)

Global flags (--dry-run, --regions-yaml) go before the subcommand.

### Regions  

*Why ecoregions?*  
Ecoregions are "based on perceived patterns of a combination of causal and integrative factors including land use, land surface form, potential natural vegetation, and soils" (Omernick, 1987). That is to say, they're rough boundaries of ecosystem generalizations. They come in shapefiles. So we use those boundaries to reverse-engineer those generalizations within the ecoregion.  
The goal for later versions is to not rely on ecoregions; think of this step as training wheels.  
  
v0 uses four Level III regions across CONUS: Central California Valley (7), High Plains (25), Western Allegheny Plateau (70), and Southern Florida Coastal Plain (76). These were selected for **contrast between regions** in the initial model build.  

---

## Data Sourcing  

### Ecoregions  

[EPA Level III Ecoregions of the Continental United States](https://www.epa.gov/eco-research/level-iii-and-iv-ecoregions-continental-united-states)  
The ecoregion data used in v0 can be found in `regions_v0.yaml`.  
These need to be manually downloaded for now.  

Omernik, J. M. (1987). Ecoregions of the Conterminous United States. _Annals of the Association of American Geographers_, _77_(1), 118–125. [https://doi.org/10.1111/j.1467-8306.1987.tb00149.x](https://doi.org/10.1111/j.1467-8306.1987.tb00149.x)  
  
### Soil  

Soil Survey Staff (2025). Gridded National Soil Survey Geographic (gNATSGO) Database for the Conterminous United States. United States Department of Agriculture, Natural Resources Conservation Service. FY2026 official release. [https://nrcs.app.box.com/v/soils]([https://nrcs.app.box.com/v/soils](https://nrcs.app.box.com/v/soils)).  
  
*Note on gNATSGO data*: unlike climate and landcover, which can be retrieved using the fetch CLI in `src/ingest/`, gNATSGO data must be retrieved manually via Box. The .7z file can be found at the link in this citation.  
  
### Climate  

Karger, D. N., Brun, P., Zilker, F. (2025). CHELSA-monthly climate data at high resolution. EnviDat. [https://www.doi.org/10.16904/envidat.686]([https://www.doi.org/10.16904/envidat.686](https://www.doi.org/10.16904/envidat.686)).  
  
### Landcover  
  
U.S. Geological Survey (USGS) (2024). Annual NLCD Collection 1 Science Products: U.S. Geological Survey data release, [https://doi.org/10.5066/P94UXNTS](https://doi.org/10.5066/P94UXNTS).  
  
The soil, climate, and landcover metadata for v0 can be found in `sources.yaml`.  
