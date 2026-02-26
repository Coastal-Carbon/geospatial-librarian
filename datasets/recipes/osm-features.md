# OpenStreetMap Features in the Data Engine

## Overview

The Data Engine uses OpenStreetMap data as a **rasterized product**, not as raw
vector features. OSM vector geometries (buildings, roads, waterways, etc.) are
converted into a 30-band binary raster where each band is a presence/absence
mask for a single feature category. The result is a `uint8` array with shape
`[H, W, 1, 30]` that slots into the OlmoEarth sample format as an optional,
static modality.

This is fundamentally different from the vector OSM described in the profile.
The profile covers raw OpenStreetMap as it exists on the web: point, line, and
polygon geometries carrying rich attribute tags. The Data Engine transforms
those geometries into a fixed set of rasterized binary masks aligned to a
pixel grid, discarding the tag hierarchy and retaining only the 30 categories
listed below.

## The 30 Rasterized Bands

Each band is a binary mask (`0` = absent, `1` = present) for one OSM category.
The band ordering is defined in both the OlmoEarth metadata schema
(`OlmoEarthSamplesV1Metadata.tensor_column_schema`) and the standalone
rasterization script (`scripts/2025.12.16_osm_to_geotiff.py`):

| Band | Category              | Typical OSM source tags                              |
|------|-----------------------|------------------------------------------------------|
| 0    | aerialway_pylon       | `aerialway=pylon`                                    |
| 1    | aerodrome             | `aeroway=aerodrome`                                  |
| 2    | airstrip              | `aeroway=airstrip`                                   |
| 3    | amenity_fuel          | `amenity=fuel`                                       |
| 4    | building              | `building=*`                                         |
| 5    | chimney               | `man_made=chimney`                                   |
| 6    | communications_tower  | `man_made=communications_tower`                      |
| 7    | crane                 | `man_made=crane`                                     |
| 8    | flagpole              | `man_made=flagpole`                                  |
| 9    | fountain              | `amenity=fountain`                                   |
| 10   | generator_wind        | `generator:source=wind`                              |
| 11   | helipad               | `aeroway=helipad`                                    |
| 12   | highway               | `highway=*`                                          |
| 13   | leisure               | `leisure=*`                                          |
| 14   | lighthouse            | `man_made=lighthouse`                                |
| 15   | obelisk               | `man_made=obelisk`                                   |
| 16   | observatory           | `man_made=observatory`                               |
| 17   | parking               | `amenity=parking`                                    |
| 18   | petroleum_well        | `man_made=petroleum_well`                            |
| 19   | power_plant           | `power=plant`                                        |
| 20   | power_substation      | `power=substation`                                   |
| 21   | power_tower           | `power=tower`                                        |
| 22   | river                 | `waterway=river`                                     |
| 23   | runway                | `aeroway=runway`                                     |
| 24   | satellite_dish        | `man_made=satellite_dish`                             |
| 25   | silo                  | `man_made=silo`                                      |
| 26   | storage_tank          | `man_made=storage_tank`                              |
| 27   | taxiway               | `aeroway=taxiway`                                    |
| 28   | water_tower           | `man_made=water_tower`                               |
| 29   | works                 | `man_made=works`                                     |

## OlmoEarth Modality Registration

The rasterized OSM product is registered in the Data Engine as:

```
OlmoEarthModality.OPEN_STREET_MAP_RASTER
    olmo_name:     'openstreetmap_raster'
    default_dtype: numpy.dtype('uint8')
    n_bands:       30
    band_id_to_idx: None  (bands are addressed by integer index, not string ID)
```

It is a **static** modality (one timestamp dimension of size 1, not varying
across dates) with no-data value `0` (the default for `uint8`).

### Array shape in an OlmoEarth record

```
[edge_length_pixels, edge_length_pixels, 1, 30]
      H                   W              T   B
```

- `H` and `W` match the spatial chip size (e.g., 128 pixels at 10m GSD).
- `T = 1` because OSM features are treated as temporally static.
- `B = 30` for the 30 binary category masks.

### Parquet schema

In the parquet schema produced by `OlmoEarthSamplesV1Metadata.to_schema()`,
the OSM raster column is:

```
pa.field('openstreetmap_raster', pa.binary(), nullable=True)
```

It is **nullable** -- the modality is optional. A record can exist without it,
in which case the field is `None`.

## How it Fits Into the OlmoEarth Pipeline

### What the pipeline currently does

The current `OlmoEarthSampleV1Recipe` assembles records from STAC-based
satellite imagery collections (Sentinel-2, Sentinel-1, Landsat). The OSM
raster is **not** populated by the recipe's `execute()` method. Instead, it is
treated as an ancillary layer that is added to records through a separate
rasterization step.

The standalone script `scripts/2025.12.16_osm_to_geotiff.py` demonstrates the
full rasterization workflow:

1. Query the Overpass API for OSM features within a bounding box.
2. Project features from WGS84 to a local UTM zone.
3. Rasterize polygons, lines, and points onto a 30-band `uint8` array using
   `scikit-image` drawing functions.
4. Write the result as a GeoTIFF with 30 bands.

The default rasterization resolution is 2.5 m/pixel, producing 1024x1024 pixel
tiles. When integrated into an OlmoEarth record at 10m GSD, the arrays are
128x128 pixels.

### Incorporating OSM raster into a record

To include the OSM raster in an `OlmoEarthSamplesV1Record`, set the
`open_street_map_raster` attribute to a numpy array of shape
`[H, W, 1, 30]` with dtype `uint8`:

```python
record = OlmoEarthSamplesV1Record(
    sample_idx=0,
    latitude=37.76,
    longitude=-122.43,
    dates=(dt.date(2024, 6, 15),),
    sentinel_2_l2a=sen2_array,       # required, shape [H, W, T, 12]
    open_street_map_raster=osm_array, # optional, shape [H, W, 1, 30]
)
```

The `OlmoEarthSamplesV1Writer` serializes it as bytes alongside all other
modalities. The `OlmoEarthSamplesV1Reader` deserializes it using the shape
and dtype declared in the metadata's `tensor_column_schema`.

## Vector vs. Raster: Key Distinctions

| Aspect                | Vector OSM (profile)                              | Rasterized OSM (Data Engine)                     |
|-----------------------|---------------------------------------------------|--------------------------------------------------|
| Format                | Points, lines, polygons with attribute tags        | 30-band binary uint8 raster                      |
| Semantic richness     | Full OSM tagging hierarchy (building type, lanes)  | 30 fixed categories, presence/absence only        |
| Spatial model         | Exact vector geometry per feature                  | Pixel grid at fixed resolution (e.g., 2.5m, 10m) |
| Temporal model        | Continuously updated, per-feature history          | Static snapshot, single timestamp                 |
| Access method         | Overpass API, PBF downloads, Geofabrik extracts    | Pre-rasterized GeoTIFF or inline numpy array      |
| Use case              | GIS analysis, label extraction, map rendering      | ML model input alongside satellite imagery        |

## Practical Notes

- **Band sparsity**: Most tiles will have only a few bands with non-zero
  pixels. Urban areas will light up `building`, `highway`, `parking`, and
  `leisure`. Rural or ocean tiles may be entirely zero across all 30 bands.
- **Coverage gaps**: The same OSM coverage limitations from the profile apply.
  The rasterized product inherits whatever is (or is not) mapped in OSM for a
  given region.
- **No-data value**: For `uint8` modalities, the Data Engine uses `0` as the
  no-data sentinel (defined in `no_data_value_for_dtype`). Since the bands are
  binary masks where `0` means "feature absent" and `1` means "feature
  present", there is no ambiguity -- an all-zero band simply means no features
  of that category exist in the tile.
- **Resolution alignment**: When pairing with Sentinel-2 imagery at 10m, the
  OSM raster should be rasterized at the same 10m resolution so that pixel
  grids align without resampling.
