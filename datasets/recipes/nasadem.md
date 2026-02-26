# NASADEM Elevation -- Data Engine Recipe

How the Hum Data Engine loads NASADEM elevation data and computes per-cell
zonal statistics. This is the primary elevation source for all Data Engine
projects.

## Quick Reference

| Property | Value |
|---|---|
| Ancillary class | `ElevationAncillaryData` |
| Source module | `hum_ai.data_engine.ancillary.elevation` |
| STAC catalog | Microsoft Planetary Computer |
| STAC collection | `nasadem` |
| Default H3 resolution | 11 (~2000 m2 cells, ~24.8m spacing) |
| Output columns | `cell`, `elevation_median`, `elevation_range` |
| Units | meters above sea level (EGM96 geoid) |
| Temporal | Static (no time dimension) |

## How It Works

The Data Engine treats NASADEM as an **ancillary data source** -- contextual
geospatial data that is not satellite imagery but provides important features
for analysis. The `ElevationAncillaryData` class inherits from `AncillaryData`
and implements the `summarize_from_cells` method.

The pipeline works in four stages:

1. **STAC search** -- Query Planetary Computer for NASADEM tiles covering the
   bounding box of the input H3 cells
2. **Lazy load** -- Load matching tiles as a dask-backed xarray DataArray via
   `odc.stac.load`
3. **Zonal statistics** -- For each H3 cell, clip the raster and compute
   median and range using `rasterstats`
4. **Output** -- Return a DataFrame with columns `cell`, `elevation_median`,
   and `elevation_range`

## Step-by-Step Walkthrough

### 1. STAC Catalog Connection

The Data Engine connects to the Planetary Computer STAC API and uses the
`planetary_computer.sign_inplace` modifier to handle token signing for
asset access. No API key or registration is required.

```python
import planetary_computer
import pystac_client

catalog = pystac_client.Client.open(
    'https://planetarycomputer.microsoft.com/api/stac/v1',
    modifier=planetary_computer.sign_inplace,
)
```

### 2. Search for NASADEM Tiles

The search uses the bounding box of the input H3 cells. The
`h3_cells_to_polygon` utility converts a collection of H3 cell IDs into a
unified Shapely polygon, then `.bounds` extracts the bounding box. Because
NASADEM is a static product, there is no time filter -- only spatial.

```python
from hum_ai.data_engine.utils.h3_utils import h3_cells_to_polygon

polygon = h3_cells_to_polygon(h3_cells)
bbox_of_interest = polygon.bounds

search = catalog.search(
    collections=['nasadem'],
    bbox=bbox_of_interest,
)
items = search.item_collection()
```

### 3. Load Raster Data with odc.stac

The `odc.stac.load` call reads the matched STAC items as a dask-backed
xarray Dataset, automatically mosaicking multiple 1-degree tiles. The
`chunks` parameter enables lazy loading -- actual pixel data is not read
until computation is triggered.

```python
import odc.stac

data = odc.stac.load(
    items,
    chunks={'x': 128, 'y': 128},
    bbox=bbox_of_interest,
)

# The NASADEM dataset has an extra dummy dimension that must be squeezed
data = data.to_array().squeeze(dim='variable')

# Set the nodata sentinel value
data.rio.write_nodata(-999, inplace=True)
```

**Note on the squeeze**: The `odc.stac.load` call returns an xarray Dataset.
Converting to a DataArray with `.to_array()` introduces a `variable` dimension
(since there is only one band in NASADEM: elevation). The `.squeeze(dim='variable')`
removes this singleton dimension so the array is shaped `(time, y, x)` or
`(y, x)` as expected by the zonal statistics functions.

### 4. Compute Zonal Statistics per H3 Cell

The `summarize_numerical` function from `hum_ai.data_engine.regrid.zonal_summary`
iterates over each H3 cell, clips the raster to the cell boundary, and
computes `median` and `range` statistics using `rasterstats.zonal_stats`.

```python
import h3
from hum_ai.data_engine.regrid.zonal_summary import summarize_numerical

# Determine whether to use all_touched based on cell size vs pixel size
resolution = h3.get_resolution(h3_cells[0])
if resolution > 11:  # default_h3_resolution
    # Cells are small relative to 30m pixels -- include all touched pixels
    all_touched = True
else:
    # Cells are large relative to pixels -- standard behavior
    all_touched = False

df = summarize_numerical(data, h3_cells, all_touched=all_touched)
```

The `all_touched` parameter is important: at H3 resolution 11, cells are
roughly 24.8m across, which is close to the 30m NASADEM pixel size. At finer
H3 resolutions, cells become smaller than pixels, so `all_touched=True`
ensures every cell intersecting a pixel gets a value (otherwise many cells
would return no data).

### 5. Rename and Return

The output columns are renamed from the generic `median`/`range` to
elevation-specific names:

```python
df = df.rename(
    columns={'median': 'elevation_median', 'range': 'elevation_range'},
)
result = df[['cell', 'elevation_median', 'elevation_range']]
```

The resulting DataFrame looks like:

| cell | elevation_median | elevation_range |
|---|---|---|
| 8b1a6c49612cfff | 342.0 | 18.0 |
| 8b1a6c4960a8fff | 358.0 | 24.0 |
| 8b1a6c4960acfff | 351.0 | 12.0 |

## Full Pipeline (Assembled)

See `nasadem.py` in this directory for a self-contained runnable example.
The complete flow from the Data Engine source is:

```python
from hum_ai.data_engine.ancillary.elevation import ElevationAncillaryData
from hum_ai.data_engine.config import get_config
from hum_ai.data_engine.database.utils import upsert_ancillary_data

# Instantiate the elevation ancillary data handler
elevation = ElevationAncillaryData()

# Summarize for a set of H3 cells
df = elevation.summarize_from_cells(h3_cells)

# Persist to the Data Engine database
upsert_ancillary_data(df, get_config().db_url, 'elevation')
```

## NASADEM vs Copernicus DEM

The Data Engine uses NASADEM, not Copernicus DEM. Key differences:

| Property | NASADEM | Copernicus DEM (GLO-30) |
|---|---|---|
| Source sensor | SRTM (C-band radar) | TanDEM-X (X-band radar) |
| Acquisition period | February 2000 | 2011-2015 |
| Vertical accuracy (LE90) | ~6-9m | ~2-4m |
| Coverage | 60N to 56S | Global (including polar) |
| Vertical datum | EGM96 | EGM2008 |
| Quality masks | NUM (source map) | HEM, EDM, FLM, WBM |
| Data Engine role | Primary elevation source | Not currently integrated |

If higher accuracy or polar coverage is needed, Copernicus DEM would be the
better choice, but it would require implementing a new ancillary data class.

## Tips

- **Static data**: NASADEM has no time dimension. The `is_temporal` flag in
  the module metadata is `False`. You never need date filters.
- **Nodata handling**: The code sets nodata to -999. Ocean areas and voids
  will have this value. The zonal statistics functions skip nodata pixels.
- **Dask chunking**: The `chunks={'x': 128, 'y': 128}` parameter keeps memory
  usage low by loading pixel data lazily. For very large areas, this is
  critical -- NASADEM tiles are 1 degree x 1 degree, and a continental-scale
  query could return dozens of tiles.
- **H3 resolution mismatch**: The default H3 resolution of 11 matches the
  ~30m NASADEM pixel spacing well. Using much coarser H3 resolutions
  (e.g., 7 or 8) means many pixels per cell, which is fine for regional
  summaries. Using much finer resolutions (e.g., 13+) means cells smaller
  than pixels -- the `all_touched` logic handles this but the statistics
  become less meaningful.
- **Database persistence**: Results are stored in the Data Engine's ancillary
  database table keyed by H3 cell ID. Use `upsert_ancillary_data` to write
  results, which handles insert-or-update semantics.
