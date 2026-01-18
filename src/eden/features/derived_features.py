#!/usr/bin/env python3

"""
derived_features.py

# *how state becomes change*

##### Goals
- simple slopes, simple volatility, simple deltas.
- The ecologically meaningful stuff that isn't directly measured but computed from raw inputs. 
- Not region-semantic like perturbances, but ecologically _meaningful state changes_

##### Specific Examples
- Aridity index (relationship between precip and potential evapotranspiration)
- Growing degree days
- VPD if you ever get that granular
- Soil water balance (precip minus estimated ET given soil properties)
- Slopes over time (5 yr NDVI trend, precip trend)
- Acceleration or volatility measures (warming, precip)
- Regime-shift flags (simple heuristics are fine)
- NDVI trend over 5 years
- precipitation volatility
- acceleration of warming
- landcover transition rates

"""