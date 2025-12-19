# Notes  
  
## Data  

I have not yet pulled the data for soil, climate, landcover. I'll get there.

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

1. ```prep_ecoregions.py```  
in: ```./src/geo/```  

- reads ```regions.yaml``` (scheme/level/code + scheme-agnostic ```uid```)
- loads the EPA CONUS Level III shapefile (```data/raw/boundaries/epa_ecoregions/conus_level3.shp```)
- auto-detects the “Level III code” column
- normalizes codes ("07", 7, "7" all match)
- fixes invalid geometries
- optionally dissolves to 1 row per ecoregion
- writes ```ecoregions_selected.gpkg```
- optionally writes a QA CSV (areas, etc.)

**1.1** ```01_region_selection.ipynb```  
pulls those bounds so i can read them, then use them in regions_v0.yaml for fetch scripts.  

2. ```clip_rasters.py```  
in: ```./src/geo/```

make CHELSA/NLCD/soils stop being enormous

3. ```zonal_stats.py```
in: ```./src/geo/```

turn pixels into features
