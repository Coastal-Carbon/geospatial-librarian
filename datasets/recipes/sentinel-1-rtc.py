"""
Sentinel-1 RTC SAR Data -- Data Engine Recipe Examples

This module provides example configurations and code snippets for working
with Sentinel-1 RTC (Radiometric Terrain Corrected) SAR backscatter data
in the Data Engine.

Sentinel-1 is accessed from Microsoft Planetary Computer via the STAC API.
The collection ID is 'sentinel-1-rtc' and is represented in the Data Engine
by CollectionName.SENTINEL1.

Key characteristics:
    - Bands: VV (co-polarization) and VH (cross-polarization)
    - Resolution: 10m
    - Data type: float32 (linear power backscatter, gamma-nought)
    - Missing value: -32768.0
    - Cloud-penetrating: SAR is unaffected by clouds, haze, or darkness
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Imports from the Data Engine
# ---------------------------------------------------------------------------

from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import (
    SOURCE_INFO,
    CollectionInput,
    ObservationType,
    Range,
)

# For ImageChips v3 output format
from hum_ai.data_engine.formats.image_chips_v3.config import ImageChipsV3Configuration

# For OlmoEarth multi-modal output format
from hum_ai.data_engine.formats.olmo_earth_samples_v1.config import (
    OlmoEarthSamplesV1Configuration,
)
from hum_ai.data_engine.formats.olmo_earth_samples_v1.names import OlmoEarthModality

# ---------------------------------------------------------------------------
# 2. Inspect Sentinel-1 source metadata
# ---------------------------------------------------------------------------


def inspect_sentinel1_metadata() -> None:
    """Print the Data Engine's stored metadata for Sentinel-1.

    SOURCE_INFO contains band IDs, band names, resolution, data type,
    and missing value information for each collection.
    """
    s1_info = SOURCE_INFO[CollectionName.SENTINEL1]
    print("Sentinel-1 SOURCE_INFO:")
    for key, value in s1_info.items():
        print(f"  {key}: {value}")
    # Expected output:
    #   band_ids: ['vh', 'vv']
    #   band_names: ['VH', 'VV']
    #   requester_pays: False
    #   resolution: 10.0
    #   missing_value: -32768.0
    #   dtype: float32

    # The CollectionName enum carries the STAC catalog and collection IDs
    print(f"\nSTAC catalog ID: {CollectionName.SENTINEL1.catalog_id}")
    print(f"STAC collection ID: {CollectionName.SENTINEL1.id}")
    # Output:
    #   STAC catalog ID: microsoft-pc
    #   STAC collection ID: sentinel-1-rtc

    # OlmoEarth modality mapping
    modality = OlmoEarthModality.for_collection_name(CollectionName.SENTINEL1)
    print(f"\nOlmoEarth modality: {modality}")
    print(f"  olmo_name: {modality.olmo_name}")
    print(f"  n_bands: {modality.n_bands()}")
    print(f"  default_dtype: {modality.default_dtype}")
    # Output:
    #   OlmoEarth modality: OlmoEarthModality.SENTINEL_1
    #   olmo_name: sentinel1
    #   n_bands: 2
    #   default_dtype: float32


# ---------------------------------------------------------------------------
# 3. Create a CollectionInput for Sentinel-1
# ---------------------------------------------------------------------------


def create_sentinel1_collection_input() -> CollectionInput:
    """Create and return a CollectionInput configured for Sentinel-1 RTC.

    CollectionInput is the standard Data Engine object for specifying a data
    source, its bands, and its resolution. It is used by ProjectDefinition,
    ImageChipsV3Configuration, and OlmoEarthSamplesV1Configuration.

    Returns:
        A CollectionInput for Sentinel-1 with both VV and VH bands at 10m.
    """
    # Using default bands and resolution (pulled from SOURCE_INFO)
    s1_input_default = CollectionInput(
        collection_name=CollectionName.SENTINEL1,
    )
    # This is equivalent to the explicit version:
    s1_input_explicit = CollectionInput(
        collection_name=CollectionName.SENTINEL1,
        band_ids=('vv', 'vh'),
        resolution=10.0,
        # No catalog_filters needed -- SAR is cloud-independent
        catalog_filters=None,
    )
    return s1_input_explicit


# ---------------------------------------------------------------------------
# 4. Configure an ImageChips v3 pipeline for Sentinel-1
# ---------------------------------------------------------------------------


def create_image_chips_v3_config() -> ImageChipsV3Configuration:
    """Create an ImageChipsV3Configuration for Sentinel-1 SAR chips.

    ImageChips v3 is a single-collection chip format. Each chip is a
    small spatial tile extracted from a single observation date.

    The chip_size_m parameter controls the ground extent of each chip.
    At 10m resolution, a 640m chip produces 64x64 pixel arrays.
    At 10m resolution, a 1280m chip produces 128x128 pixel arrays.

    Returns:
        An ImageChipsV3Configuration for producing Sentinel-1 chips.
    """
    config = ImageChipsV3Configuration(
        destination_prefix=Path("/data/output/sentinel1_rtc_chips"),
        dataset_name="sentinel-1-rtc-image-chips",
        dataset_description=(
            "Sentinel-1 RTC SAR backscatter chips (VV + VH) at 10m resolution. "
            "Values are gamma-nought in linear power scale."
        ),
        chip_collection_input=CollectionInput(
            collection_name=CollectionName.SENTINEL1,
            band_ids=("vv", "vh"),
            resolution=10.0,
        ),
        chip_size_m=1280.0,  # 128x128 pixels at 10m
    )
    print(f"Chip size: {config.chip_size_pixels} x {config.chip_size_pixels} pixels")
    print(f"Bands: {config.chip_collection_input.band_ids}")
    print(f"Resolution: {config.chip_collection_input.resolution} m")
    return config


# ---------------------------------------------------------------------------
# 5. Configure an OlmoEarth multi-modal pipeline including Sentinel-1
# ---------------------------------------------------------------------------


def create_olmo_earth_config() -> OlmoEarthSamplesV1Configuration:
    """Create an OlmoEarthSamplesV1Configuration that includes Sentinel-1.

    The OlmoEarth format is designed for foundation model training and
    combines multiple Earth observation modalities into a single dataset.
    The default configuration already includes Sentinel-1 alongside
    Sentinel-2 and Landsat.

    In the OlmoEarth HDF5 archives, Sentinel-1 is stored under the
    modality key 'sentinel1' with band ordering: vv (index 0), vh (index 1).

    Returns:
        An OlmoEarthSamplesV1Configuration with the default multi-modal setup.
    """
    # The default collection_inputs already includes Sentinel-1.
    # Here we show the explicit version for clarity.
    config = OlmoEarthSamplesV1Configuration(
        destination_prefix=Path("/data/output/olmo_earth_multimodal"),
        dataset_name="multimodal-earth-observation",
        dataset_description="Multi-modal dataset with Sentinel-1, Sentinel-2, and Landsat",
        collection_inputs=(
            CollectionInput(
                collection_name=CollectionName.SENTINEL2,
                band_ids=(
                    "B02", "B03", "B04", "B08",   # 10m: Blue, Green, Red, NIR
                    "B05", "B06", "B07", "B8A",    # 20m: Red Edge, Narrow NIR
                    "B11", "B12",                   # 20m: SWIR 1, SWIR 2
                    "B01", "B09",                   # 60m: Coastal Aerosol, Water Vapour
                ),
                resolution=10.0,
                catalog_filters={"eo:cloud_cover": {"lt": 5}},
            ),
            CollectionInput(
                collection_name=CollectionName.SENTINEL1,
                band_ids=("vv", "vh"),
                resolution=10.0,
            ),
            CollectionInput(
                collection_name=CollectionName.LANDSAT,
                band_ids=("blue", "green", "red", "nir08", "swir16", "swir22", "lwir"),
                resolution=10.0,
            ),
        ),
        chip_size_m=1280.0,  # 128x128 pixels at 10m
    )
    return config


# ---------------------------------------------------------------------------
# 6. Observation type mapping reference
# ---------------------------------------------------------------------------


def print_observation_type_mapping() -> None:
    """Print the band-index-to-ObservationType mapping for Sentinel-1.

    The COLLECTION_BAND_MAP in ingredients.py maps (CollectionName, band_index)
    to ObservationType. This is used internally by the Data Engine to label
    each band in the output datasets.
    """
    from hum_ai.data_engine.ingredients import COLLECTION_BAND_MAP

    s1_map = COLLECTION_BAND_MAP[CollectionName.SENTINEL1]
    print("Sentinel-1 band index -> ObservationType:")
    for band_idx, obs_type in s1_map.items():
        print(f"  Band {band_idx}: {obs_type.name} ('{obs_type.value}')")
    # Output:
    #   Band 0: SENTINEL1_VV ('sentinel1_vv')
    #   Band 1: SENTINEL1_VH ('sentinel1_vh')


# ---------------------------------------------------------------------------
# 7. Converting backscatter values to decibels
# ---------------------------------------------------------------------------


def linear_to_db_example() -> None:
    """Demonstrate converting Sentinel-1 linear power to decibels.

    The RTC product stores backscatter as gamma-nought in linear power
    scale. Most analysis and visualization uses decibels (dB).

    Typical backscatter ranges (dB):
        Water:      -20 to -25 dB
        Bare soil:  -10 to -15 dB
        Vegetation:  -5 to -12 dB
        Urban:        0 to  -5 dB
    """
    import numpy as np

    # Simulated linear power values (gamma-nought)
    linear_backscatter = np.array([0.001, 0.01, 0.05, 0.1, 0.5], dtype=np.float32)

    # Mask the no-data value before conversion
    no_data = -32768.0
    valid_mask = linear_backscatter != no_data

    # Convert to decibels: dB = 10 * log10(linear)
    db_backscatter = np.full_like(linear_backscatter, np.nan)
    db_backscatter[valid_mask] = 10 * np.log10(linear_backscatter[valid_mask])

    print("Linear -> dB conversion:")
    for lin, db in zip(linear_backscatter, db_backscatter):
        print(f"  {lin:.4f} -> {db:.1f} dB")


# ---------------------------------------------------------------------------
# 8. Direct STAC access (outside Data Engine framework)
# ---------------------------------------------------------------------------


def direct_stac_access_example() -> None:
    """Show how to query Sentinel-1 RTC directly from the Planetary Computer
    STAC API using pystac-client.

    This bypasses the Data Engine entirely and is useful for ad-hoc
    exploration or when you need lower-level control over the search.
    """
    import pystac_client
    import planetary_computer

    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )

    # Search for Sentinel-1 RTC items over San Francisco Bay Area
    search = catalog.search(
        collections=["sentinel-1-rtc"],
        bbox=[-122.5, 37.5, -122.0, 38.0],
        datetime="2023-01-01/2023-06-01",
    )

    items = list(search.items())
    print(f"Found {len(items)} Sentinel-1 RTC items")

    if items:
        sample = items[0]
        print(f"  ID: {sample.id}")
        print(f"  Date: {sample.datetime}")
        print(f"  Assets: {list(sample.assets.keys())}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    print("=" * 60)
    print("Sentinel-1 RTC -- Data Engine Configuration Examples")
    print("=" * 60)

    print("\n--- 1. Source Metadata ---")
    inspect_sentinel1_metadata()

    print("\n--- 2. CollectionInput ---")
    ci = create_sentinel1_collection_input()
    print(f"Created: {ci}")

    print("\n--- 3. ImageChips v3 Config ---")
    chips_config = create_image_chips_v3_config()

    print("\n--- 4. OlmoEarth Config ---")
    olmo_config = create_olmo_earth_config()

    print("\n--- 5. Observation Type Mapping ---")
    print_observation_type_mapping()

    print("\n--- 6. Linear to dB Conversion ---")
    linear_to_db_example()
