"""
OpenStreetMap Raster -- Recipe for using rasterized OSM features in OlmoEarth

This recipe demonstrates how to:
  1. Rasterize OSM vector features into a 30-band binary mask array
  2. Construct an OlmoEarthSamplesV1Record that includes the OSM raster modality
  3. Inspect the 30 category bands and visualize which features are present
  4. Write records with OSM raster data to parquet via the OlmoEarth writer

The 30 OSM categories (band index -> category name):
     0 = aerialway_pylon       15 = obelisk
     1 = aerodrome              16 = observatory
     2 = airstrip               17 = parking
     3 = amenity_fuel           18 = petroleum_well
     4 = building               19 = power_plant
     5 = chimney                20 = power_substation
     6 = communications_tower   21 = power_tower
     7 = crane                  22 = river
     8 = flagpole               23 = runway
     9 = fountain               24 = satellite_dish
    10 = generator_wind         25 = silo
    11 = helipad                26 = storage_tank
    12 = highway                27 = taxiway
    13 = leisure                28 = water_tower
    14 = lighthouse             29 = works
"""

import datetime as dt
from pathlib import Path

import numpy as np

from hum_ai.data_engine.formats.olmo_earth_samples_v1 import (
    OlmoEarthModality,
    OlmoEarthSamplesV1Metadata,
    OlmoEarthSamplesV1Record,
    OlmoEarthSamplesV1Writer,
)

# ---------------------------------------------------------------------------
# Constants: the 30 OSM categories used in the Data Engine
# ---------------------------------------------------------------------------

OSM_CATEGORIES = [
    "aerialway_pylon", "aerodrome", "airstrip", "amenity_fuel", "building",
    "chimney", "communications_tower", "crane", "flagpole", "fountain",
    "generator_wind", "helipad", "highway", "leisure", "lighthouse",
    "obelisk", "observatory", "parking", "petroleum_well", "power_plant",
    "power_substation", "power_tower", "river", "runway", "satellite_dish",
    "silo", "storage_tank", "taxiway", "water_tower", "works",
]

CATEGORY_TO_BAND = {name: idx for idx, name in enumerate(OSM_CATEGORIES)}


# ---------------------------------------------------------------------------
# 1. Create an OSM raster array from scratch (synthetic example)
# ---------------------------------------------------------------------------

def create_synthetic_osm_raster(
    edge_length_pixels: int = 128,
) -> np.ndarray:
    """Create a synthetic 30-band OSM raster for demonstration.

    In production, this array would come from rasterizing actual OSM data
    using the workflow in scripts/2025.12.16_osm_to_geotiff.py.

    Returns:
        numpy array of shape [H, W, 1, 30] with dtype uint8.
    """
    osm = np.zeros(
        (edge_length_pixels, edge_length_pixels, 1, 30),
        dtype=np.uint8,
    )

    # Simulate a building footprint in the center of the tile
    building_band = CATEGORY_TO_BAND["building"]
    osm[40:80, 50:90, 0, building_band] = 1

    # Simulate a road crossing the tile horizontally
    highway_band = CATEGORY_TO_BAND["highway"]
    osm[63:65, :, 0, highway_band] = 1

    # Simulate a parking lot adjacent to the building
    parking_band = CATEGORY_TO_BAND["parking"]
    osm[80:95, 50:75, 0, parking_band] = 1

    return osm


# ---------------------------------------------------------------------------
# 2. Build an OlmoEarth record that includes the OSM raster
# ---------------------------------------------------------------------------

def build_record_with_osm(
    latitude: float,
    longitude: float,
    sentinel_2_array: np.ndarray,
    osm_array: np.ndarray,
    date: dt.date = dt.date(2024, 6, 15),
) -> OlmoEarthSamplesV1Record:
    """Construct an OlmoEarthSamplesV1Record with OSM raster included.

    Args:
        latitude: Center latitude of the chip.
        longitude: Center longitude of the chip.
        sentinel_2_array: Sentinel-2 array, shape [H, W, T, 12], dtype uint16.
        osm_array: OSM raster array, shape [H, W, 1, 30], dtype uint8.
        date: Observation date for the Sentinel-2 imagery.

    Returns:
        An OlmoEarthSamplesV1Record with the open_street_map_raster field set.
    """
    return OlmoEarthSamplesV1Record(
        sample_idx=None,
        latitude=latitude,
        longitude=longitude,
        dates=(date,),
        sentinel_2_l2a=sentinel_2_array,
        open_street_map_raster=osm_array,
    )


# ---------------------------------------------------------------------------
# 3. Inspect which OSM categories have data in a record
# ---------------------------------------------------------------------------

def summarize_osm_bands(osm_array: np.ndarray) -> dict[str, int]:
    """Report the pixel count for each non-empty OSM category band.

    Args:
        osm_array: Array of shape [H, W, 1, 30] with dtype uint8.

    Returns:
        Dictionary mapping category name to non-zero pixel count,
        including only bands that have at least one pixel.
    """
    summary = {}
    for band_idx, category_name in enumerate(OSM_CATEGORIES):
        band_data = osm_array[:, :, 0, band_idx]
        pixel_count = int(np.count_nonzero(band_data))
        if pixel_count > 0:
            summary[category_name] = pixel_count
    return summary


# ---------------------------------------------------------------------------
# 4. Write records with OSM raster to parquet
# ---------------------------------------------------------------------------

def write_records_with_osm(
    records: list[OlmoEarthSamplesV1Record],
    output_dir: Path,
    dataset_name: str = "osm-raster-demo",
    edge_length_pixels: int = 128,
    gsd_m: float = 10.0,
    n_timestamps: int = 1,
) -> None:
    """Write OlmoEarth records (with OSM raster) to parquet.

    Args:
        records: List of OlmoEarthSamplesV1Record instances.
        output_dir: Directory to write parquet files into.
        dataset_name: Name for the dataset metadata.
        edge_length_pixels: Spatial edge length of each chip in pixels.
        gsd_m: Ground sample distance in meters.
        n_timestamps: Number of timestamps per record.
    """
    metadata = OlmoEarthSamplesV1Metadata(
        name=dataset_name,
        description="OlmoEarth samples with rasterized OpenStreetMap features",
        gsd_m=gsd_m,
        edge_length_pixels=edge_length_pixels,
        n_timestamps=n_timestamps,
    )

    writer = OlmoEarthSamplesV1Writer(metadata=metadata)
    output_dir.mkdir(parents=True, exist_ok=True)
    writer.write_metadata(output_dir)
    writer.write_partition(output_dir / "part-0.parquet", records)
    print(f"Wrote {len(records)} records to {output_dir}")


# ---------------------------------------------------------------------------
# 5. Read back and verify the OSM modality round-trips correctly
# ---------------------------------------------------------------------------

def verify_osm_modality_properties():
    """Print the OlmoEarth modality properties for the OSM raster."""
    modality = OlmoEarthModality.OPEN_STREET_MAP_RASTER

    print(f"Modality enum:  {modality.name}")
    print(f"OlmoEarth name: {modality.olmo_name}")
    print(f"Default dtype:  {modality.default_dtype}")
    print(f"Number of bands: {modality.n_bands()}")
    print(f"No-data value:  0  (uint8 default)")
    print()
    print("Band listing:")
    for idx, category in enumerate(OSM_CATEGORIES):
        print(f"  Band {idx:2d}: {category}")


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Print modality properties
    verify_osm_modality_properties()
    print()

    # Create a synthetic OSM raster
    edge_px = 128
    osm_raster = create_synthetic_osm_raster(edge_length_pixels=edge_px)
    print(f"OSM raster shape: {osm_raster.shape}, dtype: {osm_raster.dtype}")

    # Summarize which bands have data
    band_summary = summarize_osm_bands(osm_raster)
    print(f"\nNon-empty OSM bands ({len(band_summary)} of 30):")
    for category, count in sorted(band_summary.items(), key=lambda x: -x[1]):
        print(f"  {category:25s} {count:6d} pixels")

    # Build a record with a dummy Sentinel-2 array and the OSM raster
    dummy_sen2 = np.zeros((edge_px, edge_px, 1, 12), dtype=np.uint16)
    record = build_record_with_osm(
        latitude=37.76,
        longitude=-122.43,
        sentinel_2_array=dummy_sen2,
        osm_array=osm_raster,
    )

    print(f"\nRecord latitude:  {record.latitude}")
    print(f"Record longitude: {record.longitude}")
    print(f"OSM raster attached: {record.open_street_map_raster is not None}")
    print(f"OSM raster shape:    {record.open_street_map_raster.shape}")

    # To write to disk (uncomment to run):
    # write_records_with_osm([record], Path("/tmp/osm_demo_output"))
