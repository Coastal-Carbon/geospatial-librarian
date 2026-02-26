"""
University of Delaware Climate Normals — Data Engine Recipe
============================================================

Demonstrates how to load and work with UDel monthly temperature and
precipitation normals using the Data Engine's ancillary data system.

Source: University of Delaware / NOAA PSL
  https://psl.noaa.gov/data/gridded/data.UDel_AirT_Precip.html

S3 location: s3://cc-dataocean/weather/udel/
  air.mon.1981-2010.ltm.v401.nc     (monthly mean temperature, degC)
  precip.mon.1981-2010.ltm.v401.nc  (monthly mean precipitation, cm/month)

Resolution: 0.5 degree (~55 km at equator)
Climatological period: 1981-2010 long-term means
"""

import h3
import numpy as np
import pandas as pd

from hum_ai.data_engine.ancillary.weather import WeatherAncillaryData, METADATA


# ---------------------------------------------------------------------------
# 1. Inspect metadata
# ---------------------------------------------------------------------------

print("UDel Weather Normals METADATA:")
print(f"  Default H3 resolution: {METADATA['default_h3_resolution']}")
print(f"  Is temporal:           {METADATA['is_temporal']}")
print(f"  Output columns:        {METADATA['output_columns'][:5]} ... ({len(METADATA['output_columns'])} total)")
print(f"\n  Units:")
for col, unit in list(METADATA['units'].items())[:3]:
    print(f"    {col}: {unit}")
print(f"    ... ({len(METADATA['units'])} columns total)")


# ---------------------------------------------------------------------------
# 2. Generate H3 cells for a region of interest
# ---------------------------------------------------------------------------

# Example: generate H3 cells around a location in the US Midwest
# (central Iowa — 42.0N, 93.5W)
center_lat, center_lng = 42.0, -93.5
h3_resolution = METADATA['default_h3_resolution']

# Get the H3 cell containing this point and its neighbors
center_cell = h3.latlng_to_cell(center_lat, center_lng, h3_resolution)
# k-ring of 1 gives the center cell plus its 6 immediate neighbors
h3_cells = list(h3.grid_disk(center_cell, 1))

print(f"\nGenerated {len(h3_cells)} H3 cells at resolution {h3_resolution}")
print(f"  Center cell: {center_cell}")
for cell in h3_cells:
    lat, lng = h3.cell_to_latlng(cell)
    print(f"    {cell} -> ({lat:.2f}, {lng:.2f})")


# ---------------------------------------------------------------------------
# 3. Retrieve climate normals for the H3 cells
# ---------------------------------------------------------------------------

weather = WeatherAncillaryData()
result = weather.summarize_from_cells(h3_cells)

print(f"\nResult shape: {result.shape}")
print(f"Columns: {list(result.columns)}")
print(f"\nFirst few rows (temperature columns only):")
temp_cols = ['cell'] + [f'air_{i}' for i in range(1, 13)]
print(result[temp_cols].to_string(index=False))

print(f"\nFirst few rows (precipitation columns only):")
precip_cols = ['cell'] + [f'precip_{i}' for i in range(1, 13)]
print(result[precip_cols].to_string(index=False))


# ---------------------------------------------------------------------------
# 4. Compute derived climate summaries
# ---------------------------------------------------------------------------

def compute_climate_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Compute useful derived climate variables from monthly normals.

    Returns a DataFrame with one row per H3 cell and the following columns:
      - mean_annual_temp: mean of 12 monthly temperatures (degC)
      - temp_range: difference between warmest and coldest months (degC)
      - warmest_month: month number (1-12) of highest temperature
      - coldest_month: month number (1-12) of lowest temperature
      - total_annual_precip_mm: sum of 12 monthly precipitation values (mm)
      - precip_seasonality: coefficient of variation of monthly precip
      - wettest_month: month number (1-12) of highest precipitation
      - driest_month: month number (1-12) of lowest precipitation
    """
    temp_cols = [f'air_{i}' for i in range(1, 13)]
    precip_cols = [f'precip_{i}' for i in range(1, 13)]

    temp_values = df[temp_cols].values
    precip_values = df[precip_cols].values

    # Convert precipitation from cm/month to mm/month
    precip_mm = precip_values * 10

    summary = pd.DataFrame({
        'cell': df['cell'],
        'mean_annual_temp': np.nanmean(temp_values, axis=1),
        'temp_range': np.nanmax(temp_values, axis=1) - np.nanmin(temp_values, axis=1),
        'warmest_month': np.nanargmax(temp_values, axis=1) + 1,
        'coldest_month': np.nanargmin(temp_values, axis=1) + 1,
        'total_annual_precip_mm': np.nansum(precip_mm, axis=1),
        'precip_seasonality': (
            np.nanstd(precip_mm, axis=1) / np.nanmean(precip_mm, axis=1)
        ),
        'wettest_month': np.nanargmax(precip_mm, axis=1) + 1,
        'driest_month': np.nanargmin(precip_mm, axis=1) + 1,
    })
    return summary


climate_summary = compute_climate_summary(result)
print("\nDerived climate summary:")
print(climate_summary.to_string(index=False))


# ---------------------------------------------------------------------------
# 5. Retrieve climate normals from a STAC item footprint
# ---------------------------------------------------------------------------

# If you have a STAC item ID, you can get climate data for its footprint
# directly. This uses the base class summarize_from_item() method, which
# extracts the item geometry, generates H3 cells, and calls
# summarize_from_cells().
#
# Example (requires STAC database access):
#
#   item_id = '20240319_201452_87_24c2_3B_AnalyticMS_SR_8b_clip'
#   h3_level = 8
#   result = weather.summarize_from_item(item_id, h3_level)
#
# Note: using H3 level 8 here means many cells will share the same
# climate values since the weather grid is much coarser (~55 km) than
# H3 level 8 cells (~460m edge length). This is expected — the climate
# context is uniform across a typical satellite scene.


# ---------------------------------------------------------------------------
# 6. Combine climate data with other ancillary sources
# ---------------------------------------------------------------------------

# Climate normals are typically used alongside other ancillary data to build
# a complete environmental characterization. Example workflow:
#
#   from hum_ai.data_engine.ancillary.weather import WeatherAncillaryData
#   from hum_ai.data_engine.ancillary.landcover import LandcoverAncillaryData
#   from hum_ai.data_engine.ancillary.soils import SoilsAncillaryData
#
#   weather = WeatherAncillaryData()
#   landcover = LandcoverAncillaryData()
#   soils = SoilsAncillaryData()
#
#   weather_df = weather.summarize_from_cells(h3_cells)
#   landcover_df = landcover.summarize_from_cells(h3_cells)
#   soils_df = soils.summarize_from_cells(h3_cells)
#
#   # Merge all ancillary data on the H3 cell index
#   combined = weather_df.merge(landcover_df, on='cell')
#   combined = combined.merge(soils_df, on='cell')
