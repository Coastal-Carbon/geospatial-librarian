# GPW Population Density — Data Engine Recipe

How to load and work with Gridded Population of the World v4 (GPW) population
density data using the Hum data engine.

## Quick Reference

| Property | Value |
|---|---|
| Data source class | `PopulationAncillaryData` |
| Module | `hum_ai.data_engine.ancillary.population` |
| S3 location | `s3://cc-dataocean/population/gpw/` |
| File pattern | `gpw_v4_population_density_rev11_{year}_30_sec.tif` |
| Available years | 2000, 2005, 2010, 2015, 2020 |
| Active year(s) | 2020 (others commented out) |
| Resolution | 30 arc-seconds (~1km at equator) |
| Default H3 resolution | 7 |
| Units | Persons per square kilometer |
| Output columns | `cell`, `start_time`, `end_time`, `population_median`, `population_range` |

## How GPW Differs from Imagery Collections

GPW is an **ancillary data source**, not a STAC collection. This means:

- You do **not** use `CollectionInput` or `CollectionName` to access it.
- You do **not** search a STAC catalog for GPW scenes.
- Instead, you instantiate `PopulationAncillaryData` and call its
  `summarize_from_cells()` or `summarize_from_item()` methods directly.
- The data is read from a static GeoTIFF on S3, not from a dynamic catalog.

This is the same pattern used by other ancillary sources in the Data Engine
(land cover, soils, elevation derivatives).

## Basic Usage

See `gpw-population.py` in this directory for a runnable example. The key steps are:

1. **Import the class** — Use `PopulationAncillaryData` from
   `hum_ai.data_engine.ancillary.population`.
2. **Instantiate** — No arguments needed; S3 path, years, and H3 resolution
   are configured in the module-level `METADATA` dictionary.
3. **Summarize from H3 cells** — Pass a list of H3 cell IDs to
   `summarize_from_cells()`. Returns a DataFrame with median and range
   population density per cell.
4. **Or summarize from a STAC item** — Pass an item ID and H3 level to
   `summarize_from_item()`. The method resolves the item geometry, computes
   the covering H3 cells, and runs the zonal summary.

## Output Schema

The returned DataFrame has these columns:

| Column | Type | Description |
|---|---|---|
| `cell` | str | H3 cell ID |
| `start_time` | str (ISO 8601) | Start of the 5-year validity window |
| `end_time` | str (ISO 8601) | End of the 5-year validity window |
| `population_median` | float | Median population density within the H3 cell (persons/km2) |
| `population_range` | float | Range (max - min) of population density within the H3 cell |

## H3 Resolution Considerations

The GPW raster is ~1km resolution. The default H3 resolution for ingestion is 7
(~1.2km cell spacing, ~1.4km2 area). This means:

- **H3 res 7 or lower**: Each hexagon covers multiple GPW pixels. The zonal
  statistics (median, range) are computed over several pixel values, giving a
  meaningful statistical summary. `all_touched=False` is used (only pixels
  whose center falls within the hexagon are included).
- **H3 res 8 or higher**: Hexagons become smaller than a GPW pixel. The code
  detects this and switches to `all_touched=True` so that every hexagon picks
  up at least one pixel value. In this regime, many adjacent hexagons will
  share the same pixel value, and the range statistic becomes less informative.

Choose the H3 resolution based on your downstream analysis needs, but be aware
of the resolution mismatch implications.

## Enabling Multi-Year Data

By default, only the 2020 year is active. To enable all five time steps:

```python
# In hum_ai/data_engine/ancillary/population.py, change:
'years': [2020],
# To:
'years': [2000, 2005, 2010, 2015, 2020],
```

When multiple years are enabled, `summarize_from_cells()` returns a DataFrame
with rows for each (cell, year) combination. Each year is assigned a 5-year
validity window: 2000 covers 2000-01-01 to 2004-12-31, 2005 covers
2005-01-01 to 2009-12-31, and so on.

## Database Ingestion

Population summaries can be upserted into the ancillary database using the
`upsert_ancillary_data` utility:

```python
from hum_ai.data_engine.database.utils import upsert_ancillary_data
from hum_ai.data_engine.config import get_config

upsert_ancillary_data(result_df, get_config().db_url, 'population')
```

This writes the population statistics to the `population` table, indexed by
H3 cell and time range.

## Interpreting Population Density Values

Typical value ranges (persons per square kilometer):

| Environment | Approximate Range |
|---|---|
| Uninhabited / wilderness | 0 |
| Very sparse rural | 0.1 - 10 |
| Moderate rural / agricultural | 10 - 100 |
| Peri-urban / suburban | 100 - 1,000 |
| Urban | 1,000 - 10,000 |
| Dense urban core | 10,000 - 50,000+ |

## Tips

- **Coastline cells**: H3 cells near coastlines may partially overlap ocean
  NoData areas in the GPW raster. The zonal statistics will only consider valid
  (non-NoData) pixels, but be aware that coastal cells may have fewer pixels
  contributing to the summary.
- **Pairing with land cover**: Population density is most informative when
  combined with land cover data. A cell with 500 persons/km2 and majority
  cropland tells a different story than one with 500 persons/km2 and majority
  built-up surface.
- **Temporal matching**: When pairing population data with imagery from a
  specific date, use the GPW year whose 5-year window contains that date.
  For imagery from 2023, the 2020 GPW snapshot is the most appropriate.
- **Zero vs. NoData**: A population density of 0 means the cell is on land but
  has zero estimated population. NoData means the cell is ocean or otherwise
  outside the GPW coverage. These are semantically different.
