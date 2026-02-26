"""
HWSD2 Soils -- Data Engine Recipe
==================================

Demonstrates how to load Harmonized World Soil Database v2 (HWSD2) soil
properties using the Data Engine's ancillary data framework.

HWSD2 is a classified raster with a CSV lookup table:
  - HWSD2_RASTER.tif: integer soil mapping unit (SMU) codes
  - HWSD2_LAYERS.csv: ~408,000 rows mapping SMU IDs to 48 soil attributes

The Data Engine extracts four properties:
  sand (%)  |  clay (%)  |  organic_carbon (g/kg)  |  total_nitrogen (g/kg)
"""

from __future__ import annotations

import h3
import pandas as pd

from hum_ai.data_engine.ancillary.soils import METADATA, SoilsAncillaryData


# ---------------------------------------------------------------------------
# 1. Inspect HWSD2 metadata
# ---------------------------------------------------------------------------

print("HWSD2 Metadata:")
print(f"  S3 raster:       {METADATA['s3_raster_path']}")
print(f"  S3 lookup table: {METADATA['s3_table_path']}")
print(f"  Default H3 res:  {METADATA['default_h3_resolution']}")
print(f"  Output columns:  {METADATA['output_columns']}")
print(f"  Is temporal:     {METADATA['is_temporal']}")
print()
print("Units:")
for col, unit in METADATA['units'].items():
    print(f"  {col}: {unit}")


# ---------------------------------------------------------------------------
# 2. Basic usage -- summarize soil properties for a set of H3 cells
# ---------------------------------------------------------------------------

# Example: generate H3 cells covering a small area in Iowa (agricultural land)
# H3 resolution 8 gives cells of ~0.74 km2, appropriate for ~1 km HWSD2 data
iowa_lat, iowa_lng = 42.0, -93.5
example_cell = h3.latlng_to_cell(iowa_lat, iowa_lng, res=8)
h3_cells = list(h3.grid_disk(example_cell, k=2))  # center cell + 2 rings

print(f"\nExample: {len(h3_cells)} H3 cells around ({iowa_lat}, {iowa_lng})")

soils = SoilsAncillaryData()
result = soils.summarize_from_cells(h3_cells)

print("\nSoil properties:")
print(result.to_string(index=False))


# ---------------------------------------------------------------------------
# 3. Using summarize_from_item -- get soils for a STAC scene footprint
# ---------------------------------------------------------------------------

# If you have a STAC item ID, you can get soil data for its footprint:
#
#   soils = SoilsAncillaryData()
#   result = soils.summarize_from_item(item_id='my-stac-item-id', h3_level=8)
#
# This retrieves the item geometry from the STAC database, generates H3
# cells covering that geometry, and then calls summarize_from_cells().


# ---------------------------------------------------------------------------
# 4. Accessing the full lookup table for additional attributes
# ---------------------------------------------------------------------------

def load_full_hwsd2_table() -> pd.DataFrame:
    """Load the complete HWSD2 lookup table with all 48 attributes.

    Use this when you need attributes beyond the four that the Data Engine
    extracts by default (sand, clay, organic_carbon, total_nitrogen).
    """
    df = pd.read_csv(METADATA['s3_table_path'], low_memory=False)
    return df


# Uncomment to inspect:
# full_table = load_full_hwsd2_table()
# print(f"\nFull table shape: {full_table.shape}")
# print(f"Available columns:\n  {full_table.columns.tolist()}")


# ---------------------------------------------------------------------------
# 5. Derived quantities -- soil texture class and carbon stock
# ---------------------------------------------------------------------------

def soil_texture_class(sand: float, clay: float) -> str:
    """Classify soil texture using the USDA texture triangle (simplified).

    Args:
        sand: Sand content in percent (0-100).
        clay: Clay content in percent (0-100).

    Returns:
        USDA soil texture class name.
    """
    silt = 100.0 - sand - clay
    if sand >= 85 and clay < 10:
        return "sand"
    elif sand >= 70 and clay < 20:
        return "loamy sand"
    elif clay >= 40 and silt < 40:
        return "clay"
    elif clay >= 40 and sand < 45:
        return "silty clay"
    elif clay >= 27 and sand >= 20 and sand < 45:
        return "clay loam"
    elif silt >= 80:
        return "silt"
    elif silt >= 50 and clay >= 12 and clay < 27:
        return "silt loam"
    elif sand >= 52 and clay < 20:
        return "sandy loam"
    elif clay >= 20 and clay < 35 and silt >= 28 and sand < 52:
        return "loam"
    else:
        return "loam"


def carbon_stock_tonnes_per_ha(
    organic_carbon_g_per_kg: float,
    bulk_density_g_per_cm3: float,
    layer_thickness_cm: float,
    gravel_fraction: float = 0.0,
) -> float:
    """Estimate soil organic carbon stock in tonnes per hectare.

    Args:
        organic_carbon_g_per_kg: Organic carbon concentration from HWSD2.
        bulk_density_g_per_cm3: Bulk density (available in full lookup table).
        layer_thickness_cm: Depth of the soil layer in cm.
        gravel_fraction: Volume fraction of coarse fragments (0 to 1).

    Returns:
        Carbon stock in tonnes C per hectare.
    """
    # Convert g/kg to fraction
    oc_fraction = organic_carbon_g_per_kg / 1000.0
    # bulk_density in g/cm3 = tonnes/m3
    # layer_thickness in cm = m / 100
    # 1 hectare = 10,000 m2
    stock = (
        oc_fraction
        * bulk_density_g_per_cm3  # tonnes / m3
        * (layer_thickness_cm / 100.0)  # m
        * 10_000  # m2 / ha
        * (1 - gravel_fraction)
    )
    return stock
