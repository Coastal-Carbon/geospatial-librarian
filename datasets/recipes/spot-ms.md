# SPOT Multispectral — Recipes and Usage Guide

## Overview

SPOT Multispectral imagery is a commercial optical dataset from Airbus Defence
and Space, available through Hum's internal STAC FastAPI catalog. It provides
4 multispectral bands (Blue, Green, Red, NIR) at 6m resolution and a
panchromatic band at 1.5m.

This guide covers common workflows for searching, loading, and analyzing SPOT-MS
data using the data-engine library.

## Quick Reference

| Property       | Value                                       |
|----------------|---------------------------------------------|
| Collection ID  | `spot-ms`                                   |
| Enum           | `CollectionName.SPOT_MS`                    |
| Bands          | B0 (Blue), B1 (Green), B2 (Red), B3 (NIR)  |
| Resolution     | 6.0m (multispectral), 1.5m (panchromatic)   |
| Data type      | `uint16`                                    |
| Missing value  | `0`                                         |
| Catalog        | `stac-fastapi`                              |

## Band Wavelengths

| Band ID | Name  | Wavelength (nm) | GSD  |
|---------|-------|-----------------|------|
| B0      | Blue  | 485             | 6.0m |
| B1      | Green | 565             | 6.0m |
| B2      | Red   | 655             | 6.0m |
| B3      | NIR   | 825             | 6.0m |

## Recipes

### 1. Search for SPOT-MS imagery over an area of interest

Use the data-engine STAC search to find available SPOT-MS scenes. Results are
returned as STAC items with metadata including datetime, geometry, and cloud
cover when available.

```python
from hum_ai.data_engine.collections import CollectionName

collection = CollectionName.SPOT_MS
# collection.catalog_id -> 'stac-fastapi'
# collection.id -> 'spot-ms'
```

### 2. Load all 4 bands

The default band configuration loads all 4 multispectral bands. Band order
follows SOURCE_INFO: Blue (B0), Green (B1), Red (B2), NIR (B3).

```python
from hum_ai.data_engine.ingredients import CollectionInput, SOURCE_INFO

# Default: all bands at native 6m resolution
spot_input = CollectionInput(collection_name=CollectionName.SPOT_MS)

# Verify defaults
info = SOURCE_INFO[CollectionName.SPOT_MS]
print(f"Bands: {info['band_ids']}")       # ['B0', 'B1', 'B2', 'B3']
print(f"Resolution: {info['resolution']}") # 6.0
print(f"dtype: {info['dtype']}")           # uint16
```

### 3. Load a subset of bands

Select specific bands when you only need RGB (for visualization) or a single
band pair (for an index).

```python
# RGB only (no NIR) — for visual composites
spot_rgb = CollectionInput(
    collection_name=CollectionName.SPOT_MS,
    band_ids=('B0', 'B1', 'B2'),
)

# Red and NIR only — for NDVI computation
spot_ndvi_bands = CollectionInput(
    collection_name=CollectionName.SPOT_MS,
    band_ids=('B2', 'B3'),
)
```

### 4. Compute NDVI

Normalized Difference Vegetation Index using the Red (B2) and NIR (B3) bands.
Remember to mask out the nodata value (0) before computing.

```python
import numpy as np

def compute_ndvi(red: np.ndarray, nir: np.ndarray, nodata: int = 0) -> np.ndarray:
    """Compute NDVI from SPOT-MS Red (B2) and NIR (B3) bands.

    Args:
        red: Red band array (B2, 655nm)
        nir: NIR band array (B3, 825nm)
        nodata: Missing value to mask (default 0)

    Returns:
        NDVI array with values in [-1, 1], nodata pixels set to NaN
    """
    mask = (red == nodata) | (nir == nodata)
    red_f = red.astype(np.float32)
    nir_f = nir.astype(np.float32)
    denominator = nir_f + red_f
    ndvi = np.where(denominator > 0, (nir_f - red_f) / denominator, np.nan)
    ndvi[mask] = np.nan
    return ndvi
```

### 5. Compute NDWI (water detection)

Normalized Difference Water Index using Green (B1) and NIR (B3). Positive
values indicate water surfaces.

```python
def compute_ndwi(green: np.ndarray, nir: np.ndarray, nodata: int = 0) -> np.ndarray:
    """Compute NDWI from SPOT-MS Green (B1) and NIR (B3) bands.

    Args:
        green: Green band array (B1, 565nm)
        nir: NIR band array (B3, 825nm)
        nodata: Missing value to mask (default 0)

    Returns:
        NDWI array with values in [-1, 1], nodata pixels set to NaN
    """
    mask = (green == nodata) | (nir == nodata)
    green_f = green.astype(np.float32)
    nir_f = nir.astype(np.float32)
    denominator = green_f + nir_f
    ndwi = np.where(denominator > 0, (green_f - nir_f) / denominator, np.nan)
    ndwi[mask] = np.nan
    return ndwi
```

### 6. Resample to match Sentinel-2

When pairing SPOT-MS with Sentinel-2, you may need to resample to a common
resolution. The choice depends on whether you want to preserve SPOT's higher
resolution (resample S2 to 6m) or standardize to S2's grid (resample SPOT to
10m).

```python
# Load SPOT at Sentinel-2 resolution (10m) for direct stacking
spot_at_s2_res = CollectionInput(
    collection_name=CollectionName.SPOT_MS,
    resolution=10.0,
)

# Or load both at SPOT's native 6m
from hum_ai.data_engine.ingredients import CollectionInput

s2_at_spot_res = CollectionInput(
    collection_name=CollectionName.SENTINEL2,
    band_ids=('B02', 'B03', 'B04', 'B08'),  # Blue, Green, Red, NIR
    resolution=6.0,
)
```

### 7. Observation types for ML pipelines

When building data-engine pipelines that use ObservationType for band mapping,
use the SPOT_MS-specific observation types.

```python
from hum_ai.data_engine.ingredients import ObservationType, COLLECTION_BAND_MAP, CollectionName

# Band index -> ObservationType mapping
band_map = COLLECTION_BAND_MAP[CollectionName.SPOT_MS]
# {0: SPOT_MS_BLUE, 1: SPOT_MS_GREEN, 2: SPOT_MS_RED, 3: SPOT_MS_NIR}

# Get band metadata
from hum_ai.data_engine.ingredients import get_gsd, get_wavelength

for obs_type in [ObservationType.SPOT_MS_BLUE, ObservationType.SPOT_MS_GREEN,
                 ObservationType.SPOT_MS_RED, ObservationType.SPOT_MS_NIR]:
    print(f"{obs_type.name}: GSD={get_gsd(obs_type)}m, wavelength={get_wavelength(obs_type)}nm")
```

## Common Pairing Patterns

### SPOT-MS + Sentinel-2

Use Sentinel-2 for spectral depth (red edge, SWIR bands) and free time series,
while SPOT-MS provides higher spatial resolution (6m vs 10m) for the core
visible/NIR bands. This pairing is useful when you need both fine spatial detail
and spectral indices that require red edge or SWIR bands.

### SPOT-MS + Pleiades

Both are Airbus products. Use SPOT-MS (6m) for broader area coverage at lower
cost, and Pleiades (2m, with red edge) for detailed analysis of specific sites
within the same project. The Airbus ecosystem makes procurement straightforward.

### SPOT-MS + NAIP

Over US sites, pair commercial SPOT-MS with free NAIP (0.6m) for very high
resolution validation. NAIP provides sub-meter detail that SPOT cannot match,
while SPOT provides global coverage and potentially more recent acquisitions.

## Tips and Gotchas

- **Nodata masking is critical.** The missing value is 0 (zero). Always mask
  before computing statistics or indices, or you will get artificially low
  values at image edges and gaps.

- **uint16 overflow.** Band values are stored as uint16. Cast to float32 before
  arithmetic operations to avoid integer overflow in index computations.

- **Archive is not uniform.** Unlike Sentinel-2 which systematically images
  the globe, SPOT archive density varies by location. Always check availability
  for your AOI before planning a workflow around SPOT data.

- **No atmospheric correction guarantee.** Depending on the product level in
  the catalog, data may be TOA reflectance rather than surface reflectance.
  Verify the processing level in STAC item metadata before cross-sensor
  comparison.

- **Pan band is separate.** The 1.5m panchromatic band is not included in the
  spot-ms STAC collection's 4 multispectral bands. Pan-sharpened products
  require additional processing or a different product order.
