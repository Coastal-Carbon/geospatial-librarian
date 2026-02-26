# Umbra SAR: Data Access and Usage Recipes

## Overview

Umbra SAR imagery is accessed through Hum's internal STAC FastAPI catalog
using the data engine library. The collection ID is `umbra`, and data is
registered as `CollectionName.UMBRA` in the data engine.

Key facts from the data engine configuration:
- **Band IDs**: HH, VV, VH, HV (but >98% of archive is VV only)
- **Observation type used**: `ObservationType.UMBRA_VV` (band index 0)
- **Native resolution**: 1.0m
- **Catalog**: `stac-fastapi`
- **Requester pays**: No

## Recipe 1: Search for Umbra scenes over an AOI

Use the data engine's catalog search to find available Umbra imagery.

```python
from datetime import datetime, timezone
from shapely.geometry import box

from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.catalog.search import get_client

# Define your area of interest as a bounding box (west, south, east, north)
aoi = box(-122.5, 37.7, -122.3, 37.9)  # Example: San Francisco

# Get the STAC client for the stac-fastapi catalog
client = get_client(CollectionName.UMBRA.catalog_id)

# Search for Umbra scenes
results = client.search(
    collections=[CollectionName.UMBRA.id],
    intersects=aoi,
    datetime=[
        datetime(2023, 1, 1, tzinfo=timezone.utc),
        datetime(2024, 1, 1, tzinfo=timezone.utc),
    ],
)

items = list(results.items())
print(f"Found {len(items)} Umbra scenes")
for item in items:
    print(f"  {item.id} | {item.datetime} | {item.properties.get('sar:polarizations')}")
```

## Recipe 2: Load Umbra imagery as a numpy array

Use the data engine's standard raster loading pipeline with Umbra's
configured bands and resolution.

```python
import numpy as np
from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import SOURCE_INFO, CollectionInput

# Create a CollectionInput for Umbra with default settings
# This uses SOURCE_INFO to set band_ids=['HH','VV','VH','HV'] and resolution=1.0
umbra_input = CollectionInput(
    collection_name=CollectionName.UMBRA,
    band_ids=('VV',),  # Override to only load VV (the dominant polarization)
    resolution=1.0,
)

print(f"Collection: {umbra_input.collection_name.id}")
print(f"Bands: {umbra_input.band_ids}")
print(f"Resolution: {umbra_input.resolution}m")
```

## Recipe 3: Multi-source fusion with Sentinel-1 and Sentinel-2

Combine Umbra's high-resolution SAR with free Sentinel data for a
comprehensive analysis.

```python
from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import SOURCE_INFO, CollectionInput

# High-res SAR (1m) -- for detailed structure detection
umbra = CollectionInput(
    collection_name=CollectionName.UMBRA,
    band_ids=('VV',),
)

# Free SAR (10m) -- for broader temporal coverage and dual-pol analysis
sentinel1 = CollectionInput(
    collection_name=CollectionName.SENTINEL1,
)

# Optical multispectral (10m) -- for land cover context
sentinel2 = CollectionInput(
    collection_name=CollectionName.SENTINEL2,
)

# Note: When combining these sources, you will need to:
# 1. Reproject to a common CRS
# 2. Resample to a common resolution (or work at native resolutions separately)
# 3. Align temporally -- find scenes with closest acquisition dates
# 4. Apply terrain correction to SAR data if working in mountainous terrain

inputs = [umbra, sentinel1, sentinel2]
for inp in inputs:
    info = SOURCE_INFO[inp.collection_name]
    print(f"{inp.collection_name.id}: {info['resolution']}m, bands={info['band_ids']}")
```

## Recipe 4: SAR preprocessing -- convert to dB and apply speckle filter

Basic preprocessing steps for Umbra SAR backscatter data.

```python
import numpy as np
from scipy.ndimage import uniform_filter


def to_db(backscatter: np.ndarray) -> np.ndarray:
    """Convert linear backscatter to decibel (dB) scale.

    Args:
        backscatter: SAR backscatter in linear scale (sigma-nought)

    Returns:
        Backscatter in dB scale
    """
    # Avoid log of zero
    safe = np.where(backscatter > 0, backscatter, np.nan)
    return 10.0 * np.log10(safe)


def lee_filter(image: np.ndarray, size: int = 7) -> np.ndarray:
    """Apply a simplified Lee speckle filter.

    Args:
        image: SAR backscatter image (linear scale)
        size: Filter window size (default 7x7)

    Returns:
        Speckle-filtered image
    """
    mean = uniform_filter(image, size=size)
    sqr_mean = uniform_filter(image ** 2, size=size)
    variance = sqr_mean - mean ** 2
    overall_variance = np.var(image)

    # Lee filter weights
    weight = variance / (variance + overall_variance)
    filtered = mean + weight * (image - mean)
    return filtered


# Example usage:
# raw_vv = ...  # loaded Umbra VV backscatter array
# filtered = lee_filter(raw_vv, size=7)
# db_image = to_db(filtered)
```

## Recipe 5: Change detection between two Umbra scenes

Compare two Umbra acquisitions to detect changes.

```python
import numpy as np


def log_ratio_change(before: np.ndarray, after: np.ndarray) -> np.ndarray:
    """Compute log-ratio change detection between two SAR scenes.

    The log-ratio is symmetric and follows a roughly normal distribution,
    making it suitable for thresholding. Values near 0 = no change,
    large positive = increase in backscatter, large negative = decrease.

    Args:
        before: SAR backscatter from earlier date (linear scale)
        after: SAR backscatter from later date (linear scale)

    Returns:
        Log-ratio change map
    """
    # Avoid division by zero
    safe_before = np.where(before > 0, before, np.nan)
    safe_after = np.where(after > 0, after, np.nan)
    return np.log(safe_after / safe_before)


def threshold_changes(
    change_map: np.ndarray,
    n_sigma: float = 2.0,
) -> np.ndarray:
    """Classify changed pixels using a sigma threshold.

    Args:
        change_map: Log-ratio change map
        n_sigma: Number of standard deviations for threshold (default 2.0)

    Returns:
        Classification array: -1 = decrease, 0 = no change, 1 = increase
    """
    mean = np.nanmean(change_map)
    std = np.nanstd(change_map)
    result = np.zeros_like(change_map, dtype=np.int8)
    result[change_map > mean + n_sigma * std] = 1   # increase
    result[change_map < mean - n_sigma * std] = -1  # decrease
    return result


# Example usage:
# scene_t1 = ...  # Umbra VV backscatter, date 1
# scene_t2 = ...  # Umbra VV backscatter, date 2
# change = log_ratio_change(scene_t1, scene_t2)
# classified = threshold_changes(change, n_sigma=2.5)
```

## Notes

- **Resolution alignment**: Umbra is 1m, Sentinel-1 is 10m, Sentinel-2 is 10m.
  When fusing, decide whether to upsample free data or downsample Umbra
  depending on your analysis needs.
- **Polarization**: Umbra is VV-only in practice. Sentinel-1 provides VV+VH
  which enables cross-pol analysis not possible with Umbra alone.
- **Terrain correction**: Use `cop-dem` (30m Copernicus DEM) for Range-Doppler
  terrain correction before analysis in mountainous areas.
- **Data engine integration**: Use `CollectionName.UMBRA` and
  `ObservationType.UMBRA_VV` for type-safe integration with the data engine
  pipeline.
