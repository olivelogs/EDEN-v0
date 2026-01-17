#!/usr/bin/python3

"""
# perturb_features.py

# *how signals become stress/events*


Scenarios, for things like:
- Data augmentation (add noise for robustness) - with restraint, for now
- Intervention simulation (change temp by +2°C, see what happens)
- Sensitivity testing (which features matter most?)
##### Goals
- Translate “a change in variable” into a small set of region-relative stress signals. 
- The model should learn relationships like pr↓ → landcover change, 
	- and know whether pr↓ is a mild wobble or a real constraint violation
- Consume climate + productivity inputs
- apply region-aware normalization
- emit event-level or stress-level features
- minimum needs for a perturbance definition:
	1. baseline (what “normal” means here)
	2. relative scale (z-score/percentile/return period)
	3. persistence (how long it lasted)
	4. seasonality (when it happened)

##### Concepts & Specific Examples
1. Definitions (declarative) - stress functions
	- “hot extreme day” = Tmax > local 95th percentile for that day-of-year window
	- “cold snap” = Tmin < local 5th percentile
	- “dry spell” = consecutive days with pr below local 20th percentile
	- “meteorological drought proxy” = rolling precip anomaly (30/90/180d) standardized to local history
	- “compound heat-dry” = (T anomaly high) AND (precip anomaly low) for N days
	- "heat wave" = fixed offset to tas
2. Builders (mechanical)
	- given a pixel/region and time series, compute event counts, durations, max intensity, time-since-last, etc.
"""