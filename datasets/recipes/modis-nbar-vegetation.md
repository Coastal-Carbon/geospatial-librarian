# MODIS NBAR Vegetation Indices — Data Engine Recipe

How to compute NDVI percentile statistics from MODIS MCD43A4 NBAR data using the Data Engine ancillary system.

## Overview

The Data Engine uses MODIS MCD43A4 (Collection 6.1) as an ancillary data source for vegetation index statistics. Unlike the imagery collections (Sentinel-2, SuperDove, etc.) which go through the `CollectionInput` system, MODIS NBAR is accessed through the **ancillary data pipeline** — it is loaded from Microsoft Planetary Computer via STAC, NDVI is computed on-the-fly from the red and NIR bands, and percentile statistics are aggregated per H3 cell over monthly time windows.

## Quick Reference

| Property | Value |
|---|---|
| Module | `hum_ai.data_engine.ancillary.indices` |
| Class | `IndicesAncillaryData` |
| STAC Catalog | Microsoft Planetary Computer |
| STAC Collection ID | `modis-43A4-061` |
| Bands Used | Band 1 (Red, 620-670nm), Band 2 (NIR, 841-876nm) |
| Derived Index | NDVI = (NIR - Red) / (NIR + Red) |
| Output Statistics | `ndvi_min`, `ndvi_p10`, `ndvi_p50`, `ndvi_p90`, `ndvi_max` |
| Default H3 Resolution | 8 (~0.74 km^2 per cell) |
| Database Table | `modis_indices` |
| Resolution | 500m |

## How It Differs from Imagery Collections

Most Data Engine recipes use `CollectionInput` and `CollectionName` to configure imagery access. MODIS vegetation indices instead use the **ancillary data framework**:

- The `IndicesAncillaryData` class extends `AncillaryData` (the base class for contextual geospatial data).
- Data is queried directly from the Planetary Computer STAC API using `pystac_client` and loaded with `odc.stac`.
- The output is a pandas DataFrame of per-cell statistics, not raster imagery.
- Results are stored in a database table (`modis_indices`) indexed by H3 cell and time range.

This pattern is shared with other ancillary sources in the Data Engine (elevation, land cover, soils, weather, population).

## Basic Usage

See `modis-nbar-vegetation.py` in this directory for a runnable example. The key steps are:

1. **Instantiate the data source** — Create an `IndicesAncillaryData` object.
2. **Define H3 cells and time periods** — Specify which H3 cell IDs and monthly time grid IDs (e.g., `'2020-07'`) to process.
3. **Run the summary** — Call `summarize_from_cells()` which handles STAC search, data loading, NDVI computation, and zonal statistics.
4. **Store results** — Use `upsert_ancillary_data()` to write results to the database.

## NDVI Computation Details

The module computes NDVI from the NBAR (Nadir BRDF-Adjusted Reflectance) bands:

- **Band 1** (`Nadir_Reflectance_Band1`): Red, 620-670nm
- **Band 2** (`Nadir_Reflectance_Band2`): NIR, 841-876nm
- **Formula**: `NDVI = (Band2 - Band1) / (Band2 + Band1)`

The BRDF adjustment is important: it normalizes for varying sun-sensor geometry across dates and locations, producing more consistent reflectance values than raw surface reflectance. This makes the resulting NDVI time series more reliable for phenological analysis.

Division-by-zero cases (where both red and NIR reflectance are zero or near-zero) are masked. The nodata value is set to -999.

## Output Statistics

For each H3 cell within a monthly time window, the following percentile statistics are computed across all valid NDVI observations:

| Column | Description |
|---|---|
| `ndvi_min` | Minimum NDVI value observed in the cell during the month |
| `ndvi_p10` | 10th percentile — captures low-greenness conditions |
| `ndvi_p50` | Median NDVI — representative of typical vegetation condition |
| `ndvi_p90` | 90th percentile — captures peak greenness |
| `ndvi_max` | Maximum NDVI value observed in the cell during the month |

These statistics capture the distribution of vegetation condition within each cell. The spread between percentiles is informative: a narrow p10-p90 range suggests stable vegetation (e.g., evergreen forest), while a wide range suggests heterogeneous or seasonally dynamic land cover.

## STAC Search Quirk

The MODIS STAC collection on Planetary Computer returns more items than expected for narrow date ranges — up to 16 items even for a single-day query. This is because the BRDF model uses a 16-day rolling window, and items overlap temporally. The Data Engine applies explicit post-search date filtering to ensure only items within the requested time range are processed:

```python
items = [
    item for item in items
    if item.get_datetime() >= timegrid.start_time
    and item.get_datetime() < timegrid.end_time
]
```

## H3 Resolution Considerations

The default H3 resolution is 8, which yields cells of approximately 0.74 km^2. At 500m MODIS resolution, this means roughly 3 pixels per H3 cell — enough for meaningful statistics but not high-count distributions.

When the H3 resolution is finer than the default (smaller cells relative to the 500m pixel grid), the module uses `all_touched=True` in rasterization to ensure every cell receives a value, even if the cell is smaller than a single pixel.

## Tips

- **Monthly granularity**: The time grid uses monthly windows (e.g., `'2020-07'`). Each month is processed as a separate query and aggregation.
- **Temporal coverage**: MCD43A4 data is available from 2000/2001 to present. For long-term phenology baselines, query multiple years of the same month.
- **Pairing with Sentinel-2**: MODIS NDVI percentiles provide a coarse but temporally deep vegetation baseline. Pair with Sentinel-2 (10m) for detailed spatial analysis within the context of MODIS-derived phenology patterns.
- **Performance**: The zonal summary step is slow for large numbers of time slices because each daily MODIS scene is processed individually. For large-area or long-duration analyses, expect significant processing time.
- **Database storage**: Results are upserted into the `modis_indices` table. The upsert handles deduplication if the same cell and time range are processed again.
