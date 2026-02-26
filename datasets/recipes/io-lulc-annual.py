"""
Impact Observatory Annual Land Cover (IO LULC v2) — Data Engine recipe

This script demonstrates how to use the Data Engine to retrieve and analyze
IO LULC annual land cover data for a set of H3 cells.

Dataset: io-lulc-annual-v02 (Microsoft Planetary Computer)
Resolution: 10m categorical, annual (2017-2023)
Classes: Water(1), Trees(2), Flooded_vegetation(4), Crops(5), Built_area(7),
         Bare_ground(8), Snow_ice(9), Clouds(10), Rangeland(11)
"""

from hum_ai.data_engine.ancillary.landcover import (
    LandcoverAncillaryData,
    LandcoverCategory,
)

# ---------------------------------------------------------------------------
# 1. Initialize the ancillary data handler
# ---------------------------------------------------------------------------
lc = LandcoverAncillaryData()

# ---------------------------------------------------------------------------
# 2. Define your area of interest as H3 cells
# ---------------------------------------------------------------------------
# Replace these with your actual H3 cell IDs (resolution 11 recommended)
h3_cells = [
    "8b283470d4b5fff",
    "8b283470d4b1fff",
    "8b283470d4b3fff",
]

# ---------------------------------------------------------------------------
# 3. Get per-cell land cover summaries across multiple years
# ---------------------------------------------------------------------------
# This returns landcover_majority and landcover_unique for each cell and year
df = lc.summarize_from_cells(
    h3_cells=h3_cells,
    date_range="2020-01-01/2023-12-31",
    histogram=True,
)

print("=== Land cover summaries ===")
print(df.to_string(index=False))
print()

# Decode the majority class integer to a human-readable name
df["majority_name"] = df["landcover_majority"].apply(
    lambda v: LandcoverCategory(v).name
)
print("=== With class names ===")
print(df[["cell", "start_time", "majority_name", "landcover_unique"]].to_string(index=False))
print()

# ---------------------------------------------------------------------------
# 4. Get the raw xarray DataArray for custom spatial analysis
# ---------------------------------------------------------------------------
data = lc.get_landcover_array(
    h3_cells=h3_cells,
    date_range="2023-01-01/2023-12-31",
)

print("=== Raw DataArray info ===")
print(f"Shape: {data.shape}")
print(f"Dtype: {data.dtype}")
print(f"CRS:   {data.rio.crs}")
print(f"Nodata: {data.rio.nodata}")
print()

# ---------------------------------------------------------------------------
# 5. Get per-class pixel fractions for a single cell (single year)
# ---------------------------------------------------------------------------
fractions = lc.get_landcover_fractions(
    h3_cell=h3_cells[0],
    histogram=True,
)

print("=== Land cover fractions for single cell ===")
for key, value in fractions.items():
    # Histogram columns are integer class codes; decode them
    try:
        class_name = LandcoverCategory(int(key)).name
        print(f"  {class_name}: {value}")
    except (ValueError, KeyError):
        print(f"  {key}: {value}")
print()

# ---------------------------------------------------------------------------
# 6. Year-over-year change detection
# ---------------------------------------------------------------------------
# Pull all years and find cells whose majority class changed
df_all = lc.summarize_from_cells(
    h3_cells=h3_cells,
    date_range="2017-01-01/2023-12-31",
)

pivot = df_all.pivot_table(
    index="cell",
    columns="start_time",
    values="landcover_majority",
)

changed_mask = pivot.nunique(axis=1) > 1
if changed_mask.any():
    print("=== Cells with land cover change (2017-2023) ===")
    print(pivot[changed_mask])
else:
    print("No land cover changes detected across years for these cells.")
