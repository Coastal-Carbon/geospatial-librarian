"""
Pleiades Imagery — Data Engine Access Recipes

Pleiades (Airbus Defence and Space) multispectral imagery is accessed through
Hum's private STAC FastAPI catalog. This file contains code snippets for common
Data Engine workflows using Pleiades data.

Key facts:
  - catalog_id: 'stac-fastapi'
  - collection_id: 'pleiades'
  - 6 bands at 1m resolution: Coastal Blue, Blue, Green, Red, Veg Red Edge, NIR
  - Commercial data — only Hum's licensed holdings are available
"""

from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import (
    CollectionInput,
    ObservationType,
    SOURCE_INFO,
)

# ---------------------------------------------------------------------------
# 1. Basic CollectionInput — all bands at default 1m resolution
# ---------------------------------------------------------------------------

pleiades_all_bands = CollectionInput(
    collection_name=CollectionName.PLEIADES,
)

# The defaults are pulled from SOURCE_INFO automatically:
#   band_ids: ('Coastal Blue', 'Blue', 'Green', 'Red', 'Vegetation Red Edge', 'Near-Infrared')
#   resolution: 1.0

# ---------------------------------------------------------------------------
# 2. Select specific bands (e.g., RGB + NIR only)
# ---------------------------------------------------------------------------

pleiades_rgb_nir = CollectionInput(
    collection_name=CollectionName.PLEIADES,
    band_ids=('Blue', 'Green', 'Red', 'Near-Infrared'),
)

# ---------------------------------------------------------------------------
# 3. Select vegetation-focused bands (Red, Red Edge, NIR for NDRE)
# ---------------------------------------------------------------------------

pleiades_vegetation = CollectionInput(
    collection_name=CollectionName.PLEIADES,
    band_ids=('Red', 'Vegetation Red Edge', 'Near-Infrared'),
)

# ---------------------------------------------------------------------------
# 4. Override resolution (e.g., resample to 2m to match another source)
# ---------------------------------------------------------------------------

pleiades_2m = CollectionInput(
    collection_name=CollectionName.PLEIADES,
    resolution=2.0,
)

# ---------------------------------------------------------------------------
# 5. Inspect SOURCE_INFO for Pleiades
# ---------------------------------------------------------------------------

pleiades_info = SOURCE_INFO[CollectionName.PLEIADES]
# Returns:
# {
#     'band_ids': ['Coastal Blue', 'Blue', 'Green', 'Red', 'Vegetation Red Edge', 'Near-Infrared'],
#     'band_names': ['coastal-blue', 'blue', 'green', 'red', 'vegetation-red-edge-1', 'near-infrared'],
#     'requester_pays': False,
#     'resolution': 1.0,
# }

# ---------------------------------------------------------------------------
# 6. ObservationType enum members for Pleiades bands
# ---------------------------------------------------------------------------

pleiades_observation_types = [
    ObservationType.PLEIADES_COASTAL_BLUE,        # band index 0
    ObservationType.PLEIADES_BLUE,                 # band index 1
    ObservationType.PLEIADES_GREEN,                # band index 2
    ObservationType.PLEIADES_RED,                  # band index 3
    ObservationType.PLEIADES_VEGETATION_RED_EDGE_1,  # band index 4
    ObservationType.PLEIADES_NEAR_INFRARED,        # band index 5
]

# ---------------------------------------------------------------------------
# 7. Multi-source project: Pleiades + Sentinel-2
# ---------------------------------------------------------------------------
# Combines Pleiades VHR with Sentinel-2 for temporal density and SWIR bands.

multi_source_inputs = (
    CollectionInput(
        collection_name=CollectionName.PLEIADES,
    ),
    CollectionInput(
        collection_name=CollectionName.SENTINEL2,
        catalog_filters={'eo:cloud_cover': {'lt': 5}},
    ),
)

# ---------------------------------------------------------------------------
# 8. Full project definition example
# ---------------------------------------------------------------------------
# This shows how Pleiades fits into a complete Data Engine project workflow.

from datetime import datetime, timezone

from hum_ai.data_engine.ingredients import ProjectDefinition, Range

# Define an H3 cell for the area of interest (example: resolution 5 cell)
h3_cell_id = '852a100bfffffff'  # replace with your actual H3 cell

project_definition = ProjectDefinition(
    name='Pleiades VHR Analysis',
    description='High-resolution feature extraction using Pleiades multispectral imagery',
    collection_inputs=(
        CollectionInput(
            collection_name=CollectionName.PLEIADES,
        ),
    ),
    region=h3_cell_id,
    time_range=Range(
        min=datetime(2023, 1, 1, tzinfo=timezone.utc),
        max=datetime(2024, 1, 1, tzinfo=timezone.utc),
    ),
)

# ---------------------------------------------------------------------------
# 9. Checking data holdings for Pleiades
# ---------------------------------------------------------------------------
# Use the catalog search to discover what Pleiades scenes exist for an area.

from hum_ai.data_engine.catalog.search import search

# The search function queries Hum's internal STAC FastAPI for the 'pleiades'
# collection. Only scenes that Hum has ingested will be returned.

# ---------------------------------------------------------------------------
# 10. COLLECTION_BAND_MAP reference — maps band index to ObservationType
# ---------------------------------------------------------------------------

from hum_ai.data_engine.ingredients import COLLECTION_BAND_MAP

pleiades_band_map = COLLECTION_BAND_MAP[CollectionName.PLEIADES]
# Returns:
# {
#     0: ObservationType.PLEIADES_COASTAL_BLUE,
#     1: ObservationType.PLEIADES_BLUE,
#     2: ObservationType.PLEIADES_GREEN,
#     3: ObservationType.PLEIADES_RED,
#     4: ObservationType.PLEIADES_VEGETATION_RED_EDGE_1,
#     5: ObservationType.PLEIADES_NEAR_INFRARED,
# }
