# ESA WorldCover in the Data Engine

## Overview

ESA WorldCover is a 10m global land cover classification product derived from
Sentinel-1 and Sentinel-2 imagery. In the Data Engine, it serves two roles:

1. **Direct pixel-level access** via the STAC collection `esa-worldcover` on
   Microsoft Planetary Computer, used in training data pipelines (e.g.,
   OlmoEarth samples).
2. **Ancillary/contextual layer** providing land cover class information
   alongside primary imagery collections.

## Data Engine Registration

ESA WorldCover is registered as a collection and has full band mappings:

```
CollectionName.ESA_WORLDCOVER = 'microsoft-pc', 'esa-worldcover'
```

### Bands (from SOURCE_INFO)

| Band index | band_id           | band_name               | dtype  | Description                              |
|------------|-------------------|-------------------------|--------|------------------------------------------|
| 0          | map               | map                     | uint8  | Land cover classification                |
| 1          | input_quality.1   | s1_observation_count    | int16  | Sentinel-1 observation count per pixel   |
| 2          | input_quality.2   | s2_observation_count    | int16  | Sentinel-2 observation count per pixel   |
| 3          | input_quality.3   | invalid_s2_percentage   | int16  | Percentage of invalid S2 observations    |

### ObservationType Entries

```
ESA_WORLDCOVER_MAP              = 'esa_worldcover_map'
ESA_WORLDCOVER_INPUT_QUALITY_1  = 'esa_worldcover_input_quality_1'
ESA_WORLDCOVER_INPUT_QUALITY_2  = 'esa_worldcover_input_quality_2'
ESA_WORLDCOVER_INPUT_QUALITY_3  = 'esa_worldcover_input_quality_3'
```

## ESA WorldCover Class Values

The ESA WorldCover `map` band uses the following class scheme (these are the
official ESA values, distinct from the IO LULC Annual classes):

| Value | Class                      |
|-------|----------------------------|
| 0     | No Data                    |
| 10    | Tree cover                 |
| 20    | Shrubland                  |
| 30    | Grassland                  |
| 40    | Cropland                   |
| 50    | Built-up                   |
| 60    | Bare / sparse vegetation   |
| 70    | Snow and ice               |
| 80    | Permanent water bodies     |
| 90    | Herbaceous wetland         |
| 95    | Mangroves                  |
| 100   | Moss and lichen            |

## IO LULC Annual LandcoverCategory Enum

The Data Engine also includes an ancillary landcover module at
`hum_ai.data_engine.ancillary.landcover` that works with the **IO LULC Annual**
product (`io-lulc-annual-v02`). This product uses a simplified class scheme
defined in the `LandcoverCategory` enum:

```python
class LandcoverCategory(Enum):
    No_Data           = 0
    Water             = 1
    Trees             = 2
    Flooded_vegetation = 4
    Crops             = 5
    Built_area        = 7
    Bare_ground       = 8
    Snow_ice          = 9
    Clouds            = 10
    Rangeland         = 11
```

Note that these values (0-11) are **not** the same as ESA WorldCover values
(0, 10, 20, ..., 100). The IO LULC Annual product is derived from ESA
WorldCover methodology but uses its own integer encoding.

## How the Data Engine Accesses WorldCover

### Pixel-level access (STAC)

The Data Engine queries ESA WorldCover through Microsoft Planetary Computer's
STAC API using the standard catalog search pattern:

```python
from hum_ai.data_engine.collections import CollectionName
from hum_ai.stac.search import get_client

catalog = get_client(CollectionName.ESA_WORLDCOVER)
search = catalog.search(
    collections=['esa-worldcover'],
    bbox=bbox_of_interest,
)
items = search.item_collection()
```

Items are then loaded as raster arrays using `odc.stac.load()` for integration
into training data pipelines.

### OlmoEarth training data

In the OlmoEarth samples format, WorldCover is included as a single-band
static modality (`OlmoEarthModality.WORLD_COVER`) with dtype `uint8`. It
provides a per-pixel land cover label co-registered with the satellite imagery
chips, enabling models to learn with land cover context.

### H3 zonal summaries (IO LULC Annual)

For H3-based zonal analysis, the `LandcoverAncillaryData` class in
`hum_ai.data_engine.ancillary.landcover` retrieves the IO LULC Annual product
and computes per-cell majority class, unique class count, and optional
histograms. This is used for atlas tagging and contextual metadata.

## Practical Notes

- **Resampling**: Always use nearest-neighbor when reprojecting. The values are
  categorical class labels, not continuous measurements.
- **No-data handling**: The missing value is 0 for the `map` band, which
  coincides with the "No Data" class.
- **Resolution matching**: WorldCover is natively 10m, which aligns perfectly
  with Sentinel-2 visible/NIR bands. No resampling is needed when pairing them
  at 10m resolution.
- **Version selection**: Planetary Computer hosts both v100 (2020) and v200
  (2021). Filter by the `esa_worldcover:product_version` property if a specific
  year is needed.
