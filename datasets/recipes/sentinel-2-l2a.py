"""
Sentinel-2 L2A Surface Reflectance -- Data Engine Recipe Examples

This module provides example configurations and code snippets for working
with Sentinel-2 Level-2A atmospherically corrected surface reflectance data
in the Data Engine.

Sentinel-2 is accessed from Microsoft Planetary Computer via the STAC API.
The collection ID is 'sentinel-2-l2a' and is represented in the Data Engine
by CollectionName.SENTINEL2. It is the preferred reference collection and
the default data source for both ImageChips v3 and OlmoEarth formats.

Key characteristics:
    - Bands: 12 spectral bands from coastal aerosol (443nm) to SWIR (2190nm)
    - Resolution: 10m default (native varies: 10m, 20m, 60m by band)
    - Data type: uint16 (surface reflectance scaled by 10,000)
    - Missing value: 0
    - Band thresholds: (0, 10_000)
    - Cloud cover filtering: default < 5% via CATALOG_FILTERS
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Imports from the Data Engine
# ---------------------------------------------------------------------------

from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import (
    CATALOG_FILTERS,
    COLLECTION_BAND_MAP,
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

# Spatial configuration classes
from hum_ai.data_engine.spatial_config import (
    BaseGeometrySpatialConfig,
    H3CellSpatialConfig,
)

# Temporal configuration and sampling strategy classes
from hum_ai.data_engine.temporal_config import (
    LatestPrecedingTemporalConfig,
    MonthlyMiddleTemporalConfig,
)
from hum_ai.data_engine.temporal_sampling_strategies import (
    LatestPreceding,
    MonthlyMiddle,
)

# The plan function that wires spatial + temporal + format configs into a recipe
from hum_ai.data_engine.plan import make_a_plan


# ---------------------------------------------------------------------------
# 2. Inspect Sentinel-2 source metadata
# ---------------------------------------------------------------------------


def inspect_sentinel2_metadata() -> None:
    """Print the Data Engine's stored metadata for Sentinel-2.

    SOURCE_INFO contains band IDs, band names, resolution, data type,
    missing value, and band threshold information for each collection.
    """
    s2_info = SOURCE_INFO[CollectionName.SENTINEL2]
    print("Sentinel-2 SOURCE_INFO:")
    for key, value in s2_info.items():
        print(f"  {key}: {value}")
    # Expected output:
    #   band_ids: ['B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B8A', 'B09', 'B11', 'B12']
    #   band_names: ['coastal', 'blue', 'green', 'red', 'red_edge1', 'red_edge2', 'red_edge3', 'nir', 'red_edge4', 'water_vapor', 'swir1', 'swir2']
    #   requester_pays: False
    #   resolution: 10.0
    #   missing_value: 0
    #   dtype: uint16
    #   band_thresholds: (0, 10000)

    # The CollectionName enum carries the STAC catalog and collection IDs
    print(f"\nSTAC catalog ID: {CollectionName.SENTINEL2.catalog_id}")
    print(f"STAC collection ID: {CollectionName.SENTINEL2.id}")
    # Output:
    #   STAC catalog ID: microsoft-pc
    #   STAC collection ID: sentinel-2-l2a

    # Sentinel-2 is the first entry in preferred_reference_collections
    preferred = CollectionName.preferred_reference_collections()
    print(f"\nPreferred reference collections: {preferred}")
    # Output: (CollectionName.SENTINEL2, CollectionName.SENTINEL1, CollectionName.LANDSAT, CollectionName.NAIP)

    # Default catalog filters for Sentinel-2
    print(f"\nDefault CATALOG_FILTERS: {CATALOG_FILTERS.get(CollectionName.SENTINEL2)}")
    # Output: {'eo:cloud_cover': {'lt': 5}}

    # OlmoEarth modality mapping
    modality = OlmoEarthModality.for_collection_name(CollectionName.SENTINEL2)
    print(f"\nOlmoEarth modality: {modality}")
    print(f"  olmo_name: {modality.olmo_name}")
    print(f"  n_bands: {modality.n_bands()}")
    print(f"  default_dtype: {modality.default_dtype}")
    # Output:
    #   OlmoEarth modality: OlmoEarthModality.SENTINEL_2_L2A
    #   olmo_name: sentinel2_l2a
    #   n_bands: 12
    #   default_dtype: uint16


# ---------------------------------------------------------------------------
# 3. Create a CollectionInput for Sentinel-2
# ---------------------------------------------------------------------------


def create_sentinel2_collection_input() -> CollectionInput:
    """Create and return a CollectionInput configured for Sentinel-2 L2A.

    CollectionInput is the standard Data Engine object for specifying a data
    source, its bands, and its resolution. It is used by
    ImageChipsV3Configuration, OlmoEarthSamplesV1Configuration, and
    ProjectDefinition.

    Returns:
        A CollectionInput for Sentinel-2 with BGRN bands at 10m.
    """
    # Using defaults: all 12 bands at 10m, no catalog filters
    s2_input_default = CollectionInput(
        collection_name=CollectionName.SENTINEL2,
    )
    # Default band_ids will be: ('B01','B02','B03','B04','B05','B06','B07','B08','B8A','B09','B11','B12')
    # Default resolution will be: 10.0

    # Common configuration: just the four 10m-native bands with cloud filtering
    s2_input_bgrn = CollectionInput(
        collection_name=CollectionName.SENTINEL2,
        band_ids=('B02', 'B03', 'B04', 'B08'),  # Blue, Green, Red, NIR
        resolution=10.0,
        catalog_filters={'eo:cloud_cover': {'lt': 5}},
    )

    # Full 12-band configuration (as used in OlmoEarth defaults)
    s2_input_full = CollectionInput(
        collection_name=CollectionName.SENTINEL2,
        band_ids=(
            'B02', 'B03', 'B04', 'B08',  # 10m native: Blue, Green, Red, NIR
            'B05', 'B06', 'B07', 'B8A',  # 20m native: Red Edge 1-3, Narrow NIR
            'B11', 'B12',                  # 20m native: SWIR 1, SWIR 2
            'B01', 'B09',                  # 60m native: Coastal Aerosol, Water Vapour
        ),
        resolution=10.0,
        catalog_filters={'eo:cloud_cover': {'lt': 5}},
    )

    return s2_input_bgrn


# ---------------------------------------------------------------------------
# 4. Configure an ImageChips v3 pipeline for Sentinel-2
# ---------------------------------------------------------------------------


def create_image_chips_v3_config() -> ImageChipsV3Configuration:
    """Create an ImageChipsV3Configuration for Sentinel-2 chips.

    ImageChips v3 is a single-collection chip format. Each chip is a
    small spatial tile extracted from a single observation date.

    The chip_size_m parameter controls the ground extent of each chip.
    At 10m resolution, a 640m chip produces 64x64 pixel arrays.
    At 10m resolution, a 1280m chip produces 128x128 pixel arrays.

    The default ImageChipsV3Configuration already uses Sentinel-2 with
    BGRN bands (B02, B03, B04, B08) at 10m and cloud cover < 25%.

    Returns:
        An ImageChipsV3Configuration for producing Sentinel-2 chips.
    """
    # Option A: Use the built-in default (Sentinel-2 BGRN, 10m, cloud < 25%)
    config_default = ImageChipsV3Configuration(
        destination_prefix=Path("/data/output/sentinel2_chips_default"),
        dataset_name="sentinel-2-l2a-bgrn-chips",
        dataset_description="Sentinel-2 L2A BGRN image chips at 10m resolution",
    )
    # The default chip_collection_input is:
    #   CollectionInput(
    #       collection_name=CollectionName.SENTINEL2,
    #       band_ids=('B02', 'B03', 'B04', 'B08'),
    #       resolution=10.0,
    #       catalog_filters={'eo:cloud_cover': {'lt': 25}},
    #   )
    print(f"Default chip size: {config_default.chip_size_pixels}x{config_default.chip_size_pixels} pixels")
    # Output: Default chip size: 64x64 pixels (640m / 10m)

    # Option B: Explicit 12-band configuration with stricter cloud filter
    config_12band = ImageChipsV3Configuration(
        destination_prefix=Path("/data/output/sentinel2_chips_12band"),
        dataset_name="sentinel-2-l2a-12band-chips",
        dataset_description=(
            "Sentinel-2 L2A 12-band surface reflectance chips. "
            "Values are scaled reflectance (0-10000) in uint16."
        ),
        chip_collection_input=CollectionInput(
            collection_name=CollectionName.SENTINEL2,
            band_ids=(
                'B02', 'B03', 'B04', 'B08',
                'B05', 'B06', 'B07', 'B8A',
                'B11', 'B12',
                'B01', 'B09',
            ),
            resolution=10.0,
            catalog_filters={'eo:cloud_cover': {'lt': 5}},
        ),
        chip_size_m=1280.0,  # 128x128 pixels at 10m
    )
    print(f"12-band chip size: {config_12band.chip_size_pixels}x{config_12band.chip_size_pixels} pixels")
    print(f"Bands: {config_12band.chip_collection_input.band_ids}")
    print(f"Resolution: {config_12band.chip_collection_input.resolution} m")
    return config_12band


# ---------------------------------------------------------------------------
# 5. Configure an OlmoEarth multi-modal pipeline including Sentinel-2
# ---------------------------------------------------------------------------


def create_olmo_earth_config() -> OlmoEarthSamplesV1Configuration:
    """Create an OlmoEarthSamplesV1Configuration that includes Sentinel-2.

    The OlmoEarth format is designed for foundation model training and
    combines multiple Earth observation modalities into a single dataset.
    The default configuration includes Sentinel-2 (12 bands), Sentinel-1
    (2 bands), and Landsat (7 bands), all resampled to 10m.

    In the OlmoEarth HDF5 archives, Sentinel-2 is stored under the modality
    key 'sentinel2_l2a' with a custom band index ordering:
        B02=0, B03=1, B04=2, B08=3 (10m bands first)
        B05=4, B06=5, B07=6, B8A=7, B11=8, B12=9 (20m bands)
        B01=10, B09=11 (60m bands)

    All collection inputs must share the same resolution (enforced by
    the collection_inputs_one_resolution validator).

    Returns:
        An OlmoEarthSamplesV1Configuration with the default multi-modal setup.
    """
    # Using defaults: the default collection_inputs tuple already includes
    # Sentinel-2 with all 12 bands at 10m and cloud cover < 5%
    config_defaults = OlmoEarthSamplesV1Configuration(
        destination_prefix=Path("/data/output/olmo_earth_multimodal"),
        dataset_name="multimodal-earth-observation",
        dataset_description="Multi-modal dataset with Sentinel-2, Sentinel-1, and Landsat",
    )

    # Explicit version showing all collection inputs
    config_explicit = OlmoEarthSamplesV1Configuration(
        destination_prefix=Path("/data/output/olmo_earth_multimodal"),
        dataset_name="multimodal-earth-observation",
        dataset_description="Multi-modal dataset with Sentinel-2, Sentinel-1, and Landsat",
        collection_inputs=(
            CollectionInput(
                collection_name=CollectionName.SENTINEL2,
                band_ids=(
                    'B02', 'B03', 'B04', 'B08',  # 10m: Blue, Green, Red, NIR
                    'B05', 'B06', 'B07', 'B8A',  # 20m: Red Edge 1-3, Narrow NIR
                    'B11', 'B12',                  # 20m: SWIR 1, SWIR 2
                    'B01', 'B09',                  # 60m: Coastal Aerosol, Water Vapour
                ),
                resolution=10.0,
                catalog_filters={'eo:cloud_cover': {'lt': 5}},
            ),
            CollectionInput(
                collection_name=CollectionName.SENTINEL1,
                band_ids=('vv', 'vh'),
                resolution=10.0,
            ),
            CollectionInput(
                collection_name=CollectionName.LANDSAT,
                band_ids=('blue', 'green', 'red', 'nir08', 'swir16', 'swir22', 'lwir'),
                resolution=10.0,
            ),
        ),
        chip_size_m=1280.0,  # 128x128 pixels at 10m
    )
    return config_explicit


# ---------------------------------------------------------------------------
# 6. Set up spatial and temporal configurations
# ---------------------------------------------------------------------------


def create_spatial_configs() -> None:
    """Demonstrate the two spatial configuration options.

    H3CellSpatialConfig uses an H3 hexagonal grid cell ID to define the
    area of interest. BaseGeometrySpatialConfig accepts a Shapely
    Point or Polygon geometry directly.
    """
    from shapely import Point, Polygon

    # Option A: H3 cell -- good for systematic global tiling
    spatial_h3 = H3CellSpatialConfig(h3_cell_id='882ab2590bfffff')
    scenes_h3 = spatial_h3.scenes()
    print(f"H3 spatial config produces {len(scenes_h3)} scene(s)")

    # Option B: Point geometry -- produces a single chip centered at the point
    spatial_point = BaseGeometrySpatialConfig(geometry=Point(-90.0, 32.0))
    scenes_point = spatial_point.scenes()
    print(f"Point spatial config produces {len(scenes_point)} scene(s)")

    # Option C: Polygon geometry -- produces chips covering the polygon extent
    polygon = Polygon([(-90.1, 31.9), (-89.9, 31.9), (-89.9, 32.1), (-90.1, 32.1)])
    spatial_polygon = BaseGeometrySpatialConfig(geometry=polygon)
    scenes_polygon = spatial_polygon.scenes()
    print(f"Polygon spatial config produces {len(scenes_polygon)} scene(s)")


def create_temporal_configs() -> None:
    """Demonstrate the temporal configuration options relevant to Sentinel-2.

    LatestPrecedingTemporalConfig finds the most recent cloud-free image
    before each specified key date (within a tolerance window).

    MonthlyMiddleTemporalConfig selects one image per month at the
    approximate middle of each month, for foundation model pretraining.
    """
    # Option A: Latest preceding -- find closest image before each key date
    temporal_latest = LatestPrecedingTemporalConfig(
        latest_preceding=LatestPreceding(
            key_dates=(dt.date(2023, 6, 1), dt.date(2023, 9, 1)),
            max_days_before=30,
        )
    )
    print(f"Search range: {temporal_latest.time_range}")
    # The search range expands backwards by max_days_before from the earliest key date

    # Option B: Monthly middle -- one sample per month per year
    temporal_monthly = MonthlyMiddleTemporalConfig(
        monthly_middle=MonthlyMiddle(
            start_year=2020,
            end_year=2023,
            tolerance_days=15,  # only consider items within +/- 15 days of month middle
        )
    )
    print(f"Search range: {temporal_monthly.time_range}")
    # Covers 2020-01-01 through 2023-12-31


# ---------------------------------------------------------------------------
# 7. Run a pipeline using make_a_plan
# ---------------------------------------------------------------------------


def run_pipeline_example() -> None:
    """Demonstrate the full pipeline: spatial + temporal + format -> recipe -> execute.

    make_a_plan() takes spatial, temporal, and format configuration objects,
    performs a STAC search to build a manifest of available items, then
    constructs a WriteRecords recipe that can be executed or serialized.

    For OlmoEarth with LatestPreceding temporal strategy, the plan function
    matches on format_name='OlmoEarthSamples', version=1,
    strategy_type='latest_preceding'.

    For OlmoEarth with MonthlyMiddle, it matches on 'monthly_middle'.

    For ImageChips v3, the temporal strategy must be ImageChipsTakeAll
    (matched as 'image_chips_take_all' in the plan function).
    """
    # --- OlmoEarth with LatestPreceding ---
    spatial = H3CellSpatialConfig(h3_cell_id='882ab2590bfffff')

    temporal = LatestPrecedingTemporalConfig(
        latest_preceding=LatestPreceding(
            key_dates=(dt.date(2023, 6, 1),),
            max_days_before=30,
        )
    )

    format_config = OlmoEarthSamplesV1Configuration(
        destination_prefix=Path("/data/output/pipeline_test"),
        dataset_name="sentinel2-pipeline-test",
        dataset_description="Pipeline test with Sentinel-2 L2A",
        # Uses default collection_inputs (Sentinel-2 + Sentinel-1 + Landsat)
    )

    # make_a_plan searches STAC, builds a manifest, and returns a WriteRecords recipe
    recipe = make_a_plan(
        spatial_config=spatial,
        temporal_config=temporal,
        format_config=format_config,
    )

    # Execute the recipe (downloads data, creates chips, writes output)
    recipe.execute()

    # Alternatively, serialize the recipe for later execution (e.g., on AWS Lambda)
    recipe.write_to_file(Path("/data/output/recipe.json"), pretty=False)


# ---------------------------------------------------------------------------
# 8. Observation type mapping reference
# ---------------------------------------------------------------------------


def print_observation_type_mapping() -> None:
    """Print the band-index-to-ObservationType mapping for Sentinel-2.

    The COLLECTION_BAND_MAP in ingredients.py maps (CollectionName, band_index)
    to ObservationType. This is used internally by the Data Engine to label
    each band in the output datasets.
    """
    s2_map = COLLECTION_BAND_MAP[CollectionName.SENTINEL2]
    print("Sentinel-2 band index -> ObservationType:")
    for band_idx, obs_type in s2_map.items():
        print(f"  Band {band_idx}: {obs_type.name} ('{obs_type.value}')")
    # Output:
    #   Band 0: SENTINEL2_COASTAL ('sentinel2_coastal')
    #   Band 1: SENTINEL2_BLUE ('sentinel2_blue')
    #   Band 2: SENTINEL2_GREEN ('sentinel2_green')
    #   Band 3: SENTINEL2_RED ('sentinel2_red')
    #   Band 4: SENTINEL2_RED_EDGE1 ('sentinel2_red_edge1')
    #   Band 5: SENTINEL2_RED_EDGE2 ('sentinel2_red_edge2')
    #   Band 6: SENTINEL2_RED_EDGE3 ('sentinel2_red_edge3')
    #   Band 7: SENTINEL2_NIR ('sentinel2_nir')
    #   Band 8: SENTINEL2_RED_EDGE4 ('sentinel2_red_edge4')
    #   Band 9: SENTINEL2_WATER_VAPOR ('sentinel2_water_vapor')
    #   Band 10: SENTINEL2_SWIR1 ('sentinel2_swir1')
    #   Band 11: SENTINEL2_SWIR2 ('sentinel2_swir2')


# ---------------------------------------------------------------------------
# 9. OlmoEarth band index mapping
# ---------------------------------------------------------------------------


def print_olmo_earth_band_mapping() -> None:
    """Print the OlmoEarth-specific band index mapping for Sentinel-2.

    The OlmoEarth format uses a custom band ordering defined in
    _SEN2_BAND_ID_TO_IDX (in olmo_earth_samples_v1/names.py).
    This places the 10m bands first, then 20m, then 60m.
    """
    modality = OlmoEarthModality.SENTINEL_2_L2A
    band_ids = ['B02', 'B03', 'B04', 'B08', 'B05', 'B06', 'B07', 'B8A', 'B11', 'B12', 'B01', 'B09']

    print(f"OlmoEarth modality: {modality.olmo_name}")
    print(f"Number of bands: {modality.n_bands()}")
    print(f"Default dtype: {modality.default_dtype}")
    print("\nBand ID -> OlmoEarth index:")
    for band_id in band_ids:
        idx = modality.band_index(band_id)
        print(f"  {band_id}: index {idx}")
    # Output:
    #   B02: index 0    (Blue, 10m)
    #   B03: index 1    (Green, 10m)
    #   B04: index 2    (Red, 10m)
    #   B08: index 3    (NIR, 10m)
    #   B05: index 4    (Red Edge 1, 20m)
    #   B06: index 5    (Red Edge 2, 20m)
    #   B07: index 6    (Red Edge 3, 20m)
    #   B8A: index 7    (Narrow NIR, 20m)
    #   B11: index 8    (SWIR 1, 20m)
    #   B12: index 9    (SWIR 2, 20m)
    #   B01: index 10   (Coastal Aerosol, 60m)
    #   B09: index 11   (Water Vapour, 60m)


# ---------------------------------------------------------------------------
# 10. Direct STAC access (outside Data Engine framework)
# ---------------------------------------------------------------------------


def direct_stac_access_example() -> None:
    """Show how to query Sentinel-2 L2A directly from the Planetary Computer
    STAC API using pystac-client.

    This bypasses the Data Engine entirely and is useful for ad-hoc
    exploration or when you need lower-level control over the search.
    Cloud cover and nodata percentage filters are applied via the
    query parameter.
    """
    import pystac_client
    import planetary_computer

    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )

    # Search for Sentinel-2 L2A items over San Francisco Bay Area
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=[-122.5, 37.5, -122.0, 38.0],
        datetime="2023-01-01/2023-06-01",
        query={
            "eo:cloud_cover": {"lt": 5},
            "s2:nodata_pixel_percentage": {"lte": 2},
        },
    )

    items = list(search.items())
    print(f"Found {len(items)} Sentinel-2 L2A items")

    if items:
        sample = items[0]
        print(f"  ID: {sample.id}")
        print(f"  Date: {sample.datetime}")
        print(f"  Cloud cover: {sample.properties.get('eo:cloud_cover')}%")
        print(f"  Assets: {list(sample.assets.keys())}")


# ---------------------------------------------------------------------------
# 11. Reflectance value handling
# ---------------------------------------------------------------------------


def reflectance_value_example() -> None:
    """Demonstrate how to interpret Sentinel-2 L2A reflectance values.

    Sentinel-2 L2A surface reflectance values are stored as uint16 integers
    scaled by 10,000. A stored value of 1500 represents a reflectance of 0.15.

    The band_thresholds in SOURCE_INFO define the valid range: (0, 10_000).
    The missing_value is 0.
    """
    import numpy as np

    # Simulated pixel values from a Sentinel-2 chip (uint16)
    raw_values = np.array([0, 500, 1500, 3000, 8000, 10000], dtype=np.uint16)

    # Mask the no-data value (0)
    no_data = SOURCE_INFO[CollectionName.SENTINEL2]['missing_value']
    valid_mask = raw_values != no_data

    # Convert to physical reflectance (0.0 to 1.0)
    reflectance = np.full(raw_values.shape, np.nan, dtype=np.float32)
    reflectance[valid_mask] = raw_values[valid_mask].astype(np.float32) / 10_000.0

    print("Sentinel-2 reflectance conversion (uint16 -> float):")
    for raw, refl in zip(raw_values, reflectance):
        print(f"  {raw:5d} -> {refl:.4f}" if not np.isnan(refl) else f"  {raw:5d} -> no-data")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    print("=" * 60)
    print("Sentinel-2 L2A -- Data Engine Configuration Examples")
    print("=" * 60)

    print("\n--- 1. Source Metadata ---")
    inspect_sentinel2_metadata()

    print("\n--- 2. CollectionInput ---")
    ci = create_sentinel2_collection_input()
    print(f"Created: {ci}")

    print("\n--- 3. ImageChips v3 Config ---")
    chips_config = create_image_chips_v3_config()

    print("\n--- 4. OlmoEarth Config ---")
    olmo_config = create_olmo_earth_config()

    print("\n--- 5. Spatial Configs ---")
    create_spatial_configs()

    print("\n--- 6. Temporal Configs ---")
    create_temporal_configs()

    print("\n--- 7. Observation Type Mapping ---")
    print_observation_type_mapping()

    print("\n--- 8. OlmoEarth Band Mapping ---")
    print_olmo_earth_band_mapping()

    print("\n--- 9. Reflectance Values ---")
    reflectance_value_example()
