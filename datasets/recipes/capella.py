"""
Capella Space SAR — Data Engine Recipe

Demonstrates how to configure and work with Capella SAR imagery
using the Hum data engine. Capella provides ~1m resolution X-band
SAR data accessed through Hum's internal STAC FastAPI catalog.

Collection: capella (stac-fastapi)
Primary polarization: HH (>98% of holdings)
Resolution: 1.0m
"""

from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import (
    COLLECTION_BAND_MAP,
    SOURCE_INFO,
    CollectionInput,
    ObservationType,
)

# ---------------------------------------------------------------------------
# 1. Inspect Capella source configuration
# ---------------------------------------------------------------------------

capella_info = SOURCE_INFO[CollectionName.CAPELLA]
print("Capella SOURCE_INFO:")
print(f"  Band IDs:   {capella_info['band_ids']}")
print(f"  Band Names: {capella_info['band_names']}")
print(f"  Resolution: {capella_info['resolution']}m")
print(f"  Requester Pays: {capella_info['requester_pays']}")

# ---------------------------------------------------------------------------
# 2. Inspect ObservationType mapping
# ---------------------------------------------------------------------------

capella_band_map = COLLECTION_BAND_MAP[CollectionName.CAPELLA]
print("\nCapella band index -> ObservationType:")
for idx, obs_type in capella_band_map.items():
    print(f"  Band {idx}: {obs_type.name} ('{obs_type.value}')")

# ---------------------------------------------------------------------------
# 3. Build a CollectionInput for Capella HH
# ---------------------------------------------------------------------------

# HH-only input (recommended — matches >98% of available imagery)
capella_hh_input = CollectionInput(
    collection_name=CollectionName.CAPELLA,
    band_ids=('HH',),
    resolution=1.0,
)
print(f"\nCapella HH CollectionInput:")
print(f"  Collection: {capella_hh_input.collection_name.id}")
print(f"  Bands:      {capella_hh_input.band_ids}")
print(f"  Resolution: {capella_hh_input.resolution}m")

# Default input (all polarizations listed in SOURCE_INFO)
capella_default_input = CollectionInput(
    collection_name=CollectionName.CAPELLA,
)
print(f"\nCapella default CollectionInput:")
print(f"  Collection: {capella_default_input.collection_name.id}")
print(f"  Bands:      {capella_default_input.band_ids}")
print(f"  Resolution: {capella_default_input.resolution}m")

# ---------------------------------------------------------------------------
# 4. Multi-sensor configuration: Capella + Sentinel-2
# ---------------------------------------------------------------------------

# Combine high-res SAR with multispectral optical for complementary analysis.
# SAR provides structural/geometric information; optical provides spectral.
multi_sensor_inputs = [
    CollectionInput(
        collection_name=CollectionName.CAPELLA,
        band_ids=('HH',),
        resolution=1.0,
    ),
    CollectionInput(
        collection_name=CollectionName.SENTINEL2,
        band_ids=('B04', 'B03', 'B02', 'B08'),  # Red, Green, Blue, NIR
        resolution=10.0,
    ),
]

print("\nMulti-sensor configuration:")
for ci in multi_sensor_inputs:
    print(f"  {ci.collection_name.id}: bands={ci.band_ids}, res={ci.resolution}m")

# ---------------------------------------------------------------------------
# 5. Multi-sensor configuration: Capella + Sentinel-1 SAR fusion
# ---------------------------------------------------------------------------

# Combine commercial high-res SAR with free broad-area SAR.
# Sentinel-1 provides time series context; Capella provides detail.
sar_fusion_inputs = [
    CollectionInput(
        collection_name=CollectionName.CAPELLA,
        band_ids=('HH',),
        resolution=1.0,
    ),
    CollectionInput(
        collection_name=CollectionName.SENTINEL1,
        band_ids=('vv', 'vh'),
        resolution=10.0,
    ),
]

print("\nSAR fusion configuration:")
for ci in sar_fusion_inputs:
    print(f"  {ci.collection_name.id}: bands={ci.band_ids}, res={ci.resolution}m")

# ---------------------------------------------------------------------------
# 6. Compare with Umbra (another commercial high-res SAR)
# ---------------------------------------------------------------------------

umbra_info = SOURCE_INFO[CollectionName.UMBRA]
print("\nCapella vs Umbra comparison:")
print(f"  Capella - Resolution: {capella_info['resolution']}m, "
      f"Primary pol: HH, Band IDs: {capella_info['band_ids']}")
print(f"  Umbra   - Resolution: {umbra_info['resolution']}m, "
      f"Primary pol: VV, Band IDs: {umbra_info['band_ids']}")
