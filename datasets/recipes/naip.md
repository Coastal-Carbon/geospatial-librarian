# NAIP (National Agriculture Imagery Program) via the Data Engine

## Overview

The Data Engine accesses NAIP imagery from the [Earth Search AWS](https://earth-search.aws.element84.com/v1) STAC catalog, hosted by Element 84 on Amazon S3. The STAC collection ID is `naip`, and it is accessed through the `earth-search-aws` catalog. Data is served as Cloud-Optimized GeoTIFFs (COGs).

**Important: NAIP on Earth Search AWS is a requester-pays bucket.** AWS charges the requesting account for data transfer costs. Ensure your AWS credentials are configured and that you accept the cost implications before running large queries.

## Collection Details

| Property           | Value                                                        |
|--------------------|--------------------------------------------------------------|
| CollectionName     | `CollectionName.NAIP`                                        |
| Catalog ID         | `earth-search-aws`                                           |
| STAC Collection ID | `naip`                                                       |
| Band IDs           | `Red`, `Green`, `Blue`, `NIR`                                |
| Band Names         | `red`, `green`, `blue`, `nir`                                |
| Resolution (Data Engine) | 2.5 m                                                  |
| Native GSD         | 0.6 m (60 cm) for recent acquisitions; 1.0 m for older vintages |
| Data Type          | `uint8` (0-255)                                              |
| Missing Value      | `0`                                                          |
| Requester Pays     | **True**                                                     |

## Resolution: 2.5m vs Native 0.6m

The Data Engine stores NAIP at **2.5 m** resolution, not the native 0.6 m. This is a deliberate downsample to reduce data volume and align more closely with other medium-resolution collections used in multi-source pipelines. At 2.5 m, a 128-pixel chip covers 320 m on the ground -- still fine enough to resolve individual buildings, tree canopy gaps, and field boundaries.

If your application requires the full native 0.6 m resolution, you will need to access NAIP outside the Data Engine (e.g., directly from the STAC API or via USDA's Geospatial Data Gateway).

## Key Enums and Classes

The following Data Engine enums and classes are relevant when working with NAIP:

- **`CollectionName.NAIP`** (in `hum_ai.data_engine.collections`) -- Identifies the NAIP collection in the Earth Search AWS catalog.
- **`CollectionInput`** (in `hum_ai.data_engine.ingredients`) -- Configuration object specifying which collection, bands, and resolution to use.
- **`ObservationType.NAIP_RED`**, **`NAIP_GREEN`**, **`NAIP_BLUE`**, **`NAIP_NIR`** (in `hum_ai.data_engine.ingredients`) -- Standard observation type names for NAIP bands.

## Band Order

The 4 bands are indexed in this order (0-based) within the Data Engine:

| Index | Band ID | Band Name | ObservationType |
|-------|---------|-----------|-----------------|
| 0     | Red     | red       | `NAIP_RED`      |
| 1     | Green   | green     | `NAIP_GREEN`    |
| 2     | Blue    | blue      | `NAIP_BLUE`     |
| 3     | NIR     | nir       | `NAIP_NIR`      |

Note the band order: **Red is band 0, not Blue.** This differs from the typical RGB display order. When composing a true-color image, use bands [2, 1, 0] (Blue, Green, Red).

## Creating a CollectionInput

`CollectionInput` is the primary way to configure a data source in the Data Engine. For NAIP, the defaults pull all 4 bands at 2.5 m resolution:

```python
from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import CollectionInput

# Default: all 4 bands (Red, Green, Blue, NIR) at 2.5m
naip_input = CollectionInput(
    collection_name=CollectionName.NAIP,
)

# Explicit band selection and resolution
naip_input = CollectionInput(
    collection_name=CollectionName.NAIP,
    band_ids=('Red', 'Green', 'Blue', 'NIR'),
    resolution=2.5,
)
```

NAIP does not have cloud cover metadata in its STAC items, so `catalog_filters` should be left as `None` (the default).

## Requester Pays

Because NAIP on Earth Search AWS uses a requester-pays S3 bucket, the Data Engine must pass AWS credentials when reading data. This is handled internally by the catalog client, but you must have valid AWS credentials configured in your environment (via `~/.aws/credentials`, environment variables, or an IAM role). The `requester_pays: True` flag in `SOURCE_INFO` signals the Data Engine to include the necessary request headers.

Be aware that large-scale data pulls (e.g., tiling an entire state) will incur S3 data transfer charges on your AWS account.

## Using NAIP in a Multi-Source Project

NAIP is commonly paired with Sentinel-2 and Sentinel-1 in multi-source projects. Include it as one of several `CollectionInput` entries in a `ProjectDefinition`:

```python
from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import CollectionInput, ProjectDefinition, Range
from datetime import datetime, UTC

definition = ProjectDefinition(
    name='NAIP + Sentinel Multi-Source',
    description='High-res NAIP paired with Sentinel observations',
    collection_inputs=(
        CollectionInput(
            collection_name=CollectionName.NAIP,
            catalog_filters=None,
        ),
        CollectionInput(
            collection_name=CollectionName.SENTINEL2,
            catalog_filters={'eo:cloud_cover': {'lt': 5}},
        ),
        CollectionInput(
            collection_name=CollectionName.SENTINEL1,
            catalog_filters=None,
        ),
    ),
    region=h3_cell_id,
    geometry=h3_boundary,
    time=Range(
        min=datetime(year=2017, month=1, day=1, tzinfo=UTC),
        max=datetime(year=2021, month=1, day=1, tzinfo=UTC),
    ),
    chipsize={CollectionName.SENTINEL2: 128},
    spatial_ref=utm_crs,
    max_num_views=90,
    time_window=5,
    lazy_load=False,
)
```

Because NAIP is acquired infrequently (every 1-3 years per state), use a broad time range to ensure coverage. The `time_window` parameter controls how many days apart two views can be and still be considered coincident -- NAIP will rarely have a same-day match with Sentinel data, so the matched pairs will have larger temporal offsets.

## Using NAIP in ImageChips v3

```python
from pathlib import Path
from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import CollectionInput
from hum_ai.data_engine.formats.image_chips_v3.config import ImageChipsV3Configuration

config = ImageChipsV3Configuration(
    destination_prefix=Path('/data/output/naip_chips'),
    dataset_name='naip-image-chips',
    dataset_description='NAIP RGBN image chips at 2.5m resolution',
    chip_collection_input=CollectionInput(
        collection_name=CollectionName.NAIP,
        band_ids=('Red', 'Green', 'Blue', 'NIR'),
        resolution=2.5,
    ),
    chip_size_m=320.0,  # 320m / 2.5m = 128x128 pixels
)
```

At 2.5 m resolution, a 320 m chip produces 128x128 pixel arrays with 4 bands in uint8.

## Common Spectral Indices

With only RGB + NIR, the available indices are limited but still useful:

- **NDVI** = (NIR - Red) / (NIR + Red) -- vegetation greenness at very high spatial resolution
- **NDWI** = (Green - NIR) / (Green + NIR) -- water body detection

NAIP does not have red edge, SWIR, or thermal bands, so indices like NDRE, NDMI, and NBR are not possible. For those, pair NAIP with Sentinel-2.

## Coverage and Temporal Notes

- **Geographic scope**: Continental United States (CONUS) only. No international coverage.
- **Acquisition timing**: Leaf-on season (roughly June through September), ideal for vegetation analysis but occludes bare ground under tree canopy.
- **Cadence**: Each state is imaged once every 1-3 years on a rotating basis. This is not a time-series dataset -- treat each vintage as a snapshot.
- **Release lag**: Imagery becomes publicly available 6-18 months after acquisition. Not suitable for near-real-time applications.

## Tips

- **Band IDs are case-sensitive**: Use `'Red'`, `'Green'`, `'Blue'`, `'NIR'` (capitalized) when specifying band_ids in CollectionInput.
- **uint8 range**: Values span 0-255. Missing/no-data pixels are 0. Be careful not to confuse valid dark pixels (e.g., deep shadows) with no-data.
- **Pairing with Sentinel-2**: NAIP provides spatial detail; Sentinel-2 provides spectral breadth and temporal density. This is one of the most common multi-source combinations in the Data Engine for US-based projects.
- **AWS costs**: For large-area processing, estimate data transfer costs before running. A single state at 2.5 m resolution is still many gigabytes.
