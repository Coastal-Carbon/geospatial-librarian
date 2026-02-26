# Copernicus DEM (GLO-30 / GLO-90) -- Data Engine Recipe

How to access Copernicus DEM elevation data via direct STAC queries to
Microsoft Planetary Computer. This dataset is **not** integrated into the
Data Engine's collection or ancillary frameworks.

## Quick Reference

| Property | Value |
|---|---|
| Data Engine integration | **None** -- not in CollectionName, no ancillary class |
| Access method | Direct STAC queries to Planetary Computer |
| STAC catalog | Microsoft Planetary Computer |
| STAC collection (30m) | `cop-dem-glo-30` |
| STAC collection (90m) | `cop-dem-glo-90` |
| Suggested H3 resolution | 11 (~2000 m2 cells, ~24.8m spacing) |
| Output columns (recipe) | `cell`, `elevation_median`, `elevation_range` |
| Units | meters above EGM2008 geoid |
| Temporal | Static (no time dimension) |

## Data Engine Status

**Copernicus DEM is NOT accessible through the Data Engine's standard
frameworks.** Specifically:

- **No `CollectionName` entry**: The `CollectionName` enum in
  `hum_ai.data_engine.collections` does not include COP_DEM. The enum
  contains: SENTINEL1, SENTINEL2, LANDSAT, LANDCOVER, NAIP, PLEIADES,
  SKYSAT, CAPELLA, SUPERDOVE, UMBRA, SPOT_MS, WORLDVIEW, WYVERN, and
  ESA_WORLDCOVER. You cannot use `CollectionInput` or `CollectionName` to
  access Copernicus DEM.

- **No ancillary data class**: The Data Engine's elevation ancillary module
  (`hum_ai.data_engine.ancillary.elevation`) implements `ElevationAncillaryData`,
  which uses **NASADEM** (STAC collection `nasadem`), not Copernicus DEM.
  There is no `CopernicusDEMAncillaryData` class or equivalent.

- **Direct STAC access only**: To use Copernicus DEM, you must query the
  Planetary Computer STAC API directly using `pystac-client` and
  `planetary-computer`, as shown in this recipe.

## How to Access Copernicus DEM

### 1. STAC Catalog Connection

The same connection pattern used by the Data Engine's NASADEM module, but
querying the Copernicus DEM collections directly:

```python
import planetary_computer
import pystac_client

catalog = pystac_client.Client.open(
    'https://planetarycomputer.microsoft.com/api/stac/v1',
    modifier=planetary_computer.sign_inplace,
)
```

### 2. Search for DEM Tiles

Copernicus DEM is a static product with no time dimension. Search by
bounding box only. Planetary Computer hosts two collections:

- `cop-dem-glo-30` -- 30m posting (1 arc-second), the standard product
- `cop-dem-glo-90` -- 90m posting (3 arc-second), lower resolution

```python
search = catalog.search(
    collections=['cop-dem-glo-30'],  # or 'cop-dem-glo-90'
    bbox=bbox_of_interest,
)
items = search.item_collection()
```

### 3. Load Raster Data with odc.stac

Load the matched tiles as a dask-backed xarray Dataset. The elevation
data is in a band named `data`.

```python
import odc.stac

data = odc.stac.load(
    items,
    chunks={'x': 128, 'y': 128},
    bbox=bbox_of_interest,
    bands=['data'],  # Copernicus DEM band name
)

elevation = data['data']
```

**Key difference from NASADEM**: NASADEM uses `.to_array().squeeze(dim='variable')`
because odc.stac returns it with an extra singleton dimension. Copernicus DEM
can be accessed directly via `data['data']` when specifying the band name.

### 4. Compute Zonal Statistics per H3 Cell

The recipe computes the same statistics as the Data Engine's
`ElevationAncillaryData` (median and range per H3 cell), using the same
`all_touched` logic for handling cells smaller than pixels:

```python
import h3
from rasterstats import zonal_stats
from shapely.geometry import Polygon

resolution = h3.get_resolution(h3_cells[0])
if resolution > 11:  # cells smaller than 30m pixels
    all_touched = True
else:
    all_touched = False

for cell in h3_cells:
    boundary = h3.cell_to_boundary(cell)
    poly = Polygon([(lng, lat) for lat, lng in boundary])
    summary = zonal_stats(
        [poly], raster_array, affine=transform,
        nodata=0, stats=['median', 'range'],
        all_touched=all_touched,
    )[0]
```

### 5. Output

The resulting DataFrame has the same structure as the Data Engine's NASADEM
output:

| cell | elevation_median | elevation_range |
|---|---|---|
| 8b1a6c49612cfff | 345.0 | 16.0 |
| 8b1a6c4960a8fff | 361.0 | 22.0 |
| 8b1a6c4960acfff | 354.0 | 10.0 |

## Copernicus DEM vs NASADEM (Data Engine Context)

| Property | Copernicus DEM (GLO-30) | NASADEM |
|---|---|---|
| Data Engine integration | **None** | `ElevationAncillaryData` ancillary class |
| CollectionName entry | **No** | **No** (accessed via ancillary framework) |
| STAC collection | `cop-dem-glo-30` / `cop-dem-glo-90` | `nasadem` |
| Source sensor | TanDEM-X (X-band radar) | SRTM (C-band radar) |
| Acquisition period | 2011-2015 | February 2000 |
| Vertical accuracy (LE90) | ~2-4m | ~6-9m |
| Coverage | Global (including polar) | 60N to 56S |
| Vertical datum | EGM2008 | EGM96 |
| Data Engine role | Not integrated | Primary elevation source |

## When to Use Copernicus DEM Instead of NASADEM

Copernicus DEM is the better choice when you need:

- **Higher vertical accuracy** (~2-4m vs ~6-9m LE90)
- **Polar/high-latitude coverage** (Copernicus DEM covers global including
  Arctic/Antarctic; NASADEM stops at 60N/56S)
- **More recent terrain representation** (2011-2015 vs February 2000)
- **Quality masks** (HEM, EDM, FLM, WBM) for per-pixel accuracy assessment

However, using Copernicus DEM requires the direct STAC access pattern shown
in this recipe. It cannot be used with `ElevationAncillaryData` or any other
Data Engine ancillary class without implementing a new one.

## Implementing a Data Engine Ancillary Class (Future Work)

To integrate Copernicus DEM into the Data Engine, you would need to create a
new ancillary data class following the pattern of `ElevationAncillaryData`:

```python
from hum_ai.data_engine.ancillary.datasource import AncillaryData

class CopernicusDEMAncillaryData(AncillaryData):
    """Copernicus DEM elevation data -- would need to be implemented."""

    def __init__(self):
        self.catalog = 'https://planetarycomputer.microsoft.com/api/stac/v1'
        self.collection = 'cop-dem-glo-30'  # or 'cop-dem-glo-90'
        self.default_h3_resolution = 11
        self.output_columns = ['cell', 'elevation_median', 'elevation_range']
        self.is_temporal = False

    def summarize_from_cells(self, h3_cells):
        # Similar to ElevationAncillaryData.summarize_from_cells
        # but querying 'cop-dem-glo-30' instead of 'nasadem'
        # and handling the different band structure and nodata value
        raise NotImplementedError("Not yet implemented in the data-engine")
```

This class does **not** exist in the data-engine codebase today.

## Tips

- **Static data**: Like NASADEM, Copernicus DEM has no time dimension. No
  date filters are needed in STAC searches.
- **Nodata handling**: Copernicus DEM uses 0 for ocean/void areas, unlike
  NASADEM which uses -999. Be careful with nodata masking.
- **Band name**: The elevation band in Copernicus DEM is named `data`, not
  `elevation`. Specify `bands=['data']` when loading with odc.stac.
- **Vertical datum difference**: Copernicus DEM uses EGM2008; NASADEM uses
  EGM96. If comparing elevation values between the two, account for the
  small (~1m in most places) geoid model difference.
- **Dask chunking**: Same chunking strategy as NASADEM applies. Use
  `chunks={'x': 128, 'y': 128}` for lazy loading of large areas.
