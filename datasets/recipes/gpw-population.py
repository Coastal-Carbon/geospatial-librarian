"""
GPW Population Density — Data Engine Recipe
============================================

Demonstrates how to use the PopulationAncillaryData class to compute
zonal population density statistics over H3 cells.

GPW v4 (rev11) provides population density in persons per square kilometer
at 30 arc-second (~1km) resolution. Available years: 2000, 2005, 2010, 2015, 2020.

Key difference from imagery collections:
    GPW is an *ancillary* data source — it does not use CollectionInput,
    CollectionName, or STAC catalog search. Instead, it reads static
    GeoTIFFs from S3 and computes zonal statistics per H3 cell.

Source:
    S3: s3://cc-dataocean/population/gpw/gpw_v4_population_density_rev11_{year}_30_sec.tif
    Module: hum_ai.data_engine.ancillary.population
"""

import logging

import h3
import pandas as pd

from hum_ai.data_engine.ancillary.population import PopulationAncillaryData

logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# 1. Instantiate the PopulationAncillaryData class
# ---------------------------------------------------------------------------
# No arguments required — S3 paths, years, and default H3 resolution are
# configured in the module-level METADATA dictionary.

population = PopulationAncillaryData()

print("PopulationAncillaryData configuration:")
print(f"  S3 path template: {population.s3_path}")
print(f"  Active years:     {population.years}")
print(f"  Default H3 res:   {population.default_h3_resolution}")
print(f"  Output columns:   {population.output_columns}")
print(f"  Temporal:         {population.is_temporal}")


# ---------------------------------------------------------------------------
# 2. Summarize population density for a list of H3 cells
# ---------------------------------------------------------------------------
# Generate H3 cells covering an area of interest. Here we use a single
# parent cell at resolution 5 and get its children at resolution 7.

parent_cell = '852a100bfffffff'  # Example H3 res-5 cell — replace with your AOI
h3_res = 7  # Matches GPW's default_h3_resolution

# Get all resolution-7 children of the parent cell
h3_cells = list(h3.cell_to_children(parent_cell, h3_res))
print(f"\nNumber of H3 res-{h3_res} cells: {len(h3_cells)}")

# Compute zonal statistics (median and range of population density per cell)
result = population.summarize_from_cells(h3_cells)

print(f"\nResult shape: {result.shape}")
print(f"Columns: {list(result.columns)}")
print(f"\nFirst 10 rows:")
print(result.head(10).to_string(index=False))


# ---------------------------------------------------------------------------
# 3. Summarize population density from a STAC item footprint
# ---------------------------------------------------------------------------
# If you have a STAC item ID (e.g., a satellite scene), you can compute
# population density for the H3 cells covering that scene's footprint.
#
# This requires a connection to the STAC database to resolve the item geometry.

# item_id = '20240306_210217_93_2482_3B_AnalyticMS_SR_8b_clip'
# h3_level = 8
# result_from_item = population.summarize_from_item(item_id, h3_level)
# print(result_from_item.head(10))


# ---------------------------------------------------------------------------
# 4. Basic analysis — identify high- and low-density cells
# ---------------------------------------------------------------------------

if not result.empty:
    high_density = result[result['population_median'] > 1000]
    low_density = result[result['population_median'] < 1]
    moderate = result[
        (result['population_median'] >= 1)
        & (result['population_median'] <= 1000)
    ]

    print(f"\nPopulation density summary:")
    print(f"  High density (>1000 persons/km2): {len(high_density)} cells")
    print(f"  Moderate (1-1000 persons/km2):    {len(moderate)} cells")
    print(f"  Low density (<1 person/km2):      {len(low_density)} cells")

    print(f"\n  Overall median: {result['population_median'].median():.1f} persons/km2")
    print(f"  Overall max:    {result['population_median'].max():.1f} persons/km2")
    print(f"  Overall min:    {result['population_median'].min():.1f} persons/km2")


# ---------------------------------------------------------------------------
# 5. Database ingestion
# ---------------------------------------------------------------------------
# To persist population summaries in the ancillary database:

# from hum_ai.data_engine.database.utils import upsert_ancillary_data
# from hum_ai.data_engine.config import get_config
#
# upsert_ancillary_data(result, get_config().db_url, 'population')


# ---------------------------------------------------------------------------
# 6. Combining population with other ancillary sources
# ---------------------------------------------------------------------------
# Population density is commonly used alongside land cover and elevation
# data. Each ancillary source follows the same pattern: instantiate the
# class, call summarize_from_cells() with the same H3 cells, and join
# the resulting DataFrames on the 'cell' column.

# from hum_ai.data_engine.ancillary.landcover import LandcoverAncillaryData
#
# landcover = LandcoverAncillaryData()
# lc_result = landcover.summarize_from_cells(h3_cells)
#
# # Join population and land cover on H3 cell ID
# combined = pd.merge(result, lc_result, on='cell', how='inner')
# print(combined.head(10))


# ---------------------------------------------------------------------------
# 7. Understanding the all_touched behavior
# ---------------------------------------------------------------------------
# The PopulationAncillaryData class automatically adjusts the rasterization
# strategy based on the relationship between H3 cell size and GPW pixel size:
#
#   - H3 res <= 7 (default): Cells are larger than GPW pixels.
#     all_touched=False — only pixels whose center falls within the cell.
#
#   - H3 res > 7: Cells are smaller than GPW pixels.
#     all_touched=True — any pixel touching the cell is included.
#     This ensures every cell gets at least one pixel value, but adjacent
#     cells may share the same pixel.
#
# This logic is in summarize_from_cells():
#
#   resolution = h3.get_resolution(h3_cells[0])
#   if resolution > self.default_h3_resolution:
#       all_touched = True
