"""
MODIS NBAR Vegetation Indices — Data Engine Recipe
===================================================

Demonstrates how to compute NDVI percentile statistics from MODIS MCD43A4
NBAR data using the Data Engine ancillary data pipeline.

Unlike imagery collections (Sentinel-2, SuperDove, etc.) which use
CollectionInput, MODIS vegetation indices are accessed through the
ancillary data framework: data is loaded from Microsoft Planetary Computer
via STAC, NDVI is computed from red and NIR bands, and percentile
statistics are aggregated per H3 cell over monthly time windows.

Source module: hum_ai.data_engine.ancillary.indices
STAC collection: modis-43A4-061
Output columns: cell, start_time, end_time, ndvi_min, ndvi_p10, ndvi_p50,
                ndvi_p90, ndvi_max
"""

from hum_ai.data_engine.ancillary.indices import IndicesAncillaryData, METADATA
from hum_ai.data_engine.config import get_config
from hum_ai.data_engine.database.utils import upsert_ancillary_data


# ---------------------------------------------------------------------------
# 1. Inspect the MODIS indices metadata
# ---------------------------------------------------------------------------

print("MODIS NBAR Vegetation Indices — Ancillary Data Source")
print(f"  STAC catalog:         {METADATA['catalog']}")
print(f"  STAC collection:      {METADATA['collection']}")
print(f"  Default H3 resolution: {METADATA['default_h3_resolution']}")
print(f"  Is temporal:          {METADATA['is_temporal']}")
print(f"  Output columns:       {METADATA['output_columns']}")


# ---------------------------------------------------------------------------
# 2. Instantiate the ancillary data source
# ---------------------------------------------------------------------------

indices = IndicesAncillaryData()

print(f"\nIndicesAncillaryData instance:")
print(f"  catalog:    {indices.catalog}")
print(f"  collection: {indices.collection}")
print(f"  H3 res:     {indices.default_h3_resolution}")


# ---------------------------------------------------------------------------
# 3. Define H3 cells and time periods
# ---------------------------------------------------------------------------

# H3 cell IDs at resolution 8 — these identify the spatial units for
# zonal statistics. Each cell is approximately 0.74 km^2.
h3_cells = ['882a30d5b7fffff']

# Monthly time grid IDs — each triggers a separate STAC query and
# NDVI aggregation over that calendar month.
timestamps = ['2020-07', '2020-08']

print(f"\nProcessing {len(h3_cells)} H3 cell(s) x {len(timestamps)} month(s)")
for cell in h3_cells:
    print(f"  Cell: {cell}")
for ts in timestamps:
    print(f"  Month: {ts}")


# ---------------------------------------------------------------------------
# 4. Compute NDVI percentile statistics
# ---------------------------------------------------------------------------

# This single call handles the full pipeline:
#   1. Opens the Planetary Computer STAC catalog (with auto-signing)
#   2. Converts H3 cells to a bounding polygon for spatial search
#   3. For each monthly time window:
#      a. Searches STAC for MODIS items in the bbox and date range
#      b. Filters items to the exact date range (MODIS returns extras)
#      c. Loads Band 1 (Red) and Band 2 (NIR) via odc.stac with Dask
#      d. Computes NDVI = (NIR - Red) / (NIR + Red)
#      e. Runs zonal statistics (min, p10, p50, p90, max) per H3 cell
#      f. Averages across time slices within the month
#   4. Concatenates results across all months

df = indices.summarize_from_cells(h3_cells, timestamps)

print(f"\nResults shape: {df.shape}")
print(f"Columns: {list(df.columns)}")
print(df.to_string(index=False))


# ---------------------------------------------------------------------------
# 5. Store results in the database
# ---------------------------------------------------------------------------

# Upsert writes to the 'modis_indices' table, handling deduplication
# if the same cell + time range already exists.
#
# Uncomment the lines below to write to the database:
#
# db_url = get_config().db_url
# upsert_ancillary_data(df, db_url, 'modis_indices')
# print("\nResults written to 'modis_indices' table.")


# ---------------------------------------------------------------------------
# 6. Interpreting the output
# ---------------------------------------------------------------------------

print("\n--- Interpreting NDVI Percentile Statistics ---")
print("""
Each row represents one H3 cell for one monthly time window.

  ndvi_min  — Minimum NDVI observed (cloud-contaminated or bare soil pixels)
  ndvi_p10  — 10th percentile (low-greenness baseline)
  ndvi_p50  — Median NDVI (representative vegetation condition)
  ndvi_p90  — 90th percentile (peak greenness)
  ndvi_max  — Maximum NDVI observed (densest vegetation moment)

Typical NDVI ranges:
  -0.1 to 0.1  — Water, bare soil, rock, snow
   0.1 to 0.3  — Sparse vegetation, grassland, shrubland
   0.3 to 0.6  — Moderate vegetation (crops, open woodland)
   0.6 to 0.9  — Dense vegetation (forest, healthy cropland)

The spread between p10 and p90 indicates within-month variability:
  - Narrow range (e.g., p10=0.6, p90=0.7): stable, homogeneous vegetation
  - Wide range (e.g., p10=0.1, p90=0.6): mixed land cover or rapid change
""")


# ---------------------------------------------------------------------------
# 7. Low-level STAC access (outside the Data Engine framework)
# ---------------------------------------------------------------------------

# For direct STAC access without the ancillary pipeline:

# import pystac_client
# import planetary_computer
# import odc.stac
#
# catalog = pystac_client.Client.open(
#     'https://planetarycomputer.microsoft.com/api/stac/v1',
#     modifier=planetary_computer.sign_inplace,
# )
#
# search = catalog.search(
#     collections=['modis-43A4-061'],
#     bbox=[-122.5, 37.5, -122.0, 38.0],
#     datetime='2020-07-01/2020-07-31',
# )
#
# items = search.item_collection()
# print(f"Found {len(items)} MODIS items")
#
# # Load as xarray (Dask-backed)
# data = odc.stac.load(
#     items,
#     chunks={'x': 128, 'y': 128},
#     bbox=[-122.5, 37.5, -122.0, 38.0],
# )
#
# # Compute NDVI from Band 1 (Red) and Band 2 (NIR)
# red = data['Nadir_Reflectance_Band1']
# nir = data['Nadir_Reflectance_Band2']
# denom = nir + red
# ndvi = (nir - red).where(denom != 0) / denom.where(denom != 0)
