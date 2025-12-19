# EDEN v0

currently stands for **Ecological Digital Earth Network**. It's cute, right? Claude came up with it.  
  
This is my toy ecological modeling project. The aim of the project is a high-resolution differentiable ecosystem model constructed of modules. The base model is inspired by EPA ecoregion mapping, using the defining features of the region. Additional features are to be added as modules. Currently, only data for the Continental US (CONUS) is used.  

v0 takes EPA Level III Ecoregion shapefiles to define boundaries. These are layered with climate, soil, and landcover data. Publicly available data re-constructs a baseline ecoregion's defining features.  

The intention is to feed this into the model. I have concepts of a plan on this front.  

The inspiration for this project was my own audacity. It's a learn-as-I-go kind of thing. Eventually, I hope to see this become more than a toy project, but something collaborative and functional.  

---
  
## Regions  

v0 uses four Level III regions across the Continental United States (CONUS): Central California Valley (7), High Plains (25), Western Allegheny Plateau (76), and Southern Florida Coastal Plain (76). These were selected for contrast between regions in the initial model build.  

---

## Features  

For the sake of simplicity, and for the sake of my laptop's well-being, v0 uses three features: soil (gNATSGO), climate (CHELSA), and landcover (NLCD). I'd *like* to get hydrography in there, and elevation, but this ecosystem is limited by RAM.  

(That said, if she's not wheezing when this is complete, I'm adding those features)  

---

## Scripts  

```prep_ecoregions.py```  

Turn an EPA Level III (CONUS) ecoregions shapefile into a clean, filtered GeoPackage based on regions listed in a YAML config (regions_v0.yaml).  
  
```01_region_selection.ipynb```  

Extracts bounds from the geopackage produced by ```prep_ecoregions.py```.  

---

## Data Sourcing  

### Ecoregions  

[EPA Level III Ecoregions of the Continental United States](https://www.epa.gov/eco-research/level-iii-and-iv-ecoregions-continental-united-states)  
  
### Soil  

**NRCS gNATSGO**  

Soil Survey Staff (2025). Gridded National Soil Survey Geographic (gNATSGO) Database for the Conterminous United States. United States Department of Agriculture, Natural Resources Conservation Service. FY2026 official release. [https://nrcs.app.box.com/v/soils](https://nrcs.app.box.com/v/soils).  

*Note on gNATSGO data*: unlike climate and landcover, which can be retrieved using the fetch CLI in ```src/ingest/```, gNATSGO data must be retrieved manually via Box. The .7z file can be found at the link in this citation.  
  
### Climate  

**CHELSA-monthly**  

Karger, D. N., Brun, P., Zilker, F. (2025). CHELSA-monthly climate data at high resolution. EnviDat. [https://www.doi.org/10.16904/envidat.686](https://www.doi.org/10.16904/envidat.686).  
  
### Landcover  

**NLCD Land Cover**  

U.S. Geological Survey (USGS) (2024). Annual NLCD Collection 1 Science Products: U.S. Geological Survey data release, [https://doi.org/10.5066/P94UXNTS](https://doi.org/10.5066/P94UXNTS).  
  
The soil, climate, and landcover metadata for v0 can be found in ```sources.yaml```.  
