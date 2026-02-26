# Landsat 8/9 Collection 2 Level-2 via the Data Engine

## Overview

The Data Engine accesses Landsat 8 and 9 Collection 2 Level-2 surface reflectance and surface temperature data from Microsoft Planetary Computer via the STAC API. The STAC collection ID is `landsat-c2-l2`, and it is accessed through the `microsoft-pc` catalog.

Collection 2 Level-2 products are atmospherically corrected to surface reflectance (optical bands) and surface temperature (thermal bands). No additional atmospheric correction is needed for most applications.

## Collection Details

| Property           | Value                                                                 |
|--------------------|-----------------------------------------------------------------------|
| CollectionName     | `CollectionName.LANDSAT`                                              |
| Catalog ID         | `microsoft-pc`                                                        |
| STAC Collection ID | `landsat-c2-l2`                                                       |
| Band IDs           | `blue`, `green`, `red`, `nir08`, `swir16`, `swir22`                   |
| Band Names         | `blue`, `green`, `red`, `nir08`, `swir16`, `swir22`                   |
| Resolution         | 30.0 m                                                                |
| Requester Pays     | `False`                                                               |

Note: The default `SOURCE_INFO` configuration includes 6 optical/SWIR bands. The thermal band (`lwir`) is available in the OlmoEarth format (see below) but is not part of the default band set.

## Key Enums and Classes

The following Data Engine enums and classes are relevant when working with Landsat:

- **`CollectionName.LANDSAT`** (in `hum_ai.data_engine.collections`) -- Identifies the Landsat C2 L2 collection in the Planetary Computer catalog.
- **`CollectionInput`** (in `hum_ai.data_engine.ingredients`) -- Configuration object specifying which collection, bands, and resolution to use.
- **`ObservationType.LANDSAT_*`** (in `hum_ai.data_engine.ingredients`) -- Standard observation type names for each Landsat band.
- **`OlmoEarthModality.LANDSAT`** (in `hum_ai.data_engine.formats.olmo_earth_samples_v1.names`) -- The OlmoEarth modality label for Landsat, with olmo_name `'landsat'`, dtype `uint16`, and 11 bands.

## Band Order

The 6 default bands are indexed in this order (0-based) within the Data Engine:

| Band Index | Band ID  | ObservationType     | Wavelength (nm) | GSD  |
|------------|----------|---------------------|-----------------|------|
| 0          | blue     | `LANDSAT_BLUE`      | 480             | 30m  |
| 1          | green    | `LANDSAT_GREEN`     | 560             | 30m  |
| 2          | red      | `LANDSAT_RED`       | 655             | 30m  |
| 3          | nir08    | `LANDSAT_NIR08`     | 865             | 30m  |
| 4          | swir16   | `LANDSAT_SWIR16`    | 1610            | 30m  |
| 5          | swir22   | `LANDSAT_SWIR22`    | 2200            | 30m  |

Additional observation types exist but are not included in the default 6-band set:

| ObservationType     | Wavelength (nm) | GSD   | Notes                            |
|---------------------|-----------------|-------|----------------------------------|
| `LANDSAT_COASTAL`   | 440             | 30m   | Coastal aerosol band             |
| `LANDSAT_LWIR11`    | 10900           | 100m  | Thermal infrared (surface temp)  |

## Creating a CollectionInput

`CollectionInput` is the primary way to configure a data source in the Data Engine. For Landsat, the defaults pull all 6 optical/SWIR bands at 30m resolution:

```python
from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import CollectionInput

# Default: all 6 bands at 30m
landsat_input = CollectionInput(
    collection_name=CollectionName.LANDSAT,
)

# Explicit band selection and resolution
landsat_input = CollectionInput(
    collection_name=CollectionName.LANDSAT,
    band_ids=('blue', 'green', 'red', 'nir08', 'swir16', 'swir22'),
    resolution=30.0,
)
```

Unlike Sentinel-2, Landsat does not have a default cloud cover filter in `CATALOG_FILTERS`. You can add one manually via the `catalog_filters` parameter if needed, or handle cloud masking in post-processing using the QA_PIXEL band.

## Using Landsat in ImageChips v3

The `ImageChipsV3Configuration` accepts a single `chip_collection_input`. To produce Landsat chips:

```python
from pathlib import Path
from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import CollectionInput
from hum_ai.data_engine.formats.image_chips_v3.config import ImageChipsV3Configuration

config = ImageChipsV3Configuration(
    destination_prefix=Path('/output/landsat_chips'),
    dataset_name='landsat-c2-l2-chips',
    dataset_description='Landsat 8/9 C2 L2 surface reflectance image chips',
    chip_collection_input=CollectionInput(
        collection_name=CollectionName.LANDSAT,
        band_ids=('blue', 'green', 'red', 'nir08', 'swir16', 'swir22'),
        resolution=30.0,
    ),
    chip_size_m=3840.0,  # 3840m / 30m = 128x128 pixels
)
```

This produces 128x128 pixel chips with 6 bands. Adjust `chip_size_m` to control chip dimensions: at 30m resolution, 1920m gives 64x64 pixels, 3840m gives 128x128, and 7680m gives 256x256.

## Using Landsat in OlmoEarth Samples v1

The OlmoEarth format is a multi-modal format that combines multiple data sources into a single dataset. Landsat is included by default in `OlmoEarthSamplesV1Configuration` alongside Sentinel-2 and Sentinel-1:

```python
from hum_ai.data_engine.formats.olmo_earth_samples_v1.config import OlmoEarthSamplesV1Configuration

# The default configuration already includes Landsat
config = OlmoEarthSamplesV1Configuration(
    destination_prefix=Path('/output/olmo_earth'),
    dataset_name='my-olmo-dataset',
    dataset_description='Multi-modal Earth observation dataset',
    # collection_inputs defaults include:
    #   - Sentinel-2 (12 bands at 10m)
    #   - Sentinel-1 (vv, vh at 10m)
    #   - Landsat (7 bands at 10m -- note: resampled from native 30m)
)
```

In the OlmoEarth HDF5 archives, Landsat data is stored under the modality key `'landsat'` (`OlmoEarthModality.LANDSAT`). The OlmoEarth format uses 11 total band slots with the following index mapping:

| OlmoEarth Index | Band ID  |
|-----------------|----------|
| 1               | blue     |
| 2               | green    |
| 3               | red      |
| 4               | nir08    |
| 5               | swir16   |
| 6               | swir22   |
| 9               | lwir     |

The thermal band (`lwir`) is included at index 9 in the OlmoEarth format. Indices 0, 7, 8, and 10 are unused/reserved.

## Using Landsat in a Multi-Source Project

When building a project with multiple data sources, include Landsat as one of several `CollectionInput` entries in a `ProjectDefinition`:

```python
from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import CollectionInput, Range
from datetime import datetime, UTC
from shapely.geometry import box

definition = ProjectDefinition(
    name='Landsat-Sentinel Fusion Project',
    description='Combined Landsat and Sentinel-2 analysis',
    collection_inputs=(
        CollectionInput(
            collection_name=CollectionName.SENTINEL2,
            catalog_filters={'eo:cloud_cover': {'lt': 10}},
        ),
        CollectionInput(
            collection_name=CollectionName.LANDSAT,
            catalog_filters=None,
        ),
    ),
    geometry=box(-71.10, 42.30, -71.00, 42.40),
    time=Range(
        min=datetime(year=2020, month=1, day=1, tzinfo=UTC),
        max=datetime(year=2021, month=1, day=1, tzinfo=UTC),
    ),
    chipsize={CollectionName.SENTINEL2: 256},
)
```

Note: When using Landsat alongside Sentinel-2 at 10m resolution, the 30m Landsat data will be resampled to match. The upsampled pixels do not add spatial detail beyond the native 30m.

## Common Spectral Indices

Landsat's 6 default bands support several widely used spectral indices:

- **NDVI** = (NIR - Red) / (NIR + Red) = (nir08 - red) / (nir08 + red) -- standard vegetation index
- **NDWI** = (Green - NIR) / (Green + NIR) = (green - nir08) / (green + nir08) -- water body detection
- **NBR** = (NIR - SWIR2) / (NIR + SWIR2) = (nir08 - swir22) / (nir08 + swir22) -- burn severity
- **NDMI** = (NIR - SWIR1) / (NIR + SWIR1) = (nir08 - swir16) / (nir08 + swir16) -- moisture index
- **NDBI** = (SWIR1 - NIR) / (SWIR1 + NIR) = (swir16 - nir08) / (swir16 + nir08) -- built-up index

The SWIR bands are Landsat's key differentiator for indices like NBR and NDMI that Sentinel-2 also supports but at 20m rather than 30m.

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
    collections=['landsat-c2-l2'],
    bbox=[-122.5, 37.5, -122.0, 38.0],
    datetime='2023-01-01/2023-06-01',
)

items = list(search.items())
```

## Tips and Gotchas

- **Cloud masking**: Landsat does not have a default cloud cover filter in the Data Engine's `CATALOG_FILTERS`. Use the QA_PIXEL band for cloud, shadow, snow, and water masks. Consider adding `catalog_filters` to your `CollectionInput` for pre-filtering.

- **Resolution mismatch in multi-source projects**: When pairing Landsat (30m) with Sentinel-2 (10m), the Data Engine resamples Landsat to match the reference resolution. This creates 3x3 repeated-value blocks at 10m that do not contain additional spatial information.

- **Thermal band availability**: The thermal infrared band (LWIR, 100m native) is registered in `ObservationType.LANDSAT_LWIR11` and available in the OlmoEarth band index map, but is not included in the default 6-band `SOURCE_INFO` configuration.

- **Band ID naming**: Landsat band IDs in the Data Engine use lowercase descriptive names (`blue`, `green`, `red`, `nir08`, `swir16`, `swir22`) rather than the traditional B2/B3/B4/B5/B6/B7 numbers. These match the Microsoft Planetary Computer STAC asset keys.

- **Landsat is a preferred reference collection**: `CollectionName.preferred_reference_collections()` returns Landsat as the third preference (after Sentinel-2 and Sentinel-1) for use as a reference collection in multi-source projects.
