# EDEN v0

## currently stands for Ecological Digital Earth Network  

This is my toy ecological modeling project. The aim of the project is a high-resolution differentiable ecosystem model constructed of modules. The base model is inspired by EPA ecoregion mapping, using the defining features of the region. Additional features are to be added as modules. Currently, only data for the Continental US (CONUS) is used.  

v0 takes EPA Level III Ecoregion shapefiles to define boundaries. These are layered with climate, soil, and landcover data. Hydrography and elevation data will be added later. This essentially reverse-engineers the ecoregion from publicly available data.  

The inspiration for this project was my own audacity. It's a learn-as-I-go kind of thing. Eventually, I hope to see this become more than a toy project, but something collaborative and... functional.  
  
## Regions  

v0 uses four Level III regions across CONUS: Central California Valley (7), High Plains (25), Western Allegheny Plateau (76), and Southern Florida Coastal Plain (76). These were selected for contrast between regions in the initial model build.  

---

## Scripts  

1. ```prep_ecoregions.py```  

Turn an EPA Level III (CONUS) ecoregions shapefile into a clean, filtered GeoPackage
based on regions listed in a YAML config (regions_v0.yaml).

---

## Data Sourcing  

### Ecoregions  

[EPA Level III Ecoregions of the Continental United States](https://www.epa.gov/eco-research/level-iii-and-iv-ecoregions-continental-united-states)  
  
### Soil  

Soil Survey Staff (2025). Gridded National Soil Survey Geographic (gNATSGO) Database for the Conterminous United States. United States Department of Agriculture, Natural Resources Conservation Service. FY2026 official release. [https://nrcs.app.box.com/v/soils](https://nrcs.app.box.com/v/soils).  
  
### Climate  

Brun, P., Zimmermann, N. E., Hari, C., Pellissier, L., Karger, D. N. (2022). CHELSA-BIOCLIM+ A novel set of global climate-related predictors at kilometre-resolution. EnviDat. [https://www.doi.org/10.16904/envidat.332](https://www.doi.org/10.16904/envidat.332).  
  
### Landcover  

U.S. Geological Survey (USGS) (2024). Annual NLCD Collection 1 Science Products: U.S. Geological Survey data release, [https://doi.org/10.5066/P94UXNTS](https://doi.org/10.5066/P94UXNTS).  
