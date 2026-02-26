# Sentinel-1 RTC via the Data Engine

## Overview

The Data Engine accesses Sentinel-1 RTC (Radiometric Terrain Corrected) SAR backscatter data from Microsoft Planetary Computer via the STAC API. The STAC collection ID is `sentinel-1-rtc`, and it is accessed through the `microsoft-pc` catalog.

## Collection Details

| Property           | Value                                         |
|--------------------|-----------------------------------------------|
| CollectionName     | `CollectionName.SENTINEL1`                    |
| Catalog ID         | `microsoft-pc`                                |
| STAC Collection ID | `sentinel-1-rtc`                              |
| Band IDs           | `vh`, `vv`                                    |
| Band Names         | `VH`, `VV`                                    |
| Resolution         | 10.0 m                                        |
| Data Type          | `float32` (linear power backscatter)          |
| Missing Value      | `-32768.0`                                    |
| Requester Pays     | `False`                                       |

## Key Enums and Classes

The following Data Engine enums and classes are relevant when working with Sentinel-1:

- **`CollectionName.SENTINEL1`** (in `hum_ai.data_engine.collections`) -- Identifies the Sentinel-1 RTC collection in the Planetary Computer catalog.
- **`CollectionInput`** (in `hum_ai.data_engine.ingredients`) -- Configuration object specifying which collection, bands, and resolution to use.
- **`ObservationType.SENTINEL1_VV`** and **`ObservationType.SENTINEL1_VH`** (in `hum_ai.data_engine.ingredients`) -- Standard observation type names for Sentinel-1 polarization channels.
- **`OlmoEarthModality.SENTINEL_1`** (in `hum_ai.data_engine.formats.olmo_earth_samples_v1.names`) -- The OlmoEarth modality label for Sentinel-1, with olmo_name `'sentinel1'`, dtype `float32`, and 2 bands.

## Creating a CollectionInput

`CollectionInput` is the primary way to configure a data source in the Data Engine. For Sentinel-1, the defaults pull both VV and VH bands at 10m resolution:

```python
from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import CollectionInput

# Default: both bands (vh, vv) at 10m
s1_input = CollectionInput(
    collection_name=CollectionName.SENTINEL1,
)

# Explicit band selection and resolution
s1_input = CollectionInput(
    collection_name=CollectionName.SENTINEL1,
    band_ids=('vv', 'vh'),
    resolution=10.0,
)
```

Note that Sentinel-1 does not have a cloud cover filter (unlike Sentinel-2), because SAR is not affected by clouds. The `catalog_filters` parameter can be left as `None` or omitted entirely.

## Using Sentinel-1 in ImageChips v3

The `ImageChipsV3Configuration` accepts a single `chip_collection_input`. To produce Sentinel-1 chips:

```python
from pathlib import Path
from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import CollectionInput
from hum_ai.data_engine.formats.image_chips_v3.config import ImageChipsV3Configuration

config = ImageChipsV3Configuration(
    destination_prefix=Path('/output/sentinel1_chips'),
    dataset_name='sentinel-1-rtc-chips',
    dataset_description='Sentinel-1 RTC SAR backscatter image chips',
    chip_collection_input=CollectionInput(
        collection_name=CollectionName.SENTINEL1,
        band_ids=('vv', 'vh'),
        resolution=10.0,
    ),
    chip_size_m=640.0,        # 640m on the ground = 64 pixels at 10m
)
```

This produces 64x64 pixel chips (640m / 10m) with 2 bands (VV and VH) in float32.

## Using Sentinel-1 in OlmoEarth Samples v1

The OlmoEarth format is a multi-modal format that combines multiple data sources into a single dataset. Sentinel-1 is included alongside Sentinel-2 and Landsat by default in `OlmoEarthSamplesV1Configuration`:

```python
from hum_ai.data_engine.formats.olmo_earth_samples_v1.config import OlmoEarthSamplesV1Configuration

# The default configuration already includes Sentinel-1
config = OlmoEarthSamplesV1Configuration(
    destination_prefix=Path('/output/olmo_earth'),
    dataset_name='my-olmo-dataset',
    dataset_description='Multi-modal Earth observation dataset',
    # collection_inputs defaults include:
    #   - Sentinel-2 (12 bands at 10m)
    #   - Sentinel-1 (vv, vh at 10m)
    #   - Landsat (7 bands at 10m)
)
```

In the OlmoEarth HDF5 archives, Sentinel-1 data is stored under the modality key `'sentinel1'` (`OlmoEarthModality.SENTINEL_1`), with band ordering `vv` at index 0 and `vh` at index 1.

## Using Sentinel-1 in a Multi-Source Project

When building a project with multiple data sources (e.g., for SAR-optical fusion), include Sentinel-1 as one of several `CollectionInput` entries in a `ProjectDefinition`:

```python
from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import CollectionInput, ProjectDefinition, Range
from datetime import datetime, UTC

definition = ProjectDefinition(
    name='SAR-Optical Fusion Project',
    description='Combined Sentinel-1 and Sentinel-2 analysis',
    collection_inputs=(
        CollectionInput(
            collection_name=CollectionName.SENTINEL1,
            catalog_filters=None,  # No cloud filter needed for SAR
        ),
        CollectionInput(
            collection_name=CollectionName.SENTINEL2,
            catalog_filters={'eo:cloud_cover': {'lt': 5}},
        ),
    ),
    region=h3_cell_id,
    geometry=h3_boundary,
    time=Range(
        min=datetime(year=2020, month=1, day=1, tzinfo=UTC),
        max=datetime(year=2023, month=1, day=1, tzinfo=UTC),
    ),
    chipsize={CollectionName.SENTINEL2: 128},
    spatial_ref=utm_crs,
    max_num_views=90,
    time_window=5,
    lazy_load=False,
)
```

## Band Mapping Reference

The `COLLECTION_BAND_MAP` in `ingredients.py` maps band indices to `ObservationType` values:

| Band Index | ObservationType          |
|------------|--------------------------|
| 0          | `SENTINEL1_VV`           |
| 1          | `SENTINEL1_VH`           |

Additional Sentinel-1 observation types exist for other polarization modes and derived products:

- `ObservationType.SENTINEL1_HH` -- HH co-polarization (available in some acquisition modes)
- `ObservationType.SENTINEL1_HV` -- HV cross-polarization (available in some acquisition modes)
- `ObservationType.SENTINEL1_RATIO` -- VV/HH ratio (derived)

## Data Characteristics

- **Values**: Linear power backscatter (gamma-nought). To convert to decibels: `dB = 10 * log10(value)`
- **Typical ranges (dB)**: Water: -20 to -25, Bare soil: -10 to -15, Vegetation: -5 to -12, Urban: 0 to -5
- **No-data sentinel**: `-32768.0` (must be masked before log conversion)
- **Speckle**: Not filtered in the RTC product. Apply spatial or temporal filtering as needed.

## STAC API Access (Low-Level)

For direct STAC access outside the Data Engine framework:

```python
import pystac_client
import planetary_computer

catalog = pystac_client.Client.open(
    'https://planetarycomputer.microsoft.com/api/stac/v1',
    modifier=planetary_computer.sign_inplace,
)

search = catalog.search(
    collections=['sentinel-1-rtc'],
    bbox=[-122.5, 37.5, -122.0, 38.0],
    datetime='2023-01-01/2023-06-01',
)

items = list(search.items())
```
