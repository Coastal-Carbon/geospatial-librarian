# Pleiades Imagery via Hum Data Engine

## Overview

Pleiades (Airbus Defence and Space) imagery is accessed through Hum's private STAC
FastAPI catalog — **not** a public data catalog. The imagery has been licensed and
ingested by Hum, and is served as Cloud-Optimized GeoTIFFs through an internal STAC
API endpoint.

This means:

- You do **not** need your own Airbus commercial license.
- You **cannot** access arbitrary Pleiades scenes — only those in Hum's holdings.
- Access is exclusively through the Data Engine library or Hum's internal STAC API.
- There is no public browse or search interface for this data.

## Collection Configuration

In the Data Engine, Pleiades is registered as:

| Property        | Value            |
|-----------------|------------------|
| `CollectionName`| `PLEIADES`       |
| `catalog_id`    | `stac-fastapi`   |
| `collection_id` | `pleiades`       |
| `resolution`    | `1.0` (meters)   |
| `requester_pays`| `False`          |

Source: `hum_ai.data_engine.collections.CollectionName.PLEIADES`

## Band Configuration

Pleiades Neo provides 6 multispectral bands, all at 1m resolution. The band IDs
used in the Data Engine's `SOURCE_INFO` dictionary are:

| Index | Band ID                  | Band Name                 | Wavelength (approx.) |
|-------|--------------------------|---------------------------|----------------------|
| 0     | `Coastal Blue`           | `coastal-blue`            | 443nm                |
| 1     | `Blue`                   | `blue`                    | 490nm                |
| 2     | `Green`                  | `green`                   | 560nm                |
| 3     | `Red`                    | `red`                     | 665nm                |
| 4     | `Vegetation Red Edge`    | `vegetation-red-edge-1`   | 705nm                |
| 5     | `Near-Infrared`          | `near-infrared`           | 842nm                |

The `band_ids` (first column after index) are the STAC asset keys used to fetch
raster data. The `band_names` are human-readable identifiers used in the
`ObservationType` enum.

## ObservationType Mapping

Each Pleiades band maps to an `ObservationType` enum member for use in model
training and inference pipelines:

| Band Index | ObservationType                             | String Value                       |
|------------|---------------------------------------------|------------------------------------|
| 0          | `PLEIADES_COASTAL_BLUE`                     | `pleiades_coastal_blue`            |
| 1          | `PLEIADES_BLUE`                             | `pleiades_blue`                    |
| 2          | `PLEIADES_GREEN`                            | `pleiades_green`                   |
| 3          | `PLEIADES_RED`                              | `pleiades_red`                     |
| 4          | `PLEIADES_VEGETATION_RED_EDGE_1`            | `pleiades_vegetation_red_edge_1`   |
| 5          | `PLEIADES_NEAR_INFRARED`                    | `pleiades_near_infrared`           |

## CollectionInput Setup

To include Pleiades in a Data Engine project, create a `CollectionInput` with
`CollectionName.PLEIADES`. The default band IDs and resolution (1.0m) are pulled
automatically from `SOURCE_INFO`:

```python
from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import CollectionInput

# Use all 6 bands at default 1m resolution
pleiades_input = CollectionInput(
    collection_name=CollectionName.PLEIADES,
)

# Or select specific bands
pleiades_rgb_nir = CollectionInput(
    collection_name=CollectionName.PLEIADES,
    band_ids=('Blue', 'Green', 'Red', 'Near-Infrared'),
)
```

## Key Differences from Public Catalogs

Unlike Sentinel-2 (accessed via `microsoft-pc` catalog) or NAIP (accessed via
`earth-search-aws`), Pleiades uses the `stac-fastapi` catalog ID. This is Hum's
internal STAC server. Several practical differences follow:

1. **No public STAC endpoint** — You cannot use `pystac-client` to browse this
   catalog from outside Hum's infrastructure.
2. **Limited holdings** — Only scenes that Hum has specifically licensed and
   ingested are available. Coverage is not global or systematic.
3. **No standard cloud masking** — Unlike Sentinel-2 L2A which includes a Scene
   Classification Layer (SCL), Pleiades does not ship with a built-in cloud mask.
4. **No catalog filters registered** — The `CATALOG_FILTERS` dictionary in
   `ingredients.py` does not include a default filter for Pleiades (unlike
   Sentinel-2's `eo:cloud_cover` filter). Pass filters manually if needed.

## Multi-Source Workflows

Pleiades is commonly paired with other datasets in the Data Engine. A typical
multi-source project might combine Pleiades for high spatial resolution with
Sentinel-2 for temporal density and SWIR spectral coverage:

```python
collection_inputs = (
    CollectionInput(
        collection_name=CollectionName.PLEIADES,
    ),
    CollectionInput(
        collection_name=CollectionName.SENTINEL2,
        catalog_filters={'eo:cloud_cover': {'lt': 5}},
    ),
)
```

## Data Holdings Discovery

To check what Pleiades data is available for a given area, use the Data Engine's
catalog search functionality. The holdings are indexed in Hum's STAC database and
can be queried by bounding box and time range via the standard search interface
(see `hum_ai.data_engine.catalog.search`).
