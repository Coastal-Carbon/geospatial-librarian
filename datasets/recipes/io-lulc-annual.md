# Impact Observatory Annual Land Cover via Hum Data Engine

## Overview

Impact Observatory's 10m Annual Land Use/Land Cover (IO LULC v2) is a global,
annual land cover classification derived from Sentinel-2 imagery. It is accessed
through the Microsoft Planetary Computer STAC catalog and is one of the Data
Engine's built-in ancillary data sources.

Key facts:

- **Collection ID**: `io-lulc-annual-v02` (Planetary Computer catalog)
- **CollectionName enum**: `LANDCOVER` (in `hum_ai.data_engine.collections`)
- **Resolution**: 10m, categorical (uint8)
- **Temporal coverage**: 2017--2023, one map per year
- **Class scheme**: 9 land cover classes shared with ESA WorldCover

## Collection Configuration

In the Data Engine, the land cover collection is registered as:

| Property         | Value                  |
|------------------|------------------------|
| `CollectionName` | `LANDCOVER`            |
| `catalog_id`     | `microsoft-pc`         |
| `collection_id`  | `io-lulc-annual-v02`   |

Source: `hum_ai.data_engine.collections.CollectionName.LANDCOVER`

## Land Cover Classes (LandcoverCategory Enum)

The pixel values map to classes via the `LandcoverCategory` enum defined in
`hum_ai.data_engine.ancillary.landcover`:

| Value | Class Name          | Description                                      |
|-------|---------------------|--------------------------------------------------|
| 0     | `No_Data`           | Missing data or masked pixels                    |
| 1     | `Water`             | Open water bodies                                |
| 2     | `Trees`             | Tree canopy cover                                |
| 4     | `Flooded_vegetation`| Wetlands, mangroves, flooded forests             |
| 5     | `Crops`             | Cultivated agricultural land                     |
| 7     | `Built_area`        | Impervious surfaces, buildings, infrastructure   |
| 8     | `Bare_ground`       | Exposed soil, sand, rock                         |
| 9     | `Snow_ice`          | Permanent or seasonal snow and ice               |
| 10    | `Clouds`            | Unclassified due to cloud cover                  |
| 11    | `Rangeland`         | Grassland, shrubland, open vegetation            |

**Note**: Values 3 and 6 are unused. Always use the enum rather than hard-coding
integer values.

## How the Data Engine Uses Land Cover

The Data Engine uses IO LULC as an **ancillary data source** for enriching H3
cell records during ingestion. The core class is `LandcoverAncillaryData` in
`hum_ai.data_engine.ancillary.landcover`.

### Output Columns

For each H3 cell and each year in the date range, the engine produces:

| Column               | Type  | Description                                         |
|----------------------|-------|-----------------------------------------------------|
| `cell`               | str   | H3 cell ID                                          |
| `start_time`         | str   | Start of the year (`YYYY-01-01 00:00:00`)           |
| `end_time`           | str   | End of the year (`YYYY-12-31 23:59:59`)             |
| `landcover_majority` | int   | Pixel value of the most common class in the cell    |
| `landcover_unique`   | int   | Count of distinct land cover classes in the cell     |

### Default H3 Resolution

The default H3 resolution for land cover summaries is **11** (approximately 25m
edge length). This is chosen so that multiple 10m land cover pixels fall within
each H3 cell, making majority and histogram statistics meaningful.

### Zonal Summary Method

The engine uses `summarize_categorical` from `hum_ai.data_engine.regrid.zonal_summary`,
which computes per-cell statistics using `rasterstats.zonal_stats` with the H3
cell polygon as the zone geometry. For H3 cells finer than resolution 11, the
engine automatically sets `all_touched=True` to ensure small cells still
intersect raster pixels.

## Usage: Getting Land Cover Summaries

### Per-Cell Majority and Unique Counts

```python
from hum_ai.data_engine.ancillary.landcover import LandcoverAncillaryData

lc = LandcoverAncillaryData()

# Summarize land cover for a set of H3 cells over a date range
h3_cells = ['8b283470d4b5fff', '8b283470d4b1fff', '8b283470d4b3fff']
df = lc.summarize_from_cells(
    h3_cells=h3_cells,
    date_range='2020-01-01/2023-12-31',
    histogram=True,
)
# Returns a DataFrame with columns:
#   cell, start_time, end_time, landcover_majority, landcover_unique
# Plus histogram columns if histogram=True
```

### Raw Raster Array

```python
# Get the raw xarray DataArray for custom analysis
data = lc.get_landcover_array(
    h3_cells=h3_cells,
    date_range='2022-01-01/2022-12-31',
)
# Returns an xarray.DataArray (uint8) with nodata=0
```

### Land Cover Fractions for a Single Cell

```python
# Get per-class pixel fractions for one H3 cell (single year: 2023)
fractions = lc.get_landcover_fractions(
    h3_cell='8b283470d4b5fff',
    histogram=True,
)
# Returns a dict with pixel counts per class
```

## Interpreting Results

### landcover_majority

The `landcover_majority` value is the integer class code (from `LandcoverCategory`)
that covers the most pixels within the H3 cell for that year. To get the
human-readable name:

```python
from hum_ai.data_engine.ancillary.landcover import LandcoverCategory

majority_value = 7
class_name = LandcoverCategory(majority_value).name  # 'Built_area'
```

### landcover_unique

The `landcover_unique` value indicates land cover heterogeneity. A value of 1
means the entire cell is a single class; higher values indicate a mix of classes.
This is useful for:

- **Stratified sampling**: cells with `landcover_unique == 1` are "pure" and may
  be better training samples for classification models.
- **Edge detection**: cells with high `landcover_unique` are at land cover
  boundaries (e.g., urban-rural interface, forest-cropland edge).

## Change Detection Across Years

Because the dataset provides annual maps, you can detect land cover transitions:

```python
import pandas as pd

lc = LandcoverAncillaryData()
df = lc.summarize_from_cells(
    h3_cells=h3_cells,
    date_range='2017-01-01/2023-12-31',
)

# Pivot to get one row per cell, one column per year
pivot = df.pivot_table(
    index='cell',
    columns='start_time',
    values='landcover_majority',
)

# Find cells where land cover changed between any two years
changed = pivot.nunique(axis=1) > 1
changed_cells = pivot[changed]
```

**Caution**: Not all inter-annual changes are real. The classifier may assign
different classes in different years due to image quality or atmospheric
differences. Consider requiring persistent changes (same new class for 2+
consecutive years) before treating a transition as genuine.

## Relationship to ESA WorldCover

IO LULC and ESA WorldCover use the **same 9-class scheme** and the **same 10m
resolution**, both derived from Sentinel-2. The key difference is temporal:

| Property        | IO LULC Annual     | ESA WorldCover      |
|-----------------|--------------------|---------------------|
| Temporal extent | 2017--2023 (annual)| 2020, 2021 (2 maps) |
| Change tracking | Yes (7 years)      | Limited (2 years)   |
| Accuracy        | Good (automated)   | Higher (validated)  |
| Best for        | Temporal analysis  | Single-year accuracy|

For single-year land cover at highest accuracy, prefer ESA WorldCover.
For temporal change analysis, use IO LULC.
