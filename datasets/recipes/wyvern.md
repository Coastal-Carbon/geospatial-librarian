# Wyvern Hyperspectral Imagery via Hum Data Engine

## Overview

Wyvern hyperspectral satellite imagery is accessed through Hum's private STAC
FastAPI catalog — **not** a public data catalog. The imagery has been licensed and
ingested by Hum, and is served as Cloud-Optimized GeoTIFFs through an internal STAC
API endpoint.

This means:

- You do **not** need your own Wyvern commercial license.
- You **cannot** access arbitrary Wyvern scenes — only those in Hum's holdings.
- Access is exclusively through the Data Engine library or Hum's internal STAC API.
- There is no public browse or search interface for this data.

## Collection Configuration

In the Data Engine, Wyvern is registered as:

| Property        | Value            |
|-----------------|------------------|
| `CollectionName`| `WYVERN`         |
| `catalog_id`    | `stac-fastapi`   |
| `collection_id` | `wyvern`         |
| `resolution`    | `5.3` (meters)   |
| `requester_pays`| `False`          |
| `dtype`         | `uint16`         |
| `missing_value` | `0`              |

Source: `hum_ai.data_engine.collections.CollectionName.WYVERN`

## Band Configuration

Wyvern provides 23 contiguous hyperspectral bands spanning 503-799nm, all at 5.3m
resolution. The band IDs used in the Data Engine's `SOURCE_INFO` dictionary are:

| Index | Band ID       | Band Name     | Spectral Region | Wavelength |
|-------|---------------|---------------|-----------------|------------|
| 0     | `Band_503nm`  | `Green_503`   | Green           | 503nm      |
| 1     | `Band_510nm`  | `Green_510`   | Green           | 510nm      |
| 2     | `Band_519nm`  | `Green_519`   | Green           | 519nm      |
| 3     | `Band_535nm`  | `Green_535`   | Green           | 535nm      |
| 4     | `Band_549nm`  | `Green_549`   | Green           | 549nm      |
| 5     | `Band_570nm`  | `Green_570`   | Green           | 570nm      |
| 6     | `Band_584nm`  | `Yellow_584`  | Yellow          | 584nm      |
| 7     | `Band_600nm`  | `Yellow_600`  | Yellow          | 600nm      |
| 8     | `Band_614nm`  | `Yellow_614`  | Yellow          | 614nm      |
| 9     | `Band_635nm`  | `Red_635`     | Red             | 635nm      |
| 10    | `Band_649nm`  | `Red_649`     | Red             | 649nm      |
| 11    | `Band_660nm`  | `Red_660`     | Red             | 660nm      |
| 12    | `Band_669nm`  | `Red_669`     | Red             | 669nm      |
| 13    | `Band_679nm`  | `Red_679`     | Red             | 679nm      |
| 14    | `Band_690nm`  | `Red_690`     | Red             | 690nm      |
| 15    | `Band_699nm`  | `Red_699`     | Red             | 699nm      |
| 16    | `Band_711nm`  | `Rededge_711` | Red Edge        | 711nm      |
| 17    | `Band_722nm`  | `Rededge_722` | Red Edge        | 722nm      |
| 18    | `Band_734nm`  | `Rededge_734` | Red Edge        | 734nm      |
| 19    | `Band_750nm`  | `Rededge_750` | Red Edge        | 750nm      |
| 20    | `Band_764nm`  | `Rededge_764` | Red Edge        | 764nm      |
| 21    | `Band_782nm`  | `Rededge_782` | Red Edge        | 782nm      |
| 22    | `Band_799nm`  | `Nir_799`     | NIR             | 799nm      |

The `band_ids` are the STAC asset keys used to fetch raster data. The `band_names`
encode the spectral region and center wavelength.

## ObservationType Mapping

Each Wyvern band maps to an `ObservationType` enum member for use in model training
and inference pipelines:

| Band Index | ObservationType        | String Value       |
|------------|------------------------|--------------------|
| 0          | `WYVERN_503NM`         | `wyvern_503nm`     |
| 1          | `WYVERN_510NM`         | `wyvern_510nm`     |
| 2          | `WYVERN_519NM`         | `wyvern_519nm`     |
| 3          | `WYVERN_535NM`         | `wyvern_535nm`     |
| 4          | `WYVERN_549NM`         | `wyvern_549nm`     |
| 5          | `WYVERN_570NM`         | `wyvern_570nm`     |
| 6          | `WYVERN_584NM`         | `wyvern_584nm`     |
| 7          | `WYVERN_600NM`         | `wyvern_600nm`     |
| 8          | `WYVERN_614NM`         | `wyvern_614nm`     |
| 9          | `WYVERN_635NM`         | `wyvern_635nm`     |
| 10         | `WYVERN_649NM`         | `wyvern_649nm`     |
| 11         | `WYVERN_660NM`         | `wyvern_660nm`     |
| 12         | `WYVERN_669NM`         | `wyvern_669nm`     |
| 13         | `WYVERN_679NM`         | `wyvern_679nm`     |
| 14         | `WYVERN_690NM`         | `wyvern_690nm`     |
| 15         | `WYVERN_699NM`         | `wyvern_699nm`     |
| 16         | `WYVERN_711NM`         | `wyvern_711nm`     |
| 17         | `WYVERN_722NM`         | `wyvern_722nm`     |
| 18         | `WYVERN_734NM`         | `wyvern_734nm`     |
| 19         | `WYVERN_750NM`         | `wyvern_750nm`     |
| 20         | `WYVERN_764NM`         | `wyvern_764nm`     |
| 21         | `WYVERN_782NM`         | `wyvern_782nm`     |
| 22         | `WYVERN_799NM`         | `wyvern_799nm`     |

## CollectionInput Setup

To include Wyvern in a Data Engine project, create a `CollectionInput` with
`CollectionName.WYVERN`. The default band IDs and resolution (5.3m) are pulled
automatically from `SOURCE_INFO`:

```python
from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import CollectionInput

# Use all 23 bands at default 5.3m resolution
wyvern_input = CollectionInput(
    collection_name=CollectionName.WYVERN,
)

# Or select a spectral subset — e.g., red edge bands only
wyvern_red_edge = CollectionInput(
    collection_name=CollectionName.WYVERN,
    band_ids=(
        'Band_711nm', 'Band_722nm', 'Band_734nm',
        'Band_750nm', 'Band_764nm', 'Band_782nm',
    ),
)
```

## Key Differences from Broadband Multispectral Sensors

Wyvern is a **hyperspectral** sensor, which changes how you work with the data
compared to multispectral datasets like Sentinel-2, SuperDove, or Pleiades:

1. **23 contiguous bands vs. discrete bands** — Instead of a few widely-spaced
   spectral channels, Wyvern provides dense, nearly continuous spectral sampling
   across the 503-799nm range. This enables spectral curve analysis, not just
   band ratio indices.
2. **Band selection matters** — Loading all 23 bands when you only need a few
   wastes memory and I/O. Always subset to the spectral region relevant to your
   analysis.
3. **Specialized analysis techniques** — Standard indices (NDVI, NDWI) work but
   underutilize the data. Consider spectral unmixing, continuum removal,
   derivative spectroscopy, or spectral angle mapping to exploit the full
   spectral dimension.
4. **No SWIR coverage** — The spectral range stops at 799nm. For moisture,
   burn severity, or mineral features in the 1000-2500nm range, pair with
   Sentinel-2 or Landsat.
5. **Cross-sensor comparison** — A single Sentinel-2 "Red" band (665nm) integrates
   signal across a wide wavelength window. The equivalent spectral region in
   Wyvern spans multiple narrow bands (e.g., Band_660nm, Band_669nm, Band_679nm).
   Direct pixel-value comparison across sensors requires spectral convolution.

## Spectral Regions at a Glance

The 23 bands fall into five spectral regions:

| Region    | Bands          | Wavelength Range | Count | Useful For                              |
|-----------|----------------|------------------|-------|-----------------------------------------|
| Green     | 0-5            | 503-570nm        | 6     | Water quality, green vegetation peak    |
| Yellow    | 6-8            | 584-614nm        | 3     | Vegetation stress, senescence           |
| Red       | 9-15           | 635-699nm        | 7     | Chlorophyll absorption, soil contrast   |
| Red Edge  | 16-21          | 711-782nm        | 6     | Vegetation health, species separation   |
| NIR       | 22             | 799nm            | 1     | Biomass, vegetation structure           |

## Common Analysis Approaches

### Narrowband Vegetation Indices

With contiguous spectral coverage, you can compute narrowband indices that are more
sensitive than their broadband equivalents:

- **Narrowband NDVI** using Band_679nm (red absorption maximum) and Band_799nm (NIR
  reflectance plateau) — more precise than broadband NDVI because the red band is
  centered exactly at the chlorophyll absorption feature.
- **Red Edge Position (REP)** — the inflection point wavelength in the 690-750nm
  region. Shifts in REP correlate with chlorophyll concentration and vegetation
  stress. Requires fitting a curve across the red edge bands.
- **MERIS Terrestrial Chlorophyll Index (MTCI)** using bands near 681nm, 709nm, and
  753nm — Wyvern has bands very close to these wavelengths.

### Spectral Curve Analysis

Rather than computing a single index, extract the full 23-band spectral signature
for each pixel and compare against reference spectral libraries. This approach is
standard for mineral identification and vegetation species classification with
hyperspectral data.

### Derivative Spectroscopy

Compute the first or second derivative of the spectral curve to enhance subtle
absorption features and reduce the effects of illumination variation and background
reflectance.

## Key Differences from Public Catalogs

Like Pleiades and SuperDove, Wyvern uses the `stac-fastapi` catalog ID. This is
Hum's internal STAC server. Several practical differences follow:

1. **No public STAC endpoint** — You cannot use `pystac-client` to browse this
   catalog from outside Hum's infrastructure.
2. **Limited holdings** — Only scenes that Hum has specifically licensed and
   ingested are available. Wyvern is a new constellation, so holdings are smaller
   than for established sensors.
3. **No standard cloud masking** — Wyvern does not ship with a built-in cloud mask
   or scene classification layer. Cloud detection must be handled by the analyst.
4. **No catalog filters registered** — The `CATALOG_FILTERS` dictionary in
   `ingredients.py` does not include a default filter for Wyvern. Pass filters
   manually if needed.

## Multi-Source Workflows

Wyvern is most powerful when paired with other datasets. Typical combinations:

```python
# Wyvern + Sentinel-2: hyperspectral detail + SWIR bands + temporal density
collection_inputs = (
    CollectionInput(
        collection_name=CollectionName.WYVERN,
    ),
    CollectionInput(
        collection_name=CollectionName.SENTINEL2,
        catalog_filters={'eo:cloud_cover': {'lt': 5}},
    ),
)

# Wyvern + SuperDove: hyperspectral detail + near-daily revisit
collection_inputs = (
    CollectionInput(
        collection_name=CollectionName.WYVERN,
    ),
    CollectionInput(
        collection_name=CollectionName.SUPERDOVE,
    ),
)
```

## Data Holdings Discovery

To check what Wyvern data is available for a given area, use the Data Engine's
catalog search functionality. The holdings are indexed in Hum's STAC database and
can be queried by bounding box and time range via the standard search interface
(see `hum_ai.data_engine.catalog.stac_utils` and `hum_ai.data_engine.ancillary.search`).
