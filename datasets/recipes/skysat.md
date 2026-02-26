# SkySat Recipes

Practical patterns for working with Planet SkySat imagery through Hum's
data engine. SkySat is accessed via the internal STAC FastAPI catalog
(`CollectionName.SKYSAT`).

## Quick Reference

| Property | Value |
|---|---|
| Collection enum | `CollectionName.SKYSAT` |
| STAC catalog | `stac-fastapi` |
| STAC collection | `skysat` |
| Bands | Blue, Green, Red, Near-Infrared |
| Band IDs (STAC) | `Blue`, `Green`, `Red`, `Near-Infrared` |
| Band indices | 0=Blue, 1=Green, 2=Red, 3=NIR |
| Working resolution | 1.0m (multispectral) |
| ObservationTypes | `SKYSAT_BLUE`, `SKYSAT_GREEN`, `SKYSAT_RED`, `SKYSAT_NIR` |

## Recipe 1: Search for SkySat Archive Imagery

Search the Hum STAC catalog for existing SkySat scenes over an area of
interest. This is the first step in any SkySat workflow — check what
archive data is available before considering a new tasking order.

```python
from datetime import date
from shapely.geometry import box

from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import CollectionInput, Range
from hum_ai.data_engine.manifest import manifest_from_stac_search

# Configure the SkySat collection input
skysat_input = CollectionInput(
    collection_name=CollectionName.SKYSAT,
    # defaults to all 4 bands: ['Blue', 'Green', 'Red', 'Near-Infrared']
    # defaults to resolution=1.0
)

# Define a date range
date_range = Range(
    min=date(2023, 1, 1),
    max=date(2024, 1, 1),
)

# Search the catalog using manifest_from_stac_search.
# This function requires Scene objects (regions of interest), a chip size
# in meters, collection inputs, and a date range:
#
# manifest = manifest_from_stac_search(
#     scenes=my_scenes,
#     chip_size_m=256.0,
#     collection_inputs=(skysat_input,),
#     date_range=date_range,
# )
```

## Recipe 2: Compute NDVI at Sub-Meter Resolution

SkySat's NIR band enables vegetation analysis at 1m resolution. This is
useful when Sentinel-2's 10m NDVI is too coarse (e.g., individual tree
health, small garden plots, narrow riparian corridors).

```python
import numpy as np

from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import CollectionInput

# Use only the Red and NIR bands for efficiency
skysat_input = CollectionInput(
    collection_name=CollectionName.SKYSAT,
    band_ids=('Red', 'Near-Infrared'),
)

# After loading raster data (e.g., via odc-stac or rasterio):
# red = ...  # Red band array
# nir = ...  # NIR band array

# Compute NDVI
# ndvi = (nir.astype(float) - red.astype(float)) / (nir + red + 1e-10)
```

## Recipe 3: Fuse SkySat with Sentinel-2 for Spectral Depth

SkySat provides spatial detail but only 4 bands. Sentinel-2 provides 13
bands but at 10-20m resolution. Combining them gives you both spatial
detail and spectral richness.

**Strategy:** Use Sentinel-2 for spectral indices that require SWIR or
red edge bands (NDWI, NBR, NDRE), then overlay or fuse with SkySat for
spatial sharpening or fine-scale segmentation.

```python
from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import CollectionInput

# High spatial resolution from SkySat
skysat_input = CollectionInput(
    collection_name=CollectionName.SKYSAT,
    resolution=1.0,
)

# Spectral depth from Sentinel-2
sentinel2_input = CollectionInput(
    collection_name=CollectionName.SENTINEL2,
    band_ids=('B04', 'B05', 'B06', 'B07', 'B08', 'B11', 'B12'),
    resolution=10.0,
)

# Both can be passed to the data engine pipeline as separate collection inputs.
# The data engine will handle resampling to a common grid via the
# SpatialConfig and the resolution parameter on each CollectionInput.
```

## Recipe 4: Multi-Sensor VHR Stack (SkySat + SuperDove)

When you need more spectral bands at high resolution, pair SkySat (4 bands,
1m) with Planet SuperDove (8 bands including red edge, ~3m). Both are
available in Hum's STAC catalog.

```python
from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import CollectionInput

skysat_input = CollectionInput(
    collection_name=CollectionName.SKYSAT,
    resolution=1.0,
)

superdove_input = CollectionInput(
    collection_name=CollectionName.SUPERDOVE,
    # resolution defaults to 1.0 (Data Engine stored resolution)
    # native sensor GSD is ~3m but data is stored oversampled at 1.0m
)

# Use both as inputs to a data engine Plan for multi-sensor analysis
```

## Tips and Gotchas

1. **Check archive availability first.** SkySat coverage is not global or
   systematic. Always search the catalog before building a pipeline — your
   AOI may have zero scenes.

2. **Band ID casing matters.** The STAC band IDs are `'Blue'`, `'Green'`,
   `'Red'`, `'Near-Infrared'` (title case with hyphen). These must match
   exactly when constructing a `CollectionInput` with explicit `band_ids`.

3. **Resolution parameter.** The default resolution in `SOURCE_INFO` is
   `1.0` (meters). If you want to work at a coarser grid (e.g., to match
   Sentinel-2), pass `resolution=10.0` to `CollectionInput`.

4. **No cloud mask band.** Unlike Sentinel-2 (SCL band), SkySat does not
   include a built-in cloud classification layer. You will need to apply
   external cloud masking or manual QA filtering.

5. **Deep learning over pixel-based methods.** At 1m resolution, individual
   pixels represent sub-object features. Traditional pixel-based classifiers
   (e.g., Random Forest on spectral values) tend to produce noisy results.
   Use object-based or deep learning segmentation instead.

6. **ObservationType mapping.** The `COLLECTION_BAND_MAP` maps band indices
   to: `SKYSAT_BLUE` (0), `SKYSAT_GREEN` (1), `SKYSAT_RED` (2),
   `SKYSAT_NIR` (3). Use these when working with the data engine's
   `ObservationType` enum.
