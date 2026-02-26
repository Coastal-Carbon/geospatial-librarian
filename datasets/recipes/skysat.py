"""
SkySat Recipe — Search and load Planet SkySat imagery from Hum's STAC catalog.

This script demonstrates how to:
  1. Search for SkySat archive imagery over an area of interest
  2. Configure a CollectionInput for the data engine pipeline
  3. Compute NDVI from SkySat's Red and NIR bands

SkySat is a commercial constellation from Planet Labs providing sub-meter
multispectral imagery (Blue, Green, Red, NIR at ~1m resolution). Within the
data engine it is accessed via CollectionName.SKYSAT from the 'stac-fastapi'
catalog.

Prerequisites:
  - Hum platform credentials configured (for STAC FastAPI access)
  - hum_ai.data_engine and hum_ai.stac packages installed
"""

from __future__ import annotations

from datetime import datetime, timezone

from shapely.geometry import Polygon, box

from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import (
    COLLECTION_BAND_MAP,
    SOURCE_INFO,
    CollectionInput,
    ObservationType,
    Range,
)
from hum_ai.data_engine.manifest import manifest_from_stac_search
from hum_ai.data_engine.scene import Scene

# ---------------------------------------------------------------------------
# 1. Inspect SkySat configuration in the data engine
# ---------------------------------------------------------------------------

skysat_info = SOURCE_INFO[CollectionName.SKYSAT]
print("SkySat SOURCE_INFO:")
print(f"  Band IDs:   {skysat_info['band_ids']}")
print(f"  Band names: {skysat_info['band_names']}")
print(f"  Resolution: {skysat_info['resolution']}m")

skysat_band_map = COLLECTION_BAND_MAP[CollectionName.SKYSAT]
print("\nSkySat COLLECTION_BAND_MAP:")
for idx, obs_type in skysat_band_map.items():
    print(f"  Band {idx}: {obs_type.name} -> '{obs_type.value}'")

# ---------------------------------------------------------------------------
# 2. Search the STAC catalog for SkySat scenes
# ---------------------------------------------------------------------------

# Define an area of interest (example: San Francisco waterfront)
aoi: Polygon = box(-122.42, 37.78, -122.38, 37.81)

# Define a date range to search
date_range = Range(
    min=datetime(2023, 6, 1, tzinfo=timezone.utc).date(),
    max=datetime(2023, 12, 31, tzinfo=timezone.utc).date(),
)

# Create a CollectionInput using all default SkySat bands and resolution
skysat_input = CollectionInput(
    collection_name=CollectionName.SKYSAT,
    # band_ids defaults to: ('Blue', 'Green', 'Red', 'Near-Infrared')
    # resolution defaults to: 1.0
)

print(f"\nSearching for SkySat scenes...")
print(f"  AOI bounds: {aoi.bounds}")
print(f"  Date range: {date_range}")
print(f"  Bands:      {skysat_input.band_ids}")
print(f"  Resolution: {skysat_input.resolution}m")

# Execute the catalog search
# manifest_from_stac_search requires Scene objects, a chip size in meters,
# collection inputs, and a date range.
# Example (requires Scene objects from your project configuration):
#
# manifest = manifest_from_stac_search(
#     scenes=my_scenes,
#     chip_size_m=256.0,
#     collection_inputs=(skysat_input,),
#     date_range=date_range,
# )

# ---------------------------------------------------------------------------
# 3. Configure SkySat with a subset of bands (Red + NIR for NDVI)
# ---------------------------------------------------------------------------

skysat_ndvi_input = CollectionInput(
    collection_name=CollectionName.SKYSAT,
    band_ids=('Red', 'Near-Infrared'),
    resolution=1.0,
)

print(f"\nNDVI-only configuration:")
print(f"  Bands:      {skysat_ndvi_input.band_ids}")
print(f"  Resolution: {skysat_ndvi_input.resolution}m")

# ---------------------------------------------------------------------------
# 4. Multi-sensor configuration: SkySat + Sentinel-2
# ---------------------------------------------------------------------------
# Pair SkySat (high spatial resolution, 4 bands) with Sentinel-2
# (moderate resolution, 13 bands) for spectral depth.

sentinel2_input = CollectionInput(
    collection_name=CollectionName.SENTINEL2,
    band_ids=('B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B11', 'B12'),
    resolution=10.0,
)

print("\nMulti-sensor configuration:")
print(f"  SkySat:     {skysat_input.band_ids} @ {skysat_input.resolution}m")
print(f"  Sentinel-2: {sentinel2_input.band_ids} @ {sentinel2_input.resolution}m")

# Both inputs can be passed to the data engine Plan for fusion workflows.
# The data engine will handle searching, loading, and resampling each
# collection independently based on its CollectionInput configuration.
