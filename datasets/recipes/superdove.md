# SuperDove — Data Engine Recipe

How to load and work with Planet SuperDove 8-band imagery using the Hum data engine.

## Quick Reference

| Property | Value |
|---|---|
| Collection | `CollectionName.SUPERDOVE` |
| STAC catalog | `stac-fastapi` |
| STAC collection ID | `superdove` |
| Bands | Coastal Blue, Blue, Green I, Green, Yellow, Red, Red Edge, Near-Infrared |
| Resolution (stored) | 1.0m |
| Native GSD | ~3m |

## Band Order

The 8 bands are indexed in this order (0-based) within the data engine:

| Index | Band ID | ObservationType |
|---|---|---|
| 0 | Coastal Blue | `SUPERDOVE_COASTAL_BLUE` |
| 1 | Blue | `SUPERDOVE_BLUE` |
| 2 | Green I | `SUPERDOVE_GREEN_I` |
| 3 | Green | `SUPERDOVE_GREEN` |
| 4 | Yellow | `SUPERDOVE_YELLOW` |
| 5 | Red | `SUPERDOVE_RED` |
| 6 | Red Edge | `SUPERDOVE_RED_EDGE` |
| 7 | Near-Infrared | `SUPERDOVE_NIR` |

## Basic Usage

See `superdove.py` in this directory for a runnable example. The key steps are:

1. **Import the collection** — Use `CollectionName.SUPERDOVE` from `hum_ai.data_engine.collections`.
2. **Build a CollectionInput** — This specifies which bands and resolution to use.
3. **Search the catalog** — Query the STAC FastAPI catalog for scenes covering your area of interest.
4. **Load imagery** — Read the raster data for your matched scenes.

## Common Spectral Indices

SuperDove's 8-band configuration supports several useful indices:

- **NDVI** = (NIR - Red) / (NIR + Red) — standard vegetation index
- **NDRE** = (NIR - Red Edge) / (NIR + Red Edge) — sensitive to chlorophyll content, useful for crop health
- **NDWI** = (Green - NIR) / (Green + NIR) — water body detection
- **VARI** = (Green - Red) / (Green + Red - Blue) — visible-range vegetation index

The yellow band can be used in custom indices for vegetation stress and senescence detection. The coastal blue band is useful for water column penetration analysis and atmospheric correction.

## Tips

- **Band selection**: If you only need RGB+NIR, you can pass a subset of `band_ids` to `CollectionInput` to reduce memory and I/O. For example: `band_ids=('Blue', 'Green', 'Red', 'Near-Infrared')`.
- **Cloud masking**: Always check the UDM2 (Usable Data Mask) for cloud, shadow, and haze flags before analysis.
- **Time series**: SuperDove's near-daily revisit is its key advantage. When building dense time series, filter by cloud cover and consider normalizing reflectance across scenes from different satellites in the constellation.
- **Resolution**: The data engine stores SuperDove at 1.0m, but the native sensor GSD is ~3m. The 1.0m storage resolution is an oversample — it does not add spatial detail beyond the native ~3m.
- **Pairing with Sentinel-2**: For applications needing SWIR bands (burn severity, moisture indices), combine SuperDove's high-cadence observations with Sentinel-2's SWIR capability.
