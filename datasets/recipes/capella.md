# Capella Space SAR — Data Engine Recipe

How to search for, load, and work with Capella SAR imagery using the Hum data engine.

## Prerequisites

- Access to Hum's STAC FastAPI catalog with valid credentials
- The `hum_ai.data_engine` library installed
- A configured data engine environment (catalog credentials, etc.)

## Quick Reference

| Property         | Value                                      |
|------------------|--------------------------------------------|
| Collection ID    | `capella`                                  |
| STAC Catalog     | `stac-fastapi`                             |
| Enum             | `CollectionName.CAPELLA`                   |
| Band IDs         | `['HH', 'VV', 'VH', 'HV']`               |
| Primary Band     | `HH` (>98% of holdings)                   |
| ObservationType  | `CAPELLA_HH`                               |
| Default Res.     | `1.0m`                                     |
| Data Type        | SAR amplitude/intensity (single-band)      |

## Searching for Capella Imagery

Use the data engine's catalog search to find available Capella scenes
over an area and time range of interest.

```python
from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import SOURCE_INFO, CollectionInput

# Check what bands and resolution are configured
info = SOURCE_INFO[CollectionName.CAPELLA]
print(f"Band IDs: {info['band_ids']}")
print(f"Resolution: {info['resolution']}m")
```

## Building a CollectionInput

The `CollectionInput` dataclass configures how Capella data is loaded.
By default it uses all band IDs from `SOURCE_INFO`, but since our
Capella holdings are predominantly HH-polarized, you will typically
work with a single band.

```python
from hum_ai.data_engine.ingredients import CollectionInput
from hum_ai.data_engine.collections import CollectionName

# Default: all configured bands (HH, VV, VH, HV)
capella_input = CollectionInput(collection_name=CollectionName.CAPELLA)

# Explicit: HH only (recommended for most workflows)
capella_hh = CollectionInput(
    collection_name=CollectionName.CAPELLA,
    band_ids=('HH',),
    resolution=1.0,
)
```

## ObservationType Mapping

When working with the data engine's observation type system (e.g., for
model inputs or band metadata), Capella maps to a single observation type:

```python
from hum_ai.data_engine.ingredients import ObservationType, COLLECTION_BAND_MAP
from hum_ai.data_engine.collections import CollectionName

# Band index 0 -> CAPELLA_HH
band_map = COLLECTION_BAND_MAP[CollectionName.CAPELLA]
print(band_map)  # {0: ObservationType.CAPELLA_HH}
```

## Combining with Other Sensors

Capella SAR is frequently combined with optical imagery for
multi-modal analysis. The data engine supports multi-collection
workflows.

```python
from hum_ai.data_engine.ingredients import CollectionInput
from hum_ai.data_engine.collections import CollectionName

# SAR + Optical multi-sensor stack
collections = [
    CollectionInput(
        collection_name=CollectionName.CAPELLA,
        band_ids=('HH',),
    ),
    CollectionInput(
        collection_name=CollectionName.SENTINEL2,
        band_ids=('B04', 'B03', 'B02', 'B08'),  # RGB + NIR
        resolution=10.0,
    ),
]
```

## Preprocessing Considerations

1. **Speckle filtering**: SAR imagery contains speckle noise. Apply a
   spatial filter (Lee, Frost, etc.) before visual interpretation or
   pixel-based analysis.

2. **Radiometric calibration**: Convert pixel values to sigma-nought
   (dB) for quantitative backscatter analysis.

3. **Terrain correction**: Use a DEM (e.g., Copernicus DEM at 30m) to
   correct geometric distortions in areas with topography.

4. **Resolution alignment**: When combining with coarser-resolution
   data (e.g., Sentinel-1 at 10m, Sentinel-2 at 10m), decide on a
   target resolution and resample accordingly.

## Notes

- Capella data is commercial and accessed through Hum's internal STAC
  catalog. It is not available on public platforms.
- The `SOURCE_INFO` dictionary lists all four polarizations (HH, VV,
  VH, HV) as band IDs, but the comment in `ingredients.py` notes that
  >98% of our Capella holdings are HH-polarized.
- For broad-area SAR needs at lower cost, consider Sentinel-1 RTC
  (`CollectionName.SENTINEL1`) which provides free VV/VH data at 10m.
- For another commercial high-res SAR option, Umbra
  (`CollectionName.UMBRA`) provides VV-polarized data at 1m.
