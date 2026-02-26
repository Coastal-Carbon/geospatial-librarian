"""
NAIP (National Agriculture Imagery Program) -- Data Engine Recipe Examples

Demonstrates how to set up a CollectionInput for NAIP 4-band aerial imagery
and use it in Data Engine pipelines.

NAIP is accessed from the Earth Search AWS STAC catalog (element84).
The S3 bucket is requester-pays -- AWS charges the requesting account
for data transfer.

Bands (in order):
    0: Red   1: Green   2: Blue   3: NIR

Key details:
    - Resolution in the Data Engine: 2.5m (native GSD is 0.6m)
    - Data type: uint8 (0-255)
    - Missing value: 0
    - Coverage: Continental US only
    - Cadence: ~1-3 year revisit per state (leaf-on season)
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Imports from the Data Engine
# ---------------------------------------------------------------------------

from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import (
    COLLECTION_BAND_MAP,
    SOURCE_INFO,
    CollectionInput,
    ObservationType,
    Range,
)

# For ImageChips v3 output format
from hum_ai.data_engine.formats.image_chips_v3.config import ImageChipsV3Configuration


# ---------------------------------------------------------------------------
# 2. Inspect NAIP source metadata
# ---------------------------------------------------------------------------


def inspect_naip_metadata() -> None:
    """Print the Data Engine's stored metadata for NAIP.

    SOURCE_INFO contains band IDs, band names, resolution, data type,
    missing value, and requester_pays flag for each collection.
    """
    naip_info = SOURCE_INFO[CollectionName.NAIP]
    print("NAIP SOURCE_INFO:")
    for key, value in naip_info.items():
        print(f"  {key}: {value}")
    # Expected output:
    #   band_ids: ['Red', 'Green', 'Blue', 'NIR']
    #   band_names: ['red', 'green', 'blue', 'nir']
    #   requester_pays: True
    #   resolution: 2.5
    #   missing_value: 0
    #   dtype: uint8

    # The CollectionName enum carries the STAC catalog and collection IDs
    print(f"\nSTAC catalog ID: {CollectionName.NAIP.catalog_id}")
    print(f"STAC collection ID: {CollectionName.NAIP.id}")
    # Output:
    #   STAC catalog ID: earth-search-aws
    #   STAC collection ID: naip


# ---------------------------------------------------------------------------
# 3. Inspect the band-index-to-ObservationType mapping
# ---------------------------------------------------------------------------


def print_observation_type_mapping() -> None:
    """Print the band-index-to-ObservationType mapping for NAIP.

    The COLLECTION_BAND_MAP in ingredients.py maps (CollectionName, band_index)
    to ObservationType. This is used internally by the Data Engine to label
    each band in output datasets.

    Note the band order: Red is index 0, not Blue.
    """
    naip_map = COLLECTION_BAND_MAP[CollectionName.NAIP]
    print("NAIP band index -> ObservationType:")
    for band_idx, obs_type in naip_map.items():
        print(f"  Band {band_idx}: {obs_type.name} ('{obs_type.value}')")
    # Output:
    #   Band 0: NAIP_RED ('naip_red')
    #   Band 1: NAIP_GREEN ('naip_green')
    #   Band 2: NAIP_BLUE ('naip_blue')
    #   Band 3: NAIP_NIR ('naip_nir')


# ---------------------------------------------------------------------------
# 4. Create a CollectionInput -- all 4 bands at default resolution
# ---------------------------------------------------------------------------


def create_naip_collection_input() -> CollectionInput:
    """Create and return a CollectionInput configured for NAIP.

    CollectionInput is the standard Data Engine object for specifying a data
    source, its bands, and its resolution. It is used by ProjectDefinition,
    ImageChipsV3Configuration, and other pipeline configurations.

    Returns:
        A CollectionInput for NAIP with all 4 bands at 2.5m.
    """
    # Using defaults (pulled from SOURCE_INFO)
    naip_input_default = CollectionInput(
        collection_name=CollectionName.NAIP,
    )
    # This is equivalent to the explicit version:
    naip_input_explicit = CollectionInput(
        collection_name=CollectionName.NAIP,
        band_ids=('Red', 'Green', 'Blue', 'NIR'),
        resolution=2.5,
        # NAIP has no cloud cover metadata, so no catalog_filters
        catalog_filters=None,
    )
    print(f"Default bands: {naip_input_default.band_ids}")
    print(f"Default resolution: {naip_input_default.resolution} m")
    return naip_input_explicit


# ---------------------------------------------------------------------------
# 5. Create a CollectionInput -- RGB subset (no NIR)
# ---------------------------------------------------------------------------


naip_rgb = CollectionInput(
    collection_name=CollectionName.NAIP,
    band_ids=('Red', 'Green', 'Blue'),
)


# ---------------------------------------------------------------------------
# 6. Configure an ImageChips v3 pipeline for NAIP
# ---------------------------------------------------------------------------


def create_image_chips_v3_config() -> ImageChipsV3Configuration:
    """Create an ImageChipsV3Configuration for NAIP chips.

    ImageChips v3 is a single-collection chip format. Each chip is a
    small spatial tile extracted from a single observation date.

    At 2.5m resolution:
        - chip_size_m=320.0  -> 128x128 pixel chips
        - chip_size_m=640.0  -> 256x256 pixel chips

    Returns:
        An ImageChipsV3Configuration for producing NAIP chips.
    """
    config = ImageChipsV3Configuration(
        destination_prefix=Path("/data/output/naip_chips"),
        dataset_name="naip-rgbn-chips",
        dataset_description=(
            "NAIP 4-band (RGBN) image chips at 2.5m resolution. "
            "Values are uint8 (0-255). Continental US coverage only."
        ),
        chip_collection_input=CollectionInput(
            collection_name=CollectionName.NAIP,
            band_ids=("Red", "Green", "Blue", "NIR"),
            resolution=2.5,
        ),
        chip_size_m=320.0,  # 128x128 pixels at 2.5m
    )
    print(f"Chip size: {config.chip_size_pixels} x {config.chip_size_pixels} pixels")
    print(f"Bands: {config.chip_collection_input.band_ids}")
    print(f"Resolution: {config.chip_collection_input.resolution} m")
    return config


# ---------------------------------------------------------------------------
# 7. Use NAIP in a multi-source ProjectDefinition
# ---------------------------------------------------------------------------


def create_multi_source_project_definition(
    h3_cell_id: str,
    h3_boundary,
    utm_crs: str,
):
    """Create a ProjectDefinition combining NAIP with Sentinel-2 and Sentinel-1.

    This is a common pattern for US-based projects: NAIP provides very high
    spatial resolution (2.5m in the engine, 0.6m native), while Sentinel-2
    adds spectral breadth (12 bands incl. SWIR) and dense temporal coverage,
    and Sentinel-1 adds all-weather SAR observations.

    Args:
        h3_cell_id: H3 cell ID string defining the region of interest.
        h3_boundary: Shapely Polygon of the H3 cell boundary.
        utm_crs: UTM CRS string (e.g., 'EPSG:32615') for the region.
    """
    from hum_ai.data_engine.ingredients import ProjectDefinition

    definition = ProjectDefinition(
        name="NAIP + Sentinel Multi-Source",
        description="High-res NAIP paired with Sentinel-1 and Sentinel-2",
        collection_inputs=(
            CollectionInput(
                collection_name=CollectionName.NAIP,
                # No cloud filter -- NAIP items lack cloud cover metadata
                catalog_filters=None,
            ),
            CollectionInput(
                collection_name=CollectionName.SENTINEL2,
                catalog_filters={"eo:cloud_cover": {"lt": 5}},
            ),
            CollectionInput(
                collection_name=CollectionName.SENTINEL1,
                catalog_filters=None,
            ),
        ),
        region=h3_cell_id,
        geometry=h3_boundary,
        # Use a broad time range -- NAIP is acquired every 1-3 years
        time=Range(
            min=datetime(year=2017, month=1, day=1, tzinfo=UTC),
            max=datetime(year=2021, month=1, day=1, tzinfo=UTC),
        ),
        # Anchor chip grid to Sentinel-2 at 128 pixels (1280m at 10m)
        # NAIP chips will cover the same ground extent but at 2.5m -> 512 pixels
        chipsize={CollectionName.SENTINEL2: 128},
        spatial_ref=utm_crs,
        max_num_views=90,
        time_window=5,
        lazy_load=False,
    )
    return definition


# ---------------------------------------------------------------------------
# 8. Spectral index helpers
# ---------------------------------------------------------------------------


def ndvi(red, nir):
    """Normalized Difference Vegetation Index: (NIR - Red) / (NIR + Red)

    NAIP band mapping: Red = band 0, NIR = band 3.
    At 2.5m resolution, NDVI captures fine-scale vegetation patterns
    such as individual tree crowns and field-level crop variability.
    """
    return (nir - red) / (nir + red)


def ndwi(green, nir):
    """Normalized Difference Water Index: (Green - NIR) / (Green + NIR)

    NAIP band mapping: Green = band 1, NIR = band 3.
    Useful for delineating water bodies and wetland boundaries.
    """
    return (green - nir) / (green + nir)


# ---------------------------------------------------------------------------
# 9. Direct STAC access (outside Data Engine framework)
# ---------------------------------------------------------------------------


def direct_stac_access_example() -> None:
    """Show how to query NAIP directly from the Earth Search AWS STAC API.

    This bypasses the Data Engine entirely and is useful for ad-hoc
    exploration or when you need the native 0.6m resolution.

    Note: Because NAIP is on a requester-pays S3 bucket, you must
    have AWS credentials configured to actually read the asset data.
    The STAC metadata search itself does not require credentials.
    """
    import pystac_client

    catalog = pystac_client.Client.open(
        "https://earth-search.aws.element84.com/v1",
    )

    # Search for NAIP items over a location in Iowa
    search = catalog.search(
        collections=["naip"],
        bbox=[-93.8, 41.9, -93.5, 42.1],
        datetime="2020-01-01/2022-12-31",
    )

    items = list(search.items())
    print(f"Found {len(items)} NAIP items")

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
    print("NAIP -- Data Engine Configuration Examples")
    print("=" * 60)

    print("\n--- 1. Source Metadata ---")
    inspect_naip_metadata()

    print("\n--- 2. ObservationType Mapping ---")
    print_observation_type_mapping()

    print("\n--- 3. CollectionInput ---")
    ci = create_naip_collection_input()
    print(f"Created: {ci}")

    print("\n--- 4. RGB Subset ---")
    print(f"RGB-only bands: {naip_rgb.band_ids}")

    print("\n--- 5. ImageChips v3 Config ---")
    chips_config = create_image_chips_v3_config()
