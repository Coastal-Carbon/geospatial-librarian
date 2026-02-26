# WorldView Imagery — Usage Recipes

Practical recipes for working with Maxar WorldView imagery through Hum's
data engine. These examples assume you have access to Hum's STAC FastAPI
catalog and the `hum_ai.data_engine` library.

## Collection Details

| Property         | Value                                                  |
|------------------|--------------------------------------------------------|
| Collection ID    | `worldview`                                            |
| STAC Catalog     | `stac-fastapi` (Hum internal)                          |
| Enum             | `CollectionName.WORLDVIEW`                             |
| Bands            | 8 multispectral (~1.84m native, ~2.0m product)         |
| Panchromatic     | ~0.5m (separate asset)                                 |
| Data type        | `uint16`                                               |
| Missing value    | `0`                                                    |

## Band Reference

| Band ID            | Name             | Wavelength (nm) | GSD (m) |
|--------------------|------------------|-----------------|---------|
| Coastal Blue       | Coastal Blue     | 425             | 1.84    |
| Blue               | Blue             | 480             | 1.84    |
| Green              | Green            | 545             | 1.84    |
| Yellow             | Yellow           | 610             | 1.84    |
| Red                | Red              | 660             | 1.84    |
| Red Edge           | Red Edge         | 730             | 1.84    |
| Near-Infrared 1    | Near-Infrared 1  | 835             | 1.84    |
| Near-Infrared 2    | Near-Infrared 2  | 950             | 1.84    |

## Recipe 1: Search and Load WorldView Imagery

Search for available WorldView scenes in your area of interest and load
the multispectral bands.

```python
from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import SOURCE_INFO, CollectionInput

# Define your collection input — all 8 MS bands at native resolution
wv_input = CollectionInput(
    collection_name=CollectionName.WORLDVIEW,
    # defaults to all 8 bands and 1.84m resolution from SOURCE_INFO
)

# Or select specific bands
wv_rgb = CollectionInput(
    collection_name=CollectionName.WORLDVIEW,
    band_ids=('Red', 'Green', 'Blue'),
    resolution=2.0,
)
```

## Recipe 2: NDVI with WorldView's Dual NIR Bands

WorldView has two NIR bands. NIR1 (835nm) is comparable to Sentinel-2's
B08 and is the standard choice for NDVI. NIR2 (950nm) is less affected
by atmospheric water vapor and can be more robust in humid conditions.

```python
import numpy as np

def worldview_ndvi(red: np.ndarray, nir1: np.ndarray) -> np.ndarray:
    """Standard NDVI using WorldView Red and NIR1 bands.

    Args:
        red: Red band (660nm) as float array
        nir1: Near-Infrared 1 band (835nm) as float array

    Returns:
        NDVI array with values in [-1, 1]
    """
    red = red.astype(np.float32)
    nir1 = nir1.astype(np.float32)
    return np.where(
        (nir1 + red) > 0,
        (nir1 - red) / (nir1 + red),
        np.nan,
    )

def worldview_ndvi_robust(red: np.ndarray, nir2: np.ndarray) -> np.ndarray:
    """NDVI using NIR2 — more robust under humid/hazy conditions.

    NIR2 (950nm) is less affected by water vapor absorption than NIR1.
    Values will differ slightly from standard NDVI due to the different
    wavelength. Do not mix NIR1-NDVI and NIR2-NDVI in the same analysis.

    Args:
        red: Red band (660nm) as float array
        nir2: Near-Infrared 2 band (950nm) as float array

    Returns:
        NDVI array with values in [-1, 1]
    """
    red = red.astype(np.float32)
    nir2 = nir2.astype(np.float32)
    return np.where(
        (nir2 + red) > 0,
        (nir2 - red) / (nir2 + red),
        np.nan,
    )
```

## Recipe 3: Yellow Band — Vegetation Stress Detection

The Yellow band (~610nm) is unique to WorldView among VHR satellites.
It sits between Red and Green and is sensitive to yellowing/chlorosis
in vegetation, making it useful for detecting vegetation stress before
it becomes visible in standard RGB.

```python
import numpy as np

def yellowness_index(green: np.ndarray, yellow: np.ndarray, red: np.ndarray) -> np.ndarray:
    """Normalized Yellow index for detecting vegetation senescence/stress.

    Higher values indicate more yellowness (potential stress or senescence).

    Args:
        green: Green band (545nm) as float array
        yellow: Yellow band (610nm) as float array
        red: Red band (660nm) as float array

    Returns:
        Yellowness index array
    """
    green = green.astype(np.float32)
    yellow = yellow.astype(np.float32)
    red = red.astype(np.float32)
    return np.where(
        (green + red) > 0,
        (2.0 * yellow - green - red) / (green + red),
        np.nan,
    )
```

## Recipe 4: Coastal and Shallow Water Analysis

The Coastal Blue band (~425nm) penetrates shallow water more effectively
than standard blue. Combined with the other bands, it enables basic
bathymetric estimation in clear water.

```python
import numpy as np

def stumpf_ratio_bathymetry(
    coastal_blue: np.ndarray,
    green: np.ndarray,
    m0: float = 0.0,
    m1: float = 1.0,
) -> np.ndarray:
    """Stumpf et al. (2003) log-ratio bathymetry estimate.

    This is a relative depth estimate that must be calibrated against
    known depth points. Only valid in clear, shallow water (<20-25m
    depending on water clarity).

    Args:
        coastal_blue: Coastal Blue band (425nm) as float array
        green: Green band (545nm) as float array
        m0: Calibration offset (from regression against known depths)
        m1: Calibration gain (from regression against known depths)

    Returns:
        Relative depth estimate (uncalibrated if m0=0, m1=1)
    """
    coastal_blue = coastal_blue.astype(np.float32)
    green = green.astype(np.float32)

    # Avoid log of zero
    cb_safe = np.where(coastal_blue > 0, coastal_blue, np.nan)
    g_safe = np.where(green > 0, green, np.nan)

    ratio = np.log(cb_safe) / np.log(g_safe)
    return m1 * ratio + m0
```

## Recipe 5: Using WorldView with the Data Engine

Full workflow for searching, loading, and processing WorldView data
through the data engine.

```python
from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import (
    SOURCE_INFO,
    CollectionInput,
    COLLECTION_BAND_MAP,
    ObservationType,
)

# Check what bands and resolution are configured
wv_info = SOURCE_INFO[CollectionName.WORLDVIEW]
print(f"Band IDs: {wv_info['band_ids']}")
print(f"Resolution: {wv_info['resolution']}m")
print(f"Data type: {wv_info['dtype']}")
print(f"Missing value: {wv_info['missing_value']}")

# Map band indices to ObservationTypes
wv_band_map = COLLECTION_BAND_MAP[CollectionName.WORLDVIEW]
for idx, obs_type in wv_band_map.items():
    print(f"  Band {idx}: {obs_type.value}")
```

## Recipe 6: Multi-Sensor Fusion — WorldView + Sentinel-2

WorldView provides spatial detail but lacks SWIR bands. Sentinel-2
provides SWIR but at coarser resolution. Combining them gives you both.

```python
from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import CollectionInput

# WorldView for high-resolution visible/NIR
wv_input = CollectionInput(
    collection_name=CollectionName.WORLDVIEW,
    band_ids=('Red', 'Green', 'Blue', 'Near-Infrared 1'),
    resolution=2.0,
)

# Sentinel-2 for SWIR bands (resampled to match WorldView extent)
s2_swir = CollectionInput(
    collection_name=CollectionName.SENTINEL2,
    band_ids=('B11', 'B12'),
    resolution=20.0,  # native SWIR resolution
)

# NOTE: When fusing these datasets:
# 1. Ensure temporal alignment — acquire S2 and WV scenes close in time
# 2. Reproject to a common CRS before analysis
# 3. Keep the SWIR at its native 20m; do not upsample to 2m
#    (it adds no information and inflates data volume)
# 4. Run SWIR-based indices (NBR, NDMI) at 20m, then overlay
#    on the WV basemap for spatial context
```

## Common Gotchas

1. **Missing value is 0** — valid dark pixels (deep water, shadows) can
   also have very low DN values. Apply a cloud/shadow mask before
   interpreting near-zero values as missing data.

2. **DN to reflectance** — raw WorldView data is in digital numbers,
   not surface reflectance. Band ratios (NDVI, etc.) computed on DN
   will be approximate. For rigorous analysis, convert to TOA or
   surface reflectance first.

3. **Resolution mismatch** — native GSD is 1.84m but commercial products
   are commonly resampled to 2.0m. The data engine uses 1.84 as the
   default resolution. Be explicit about what resolution you want when
   creating CollectionInput objects.

4. **No SWIR** — if your workflow requires SWIR bands (burn severity,
   moisture, mineral mapping), WorldView cannot provide them. Pair with
   Sentinel-2 or Landsat for SWIR capability.

5. **Orthorectification** — always verify geometric accuracy against a
   reference dataset. Pair with `cop-dem` for DEM-based orthorectification
   in terrain with relief.
