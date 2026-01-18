#!/usr/bin/python3

"""
validate_features.py

##### Goal
- QA!
- Check: 
	- are values within plausible ranges?
	- Is there missing data? 
	- Anomalies? 
##### Examples
- missingness rates
- impossible values (negative precip, NDVI > 1, etc.)
- distribution sanity (exploding variance, constant features)
- temporal alignment errors
- leakage checks (feature timestamp > target timestamp)
"""