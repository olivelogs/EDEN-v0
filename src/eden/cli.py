#!/usr/bin/env python3

"""
Docstring for src.eden.cli

cli.py

BAD i do not want to use this yet.

CLI entrypoint eden workflow. Does subparsers.
i.e.
fetch → dispatch to src/ingest/fetch_chelsa_monthly.py, fetch_nlcd.py, check_gnatsgo.py
geo → dispatch to src/geo/prep_ecoregions.py, zonal_stats.py

examples:
python -m eden.cli fetch chelsa-monthly ...
python -m eden.cli geo zonal-stats ...
python -m eden.cli features build ...
python -m eden.cli model baseline-cluster ...

python -m eden.cli fetch chelsa-monthly \
  --vars tas pr \
  --start-year 2011 --end-year 2020 \
  --aoi config

"""
