#!/usr/bin/env python3


# build_features.py 

# *how raw data becomes signals*

##### Goals
# Read interim data (clipped rasters, zonal stats)
# Compute derived features (e.g., temp ranges, seasonal patterns, vegetation indices)
# Align spatial grids
# Aggregate spatially/temporally as needed
# Compute anomalies, deltas, neighborhood stats
# Enforce reproducibility (same inputs → same features)
# merges all extracted tables/output clean feature tables for modeling

##### Specific Examples
# Biological productivity & energy flow
#   Not species. Never species (yet). Flux.
#   NDVI/EVI summaries (mean, max, seasonal amplitude)
#   Phenology markers (green-up timing, senescence timing)
#   Productivity anomalies (delta NDVI vs baseline)
# Spatial context & memory
#	 Places are not independent pixels. 
#	 Neighborhood summaries (e.g., mean NDVI in 5–10 km radius)
#	 Edge density / patchiness metrics
#	 Ecoregion or biome *soft membership* (probabilistic, not hard labels if possible)?