# Sentinel-2 L2A via the Data Engine

## Overview

The Data Engine accesses Sentinel-2 Level-2A surface reflectance data from Microsoft Planetary Computer via the STAC API. The STAC collection ID is `sentinel-2-l2a`, and it is accessed through the `microsoft-pc` catalog. Sentinel-2 is the preferred reference collection in the Data Engine and serves as the default data source for both ImageChips v3 and OlmoEarth formats.

## Collection Details

| Property           | Value                                                              |
|--------------------|--------------------------------------------------------------------|
| CollectionName     | `CollectionName.SENTINEL2`                                         |
| Catalog ID         | `microsoft-pc`                                                     |
| STAC Collection ID | `sentinel-2-l2a`                                                   |
| Band IDs           | `B01`, `B02`, `B03`, `B04`, `B05`, `B06`, `B07`, `B08`, `B8A`, `B09`, `B11`, `B12` |
| Band Names         | `coastal`, `blue`, `green`, `red`, `red_edge1`, `red_edge2`, `red_edge3`, `nir`, `red_edge4`, `water_vapor`, `swir1`, `swir2` |
| Resolution         | 10.0 m (default; native resolution varies by band: 10m, 20m, 60m) |
| Data Type          | `uint16`                                                           |
| Missing Value      | `0`                                                                |
| Band Thresholds    | `(0, 10_000)` -- reflectance values are scaled by 10,000           |
| Requester Pays     | `False`                                                            |

## Key Enums and Classes

The following Data Engine enums and classes are relevant when working with Sentinel-2:

- **`CollectionName.SENTINEL2`** (in `hum_ai.data_engine.collections`) -- Identifies the Sentinel-2 L2A collection in the Planetary Computer catalog. This is the first entry in `preferred_reference_collections()`, making it the default anchor for chip footprints.
- **`CollectionInput`** (in `hum_ai.data_engine.ingredients`) -- Configuration object specifying which collection, bands, resolution, and catalog filters to use.
- **`ObservationType.SENTINEL2_*`** (in `hum_ai.data_engine.ingredients`) -- Standard observation type names for each Sentinel-2 band, from `SENTINEL2_COASTAL` through `SENTINEL2_SWIR2`.
- **`OlmoEarthModality.SENTINEL_2_L2A`** (in `hum_ai.data_engine.formats.olmo_earth_samples_v1.names`) -- The OlmoEarth modality label for Sentinel-2, with olmo_name `'sentinel2_l2a'`, dtype `uint16`, and 12 bands.

## Cloud Cover Filtering

Sentinel-2 is the only collection in the Data Engine that has default catalog filters defined in `CATALOG_FILTERS`:

```python
CATALOG_FILTERS = {
    CollectionName.SENTINEL2: {
        'eo:cloud_cover': {'lt': 5},
    }
}
```

This means that when using the low-level STAC search, items with 5% or more cloud cover are excluded by default. However, `CATALOG_FILTERS` is a reference constant -- the actual filter applied to a pipeline is set via the `catalog_filters` parameter on `CollectionInput`. Common values used across scripts and configurations:

- `{'eo:cloud_cover': {'lt': 5}}` -- strict, used in OlmoEarth defaults and many scripts
- `{'eo:cloud_cover': {'lt': 10}}` -- moderate, used in some workflow scripts
- `{'eo:cloud_cover': {'lt': 25}}` -- relaxed, used in the ImageChipsV3Configuration default
- Additional filters like `{'s2:nodata_pixel_percentage': {'lte': 2}}` can be combined for stricter quality control

## Creating a CollectionInput

`CollectionInput` is the primary way to configure a data source in the Data Engine. For Sentinel-2, the defaults pull all 12 spectral bands at 10m resolution:

```python
from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import CollectionInput

# Default: all 12 bands at 10m, no catalog filters
s2_input = CollectionInput(
    collection_name=CollectionName.SENTINEL2,
)

# Explicit: select only BGRN bands with cloud filtering
s2_input = CollectionInput(
    collection_name=CollectionName.SENTINEL2,
    band_ids=('B02', 'B03', 'B04', 'B08'),  # Blue, Green, Red, NIR
    resolution=10.0,
    catalog_filters={'eo:cloud_cover': {'lt': 5}},
)
```

Note that Sentinel-2 has bands at multiple native resolutions (10m, 20m, 60m). All bands are resampled to the specified `resolution` during chip creation. The default resolution of 10m matches the native resolution of the B02, B03, B04, and B08 bands.

## Using Sentinel-2 in ImageChips v3

The `ImageChipsV3Configuration` accepts a single `chip_collection_input`. Sentinel-2 is the default collection for this format. To produce Sentinel-2 chips:

```python
from pathlib import Path
from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import CollectionInput
from hum_ai.data_engine.formats.image_chips_v3.config import ImageChipsV3Configuration

# Using the built-in default (Sentinel-2 BGRN at 10m, cloud cover < 25%)
config = ImageChipsV3Configuration(
    destination_prefix=Path('/output/sentinel2_chips'),
    dataset_name='sentinel-2-l2a-chips',
    dataset_description='Sentinel-2 L2A surface reflectance image chips',
)

# Explicit configuration with all 12 bands
config = ImageChipsV3Configuration(
    destination_prefix=Path('/output/sentinel2_chips_12band'),
    dataset_name='sentinel-2-l2a-chips-12band',
    dataset_description='Sentinel-2 L2A 12-band surface reflectance chips',
    chip_collection_input=CollectionInput(
        collection_name=CollectionName.SENTINEL2,
        band_ids=(
            'B02', 'B03', 'B04', 'B08',  # 10m native
            'B05', 'B06', 'B07', 'B8A',  # 20m native (red edge, narrow NIR)
            'B11', 'B12',                  # 20m native (SWIR)
            'B01', 'B09',                  # 60m native (coastal aerosol, water vapor)
        ),
        resolution=10.0,
        catalog_filters={'eo:cloud_cover': {'lt': 5}},
    ),
    chip_size_m=1280.0,  # 128x128 pixels at 10m
)
```

The default `ImageChipsV3Configuration` uses Sentinel-2 with bands `('B02', 'B03', 'B04', 'B08')` at 10m and a cloud cover threshold of 25%. The default chip size is 640m, producing 64x64 pixel chips.

## Using Sentinel-2 in OlmoEarth Samples v1

The OlmoEarth format is a multi-modal format combining multiple data sources. Sentinel-2 is included by default alongside Sentinel-1 and Landsat:

```python
from pathlib import Path
from hum_ai.data_engine.formats.olmo_earth_samples_v1.config import OlmoEarthSamplesV1Configuration

# The default configuration already includes Sentinel-2 (12 bands)
config = OlmoEarthSamplesV1Configuration(
    destination_prefix=Path('/output/olmo_earth'),
    dataset_name='my-olmo-dataset',
    dataset_description='Multi-modal Earth observation dataset',
    # Default collection_inputs include:
    #   - Sentinel-2 (12 bands at 10m, cloud cover < 5%)
    #   - Sentinel-1 (vv, vh at 10m)
    #   - Landsat (7 bands at 10m)
)
```

In the OlmoEarth HDF5 archives, Sentinel-2 data is stored under the modality key `'sentinel2_l2a'` (`OlmoEarthModality.SENTINEL_2_L2A`), with 12 bands. The band ordering in OlmoEarth uses a custom index map (`_SEN2_BAND_ID_TO_IDX`) that places the 10m bands first (B02=0, B03=1, B04=2, B08=3), then 20m bands (B05=4 through B12=9), then 60m bands (B01=10, B09=11).

## Band Mapping Reference

The `COLLECTION_BAND_MAP` in `ingredients.py` maps band indices to `ObservationType` values:

| Band Index | Band ID | ObservationType           | Wavelength | Native Resolution |
|------------|---------|---------------------------|------------|-------------------|
| 0          | B01     | `SENTINEL2_COASTAL`       | 443 nm     | 60m               |
| 1          | B02     | `SENTINEL2_BLUE`          | 490 nm     | 10m               |
| 2          | B03     | `SENTINEL2_GREEN`         | 560 nm     | 10m               |
| 3          | B04     | `SENTINEL2_RED`           | 665 nm     | 10m               |
| 4          | B05     | `SENTINEL2_RED_EDGE1`     | 705 nm     | 20m               |
| 5          | B06     | `SENTINEL2_RED_EDGE2`     | 740 nm     | 20m               |
| 6          | B07     | `SENTINEL2_RED_EDGE3`     | 783 nm     | 20m               |
| 7          | B08     | `SENTINEL2_NIR`           | 842 nm     | 10m               |
| 8          | B8A     | `SENTINEL2_RED_EDGE4`     | 865 nm     | 20m               |
| 9          | B09     | `SENTINEL2_WATER_VAPOR`   | 945 nm     | 60m               |
| 10         | B11     | `SENTINEL2_SWIR1`         | 1610 nm    | 20m               |
| 11         | B12     | `SENTINEL2_SWIR2`         | 2190 nm    | 20m               |

Note: B10 (Cirrus, 1375 nm, 60m) is not included in the default `SOURCE_INFO` band list but does have an `ObservationType.SENTINEL2_CIRRUS` entry for use in specific datasets like Sen1Floods11.

## Data Characteristics

- **Values**: Atmospherically corrected surface reflectance (L2A), scaled by 10,000. A reflectance of 0.15 is stored as 1500.
- **Valid range**: 0 to 10,000 (per `band_thresholds`)
- **No-data sentinel**: `0`
- **Data type**: `uint16`
- **Scene Classification Layer (SCL)**: Available as a separate band for cloud, shadow, water, and vegetation masking (not included in the default band list).

## Spatial and Temporal Configuration

The Data Engine uses separate spatial and temporal configuration objects that pair with the format configuration:

```python
from hum_ai.data_engine.spatial_config import H3CellSpatialConfig, BaseGeometrySpatialConfig
from hum_ai.data_engine.temporal_config import (
    LatestPrecedingTemporalConfig,
    MonthlyMiddleTemporalConfig,
)

# Spatial: using an H3 cell
spatial = H3CellSpatialConfig(h3_cell_id='882ab2590bfffff')

# Spatial: using a polygon or point geometry
from shapely import Point
spatial = BaseGeometrySpatialConfig(geometry=Point(-90, 32))

# Temporal: find the closest item before each key date
from hum_ai.data_engine.temporal_sampling_strategies import LatestPreceding
import datetime as dt
temporal = LatestPrecedingTemporalConfig(
    latest_preceding=LatestPreceding(
        key_dates=(dt.date(2023, 6, 1), dt.date(2023, 9, 1)),
        max_days_before=30,
    )
)

# Temporal: monthly middle (for OlmoEarth pretraining-style sampling)
from hum_ai.data_engine.temporal_sampling_strategies import MonthlyMiddle
temporal = MonthlyMiddleTemporalConfig(
    monthly_middle=MonthlyMiddle(start_year=2020, end_year=2023)
)
```

## CLI Commands

The Data Engine CLI provides commands for planning and executing recipes via `planning_and_execution.py`:

```bash
# Plan and execute locally in one step (requires a JSON config file)
data-engine plan-and-execute-locally --config /path/to/config.json

# Create a recipe (serialize to disk or S3) without executing
data-engine create-and-write-recipe --config /path/to/config.json --recipe-dest-path /path/to/recipe.json

# Execute a previously serialized recipe
data-engine execute-recipe --recipe /path/to/recipe.json
```

The `--config` option accepts a JSON file conforming to the `CompleteConfig` schema, which bundles spatial, temporal, and format configuration. Example JSON config for Sentinel-2 with OlmoEarth format:

```json
{
    "spatial_config": {
        "type": "h3_cell_spatial_config",
        "h3_cell_id": "882ab2590bfffff"
    },
    "temporal_config": {
        "type": "latest_preceding_temporal_config",
        "latest_preceding": {
            "key_dates": ["2023-06-01"],
            "max_days_before": 30
        }
    },
    "format_config": {
        "type": "olmo_earth_samples_v1",
        "destination_prefix": "/tmp/sentinel2_output/",
        "dataset_name": "sentinel2_test_dataset",
        "dataset_description": "Sentinel-2 L2A test"
    }
}
```

## Pipeline Shell Script Example

From `scripts/2025.07.11_run_pipeline.sh`, a pipeline invocation that includes Sentinel-2:

```bash
python src/data_engine/pipeline.py \
    --project_name "test_dataset_2025-07-30" \
    --collection_names "superdove,sentinel-2-l2a" \
    --sample_columns "Built_area,Crops,Trees,SUPERDOVE" \
    --start_datetime "2017-01-01" \
    --end_datetime "2023-12-31" \
    --chipsize 1280 \
    --debug True \
    --make_videos False \
    --batch False \
    --num_workers 10 \
    --worker_id 8
```

## Script Examples from the Codebase

Multiple scripts in `scripts/` demonstrate Sentinel-2 usage:

- **`s2_chips_for_sites.py`** -- Searches for Sentinel-2 items over site geometries using `pystac_client`, applying cloud cover and nodata percentage filters, then exports chips with `export_from_item()`.
- **`hum-337_example_full_workflow_with_writer.py`** -- Creates a multi-source `ProjectDefinition` with `CollectionName.SENTINEL2` and a cloud cover filter of `{'eo:cloud_cover': {'lt': 5}}`, combined with NAIP and Sentinel-1 inputs.
- **`2025.05.26_example_full_workflow.py`** -- Defines a Sentinel-2 + NAIP project with `{'eo:cloud_cover': {'lt': 10}}` and uses `chipsize={CollectionName.SENTINEL2: 128}` to anchor chip footprints to Sentinel-2.

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
    collections=['sentinel-2-l2a'],
    bbox=[-122.5, 37.5, -122.0, 38.0],
    datetime='2023-01-01/2023-06-01',
    query={
        'eo:cloud_cover': {'lt': 5},
        's2:nodata_pixel_percentage': {'lte': 2},
    },
)

items = list(search.items())
```
