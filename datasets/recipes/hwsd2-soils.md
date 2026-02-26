# HWSD2 Soils -- Data Engine Recipe

How to load and work with the Harmonized World Soil Database v2 (HWSD2) using the Hum data engine.

## Quick Reference

| Property | Value |
|---|---|
| Ancillary class | `SoilsAncillaryData` |
| Module | `hum_ai.data_engine.ancillary.soils` |
| S3 raster path | `s3://cc-dataocean/soils/harmonized_world_soils_database_v2/HWSD2_RASTER.tif` |
| S3 lookup table | `s3://cc-dataocean/soils/harmonized_world_soils_database_v2/HWSD2_DB/HWSD2_LAYERS.csv` |
| Resolution | 30 arc-seconds (~1 km at equator) |
| Default H3 resolution | 11 |
| Temporal | Static (not time-varying) |

## Output Columns

The Data Engine extracts four soil properties from the full 48-attribute HWSD2 lookup table:

| Column | Description | Units |
|---|---|---|
| `cell` | H3 cell identifier | -- |
| `sand` | Sand content of the fine earth fraction | percent (%) |
| `clay` | Clay content of the fine earth fraction | percent (%) |
| `organic_carbon` | Soil organic carbon concentration | g/kg |
| `total_nitrogen` | Total nitrogen concentration | g/kg |

## How It Works

HWSD2 is a **classified raster with a lookup table**, not a continuous-value raster. This means:

1. **HWSD2_RASTER.tif** contains integer codes representing soil mapping units (SMUs), not soil property values directly.
2. **HWSD2_LAYERS.csv** (~408,000 rows) maps each SMU ID to 48 soil attributes across multiple depth layers.
3. The Data Engine performs a categorical zonal summary to find the **majority SMU** within each H3 cell, then joins that ID against the CSV to retrieve property values.

This is fundamentally different from continuous rasters (like a DEM) where pixel values are directly meaningful.

## Basic Usage

See `hwsd2-soils.py` in this directory for a runnable example. The key steps are:

1. **Instantiate the ancillary class** -- Create a `SoilsAncillaryData` object.
2. **Provide H3 cells** -- Pass a list of H3 cell IDs to `summarize_from_cells()`.
3. **Receive a DataFrame** -- Get back soil properties indexed by H3 cell.

```python
from hum_ai.data_engine.ancillary.soils import SoilsAncillaryData

soils = SoilsAncillaryData()
result = soils.summarize_from_cells(h3_cells)
# result has columns: cell, sand, clay, organic_carbon, total_nitrogen
```

## Ingesting Into the Database

To ingest HWSD2 summaries into the ancillary database:

```python
from hum_ai.data_engine.ancillary.soils import SoilsAncillaryData
from hum_ai.data_engine.config import get_config
from hum_ai.data_engine.database.utils import upsert_ancillary_data

soils = SoilsAncillaryData()
result = soils.test_summarize()
result = result.drop(columns=['time'])  # static dataset, no time dimension
upsert_ancillary_data(result, get_config().db_url, 'soils')
```

## H3 Resolution Behavior

The default H3 resolution is 11 (~24.8 m cell spacing, ~2000 m2 area). The class automatically adjusts its rasterization strategy based on the relationship between H3 cell size and raster pixel size:

- **H3 resolution <= 11** (cells larger than ~1 km raster pixels): Standard rasterization. Multiple raster pixels fall within each H3 cell and the majority class is selected.
- **H3 resolution > 11** (cells smaller than ~1 km raster pixels): Uses `all_touched=True` to ensure every cell gets a value, since cells may be smaller than individual pixels.

## Accessing Additional Soil Attributes

The Data Engine currently extracts only 4 of the 48 available attributes. If you need others (silt, pH, CEC, bulk density, etc.), you can read the full lookup table directly:

```python
import pandas as pd

df = pd.read_csv(
    's3://cc-dataocean/soils/harmonized_world_soils_database_v2/HWSD2_DB/HWSD2_LAYERS.csv',
    low_memory=False,
    storage_options={'anon': False},
)
print(df.columns.tolist())
# Includes: SAND, SILT, CLAY, ORG_CARBON, TOTAL_N, PH_H2O, CEC_CLAY,
# CEC_SOIL, BULK_DENSITY, GRAVEL, ELCO, ESP, ECE, GYPS, CALCIUM_ITE, ...
```

## Tips

- **Majority class caveat**: The current implementation returns attributes for the single majority soil mapping unit within each H3 cell. In areas with heterogeneous soils, this misses the contribution of minority soil types. A weighted-average approach is planned but not yet implemented.
- **Sand + clay + silt**: These three fractions should sum to approximately 100%. If you need silt content, it can be derived as `silt = 100 - sand - clay`, or read directly from the lookup table.
- **Carbon stock calculation**: To convert organic carbon concentration (g/kg) to a carbon stock (kg/m2 or tonnes/ha), you also need bulk density and layer thickness from the lookup table.
- **Pairing with other ancillary data**: HWSD2 soil properties are commonly used alongside elevation (NASADEM for slope/aspect), land cover (ESA WorldCover), and climate normals (UDel) for ecological modeling and carbon MRV workflows.
- **Resolution awareness**: The ~1 km native resolution means all values within a ~1 km pixel are identical. Do not interpret fine-scale spatial patterns that appear after reprojection or resampling -- they are artifacts of the coarse source data.
