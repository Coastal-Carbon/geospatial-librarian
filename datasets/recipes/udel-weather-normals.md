# University of Delaware Climate Normals — Data Engine Recipe

How to load and work with UDel monthly climate normals (temperature and precipitation) using the Hum data engine's ancillary data system.

## Quick Reference

| Property | Value |
|---|---|
| Ancillary class | `WeatherAncillaryData` |
| Module | `hum_ai.data_engine.ancillary.weather` |
| S3 location | `s3://cc-dataocean/weather/udel/` |
| Files | `air.mon.1981-2010.ltm.v401.nc`, `precip.mon.1981-2010.ltm.v401.nc` |
| Resolution | 0.5 degree (~55 km at equator) |
| Default H3 res | 3 (~59.7 km spacing) |
| Climatological period | 1981-2010 |
| Original source | [NOAA PSL](https://psl.noaa.gov/data/gridded/data.UDel_AirT_Precip.html) |

## Output Columns

The `summarize_from_cells()` method returns a DataFrame with 25 columns:

| Column | Description | Units |
|---|---|---|
| `cell` | H3 cell index | — |
| `air_1` through `air_12` | Monthly mean temperature (Jan-Dec) | degrees C |
| `precip_1` through `precip_12` | Monthly mean precipitation (Jan-Dec) | cm/month |

## Basic Usage

See `udel-weather-normals.py` in this directory for a runnable example. The key steps are:

1. **Import the ancillary class** — Use `WeatherAncillaryData` from `hum_ai.data_engine.ancillary.weather`.
2. **Provide H3 cells** — Either generate H3 cells from a geometry or pass them directly.
3. **Call `summarize_from_cells()`** — Returns a DataFrame with climate values for each cell.
4. **Or use `summarize_from_item()`** — Pass a STAC item ID and H3 level to get climate context for a satellite scene's footprint.

## How Spatial Sampling Works

The weather data is on a regular 0.5-degree grid, which is much coarser than typical imagery. Instead of zonal statistics (used for higher-resolution ancillary rasters), the Data Engine uses nearest-neighbor point sampling:

1. All unique weather grid points are loaded and indexed in a **scipy cKDTree**.
2. Each H3 cell centroid is queried against the tree to find the nearest weather grid point.
3. All 12 monthly values for both temperature and precipitation are assigned from that nearest point.

This means multiple H3 cells (especially at fine resolutions) will share identical climate values. The default H3 resolution of 3 is chosen to approximately match the weather grid spacing.

## Common Use Cases

- **Ecological niche modeling**: Monthly temperature and precipitation define the fundamental climate envelope for species distribution. Pair with elevation (NASADEM) and soils (HWSD2) for a complete environmental characterization.
- **Agricultural suitability**: Crop growth models use monthly temperature and precipitation as primary drivers. The 12-month profile captures seasonality critical for determining growing seasons.
- **Carbon flux estimation**: Climate is a primary control on ecosystem productivity and decomposition. These normals provide the baseline climate context for carbon cycle modeling.
- **Site characterization**: For any area of interest, the 24 climate variables provide a compact fingerprint of the local climate regime.

## Derived Variables

From the raw monthly values, you can compute useful summary statistics:

- **Mean annual temperature**: average of `air_1` through `air_12`
- **Annual temperature range**: max monthly temp minus min monthly temp (continentality)
- **Total annual precipitation**: sum of `precip_1` through `precip_12`
- **Precipitation seasonality**: coefficient of variation across the 12 monthly precip values
- **Warmest/coldest month**: identifies the temperature extremes
- **Driest/wettest month**: identifies the precipitation extremes

These derived variables are often more ecologically meaningful than individual monthly values.

## Tips

- **H3 resolution**: The default H3 resolution of 3 is appropriate for most use cases. Going finer (e.g., H3 res 5 or 8) will not add climate information — you will just get duplicate values across nearby cells. However, finer H3 resolution may be needed if you are joining climate data with other ancillary sources that use a finer grid.
- **Unit conversion**: Precipitation is in cm/month. Multiply by 10 to convert to mm/month, which is the more common unit in hydrological and ecological literature.
- **Longitude convention**: The source NetCDF files use 0-360 longitude. The Data Engine automatically converts to -180/+180. If you load the files directly, remember to apply this shift.
- **Memory**: Both NetCDF files are ~18 MB each. They are loaded fully into memory on each call. For batch processing many areas, consider caching the loaded data.
- **Pairing with imagery**: When building feature stacks that combine satellite imagery with climate context, remember that one climate grid cell covers a very large area (~55 km). Climate values will be constant across an entire satellite scene for small footprints.
