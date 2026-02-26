"""
Landsat 8/9 Collection 2 Level-2 -- Data Engine Recipe Examples
===============================================================

Demonstrates how to set up a CollectionInput for Landsat 8/9 C2 L2
surface reflectance data and access it through the data engine.

Landsat is accessed from Microsoft Planetary Computer via the STAC API.
The collection ID is 'landsat-c2-l2' and is represented in the Data Engine
by CollectionName.LANDSAT.

Key characteristics:
    - Default bands: blue, green, red, nir08, swir16, swir22 (6 bands)
    - Resolution: 30m
    - Data type: uint16 (surface reflectance, scaled)
    - Thermal band (lwir) available separately in OlmoEarth format
    - Atmospherically corrected (Collection 2 Level-2)

Band order (0-based index in COLLECTION_BAND_MAP):
    0: blue (480nm)    1: green (560nm)   2: red (655nm)
    3: nir08 (865nm)   4: swir16 (1610nm) 5: swir22 (2200nm)
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

# For OlmoEarth multi-modal output format
from hum_ai.data_engine.formats.olmo_earth_samples_v1.config import (
    OlmoEarthSamplesV1Configuration,
)
from hum_ai.data_engine.formats.olmo_earth_samples_v1.names import OlmoEarthModality

# ---------------------------------------------------------------------------
# 2. Inspect Landsat source metadata
# ---------------------------------------------------------------------------


def inspect_landsat_metadata() -> None:
    """Print the Data Engine's stored metadata for Landsat 8/9.

    SOURCE_INFO contains band IDs, band names, resolution, and requester-pays
    information for each collection.
    """
    landsat_info = SOURCE_INFO[CollectionName.LANDSAT]
    print("Landsat SOURCE_INFO:")
    for key, value in landsat_info.items():
        print(f"  {key}: {value}")
    # Expected output:
    #   band_ids: ['blue', 'green', 'red', 'nir08', 'swir16', 'swir22']
    #   band_names: ['blue', 'green', 'red', 'nir08', 'swir16', 'swir22']
    #   requester_pays: False
    #   resolution: 30.0

    # The CollectionName enum carries the STAC catalog and collection IDs
    print(f"\nSTAC catalog ID: {CollectionName.LANDSAT.catalog_id}")
    print(f"STAC collection ID: {CollectionName.LANDSAT.id}")
    # Output:
    #   STAC catalog ID: microsoft-pc
    #   STAC collection ID: landsat-c2-l2

    # OlmoEarth modality mapping
    modality = OlmoEarthModality.for_collection_name(CollectionName.LANDSAT)
    print(f"\nOlmoEarth modality: {modality}")
    print(f"  olmo_name: {modality.olmo_name}")
    print(f"  n_bands: {modality.n_bands()}")
    print(f"  default_dtype: {modality.default_dtype}")
    # Output:
    #   OlmoEarth modality: OlmoEarthModality.LANDSAT
    #   olmo_name: landsat
    #   n_bands: 11
    #   default_dtype: uint16


# ---------------------------------------------------------------------------
# 3. Create a CollectionInput for Landsat
# ---------------------------------------------------------------------------


def create_landsat_collection_input() -> CollectionInput:
    """Create and return a CollectionInput configured for Landsat 8/9 C2 L2.

    CollectionInput is the standard Data Engine object for specifying a data
    source, its bands, and its resolution. It is used by ProjectDefinition,
    ImageChipsV3Configuration, and OlmoEarthSamplesV1Configuration.

    Returns:
        A CollectionInput for Landsat with all 6 default bands at 30m.
    """
    # Using default bands and resolution (pulled from SOURCE_INFO)
    landsat_input_default = CollectionInput(
        collection_name=CollectionName.LANDSAT,
    )
    # This is equivalent to the explicit version:
    landsat_input_explicit = CollectionInput(
        collection_name=CollectionName.LANDSAT,
        band_ids=('blue', 'green', 'red', 'nir08', 'swir16', 'swir22'),
        resolution=30.0,
        # No default catalog_filters for Landsat (unlike Sentinel-2).
        # Cloud masking is typically done in post-processing via QA_PIXEL.
        catalog_filters=None,
    )
    return landsat_input_explicit


# ---------------------------------------------------------------------------
# 4. Create a CollectionInput -- band subsets
# ---------------------------------------------------------------------------


# RGB + NIR only (e.g., for NDVI or true-color composites)
landsat_rgbn = CollectionInput(
    collection_name=CollectionName.LANDSAT,
    band_ids=('blue', 'green', 'red', 'nir08'),
    resolution=30.0,
)

# SWIR bands for moisture/burn analysis
landsat_swir = CollectionInput(
    collection_name=CollectionName.LANDSAT,
    band_ids=('nir08', 'swir16', 'swir22'),
    resolution=30.0,
)

# Including the thermal band (available in the OlmoEarth band map)
landsat_with_thermal = CollectionInput(
    collection_name=CollectionName.LANDSAT,
    band_ids=('blue', 'green', 'red', 'nir08', 'swir16', 'swir22', 'lwir'),
    resolution=30.0,
)


# ---------------------------------------------------------------------------
# 5. Configure an ImageChips v3 pipeline for Landsat
# ---------------------------------------------------------------------------


def create_image_chips_v3_config() -> ImageChipsV3Configuration:
    """Create an ImageChipsV3Configuration for Landsat surface reflectance chips.

    ImageChips v3 is a single-collection chip format. Each chip is a
    small spatial tile extracted from a single observation date.

    At 30m resolution:
        - chip_size_m=1920  -> 64x64 pixels
        - chip_size_m=3840  -> 128x128 pixels
        - chip_size_m=7680  -> 256x256 pixels

    Returns:
        An ImageChipsV3Configuration for producing Landsat chips.
    """
    config = ImageChipsV3Configuration(
        destination_prefix=Path("/data/output/landsat_c2l2_chips"),
        dataset_name="landsat-c2-l2-image-chips",
        dataset_description=(
            "Landsat 8/9 Collection 2 Level-2 surface reflectance chips "
            "(6 bands: blue, green, red, nir08, swir16, swir22) at 30m resolution."
        ),
        chip_collection_input=CollectionInput(
            collection_name=CollectionName.LANDSAT,
            band_ids=('blue', 'green', 'red', 'nir08', 'swir16', 'swir22'),
            resolution=30.0,
        ),
        chip_size_m=3840.0,  # 128x128 pixels at 30m
    )
    print(f"Chip size: {config.chip_size_pixels} x {config.chip_size_pixels} pixels")
    print(f"Bands: {config.chip_collection_input.band_ids}")
    print(f"Resolution: {config.chip_collection_input.resolution} m")
    return config


# ---------------------------------------------------------------------------
# 6. Configure an OlmoEarth multi-modal pipeline including Landsat
# ---------------------------------------------------------------------------


def create_olmo_earth_config() -> OlmoEarthSamplesV1Configuration:
    """Create an OlmoEarthSamplesV1Configuration that includes Landsat.

    The OlmoEarth format is designed for foundation model training and
    combines multiple Earth observation modalities into a single dataset.
    The default configuration already includes Landsat alongside
    Sentinel-2 and Sentinel-1.

    In the OlmoEarth HDF5 archives, Landsat is stored under the modality
    key 'landsat' with 11 band slots. The band index mapping is:
        1: blue, 2: green, 3: red, 4: nir08, 5: swir16, 6: swir22, 9: lwir

    Returns:
        An OlmoEarthSamplesV1Configuration with the default multi-modal setup.
    """
    # The default collection_inputs already includes Landsat.
    # Here we show the explicit version for clarity.
    config = OlmoEarthSamplesV1Configuration(
        destination_prefix=Path("/data/output/olmo_earth_multimodal"),
        dataset_name="multimodal-earth-observation",
        dataset_description="Multi-modal dataset with Sentinel-2, Sentinel-1, and Landsat",
        collection_inputs=(
            CollectionInput(
                collection_name=CollectionName.SENTINEL2,
                band_ids=(
                    "B02", "B03", "B04", "B08",  # 10m: Blue, Green, Red, NIR
                    "B05", "B06", "B07", "B8A",  # 20m: Red Edge, Narrow NIR
                    "B11", "B12",                 # 20m: SWIR 1, SWIR 2
                    "B01", "B09",                 # 60m: Coastal Aerosol, Water Vapour
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
                resolution=10.0,  # Resampled from native 30m to match Sentinel-2
            ),
        ),
        chip_size_m=1280.0,  # 128x128 pixels at 10m
    )
    return config


# ---------------------------------------------------------------------------
# 7. Observation type mapping reference
# ---------------------------------------------------------------------------


def print_observation_type_mapping() -> None:
    """Print the band-index-to-ObservationType mapping for Landsat.

    The COLLECTION_BAND_MAP in ingredients.py maps (CollectionName, band_index)
    to ObservationType. This is used internally by the Data Engine to label
    each band in the output datasets.
    """
    landsat_map = COLLECTION_BAND_MAP[CollectionName.LANDSAT]
    print("Landsat band index -> ObservationType:")
    for band_idx, obs_type in landsat_map.items():
        print(f"  Band {band_idx}: {obs_type.name} ('{obs_type.value}')")
    # Output:
    #   Band 0: LANDSAT_BLUE ('landsat_blue')
    #   Band 1: LANDSAT_GREEN ('landsat_green')
    #   Band 2: LANDSAT_RED ('landsat_red')
    #   Band 3: LANDSAT_NIR08 ('landsat_nir08')
    #   Band 4: LANDSAT_SWIR16 ('landsat_swir16')
    #   Band 5: LANDSAT_SWIR22 ('landsat_swir22')

    # Additional observation types not in the default band map:
    print("\nAdditional Landsat ObservationTypes:")
    print(f"  LANDSAT_COASTAL: '{ObservationType.LANDSAT_COASTAL.value}' (440nm, 30m)")
    print(f"  LANDSAT_LWIR11: '{ObservationType.LANDSAT_LWIR11.value}' (10900nm, 100m)")


# ---------------------------------------------------------------------------
# 8. Band metadata access
# ---------------------------------------------------------------------------


def print_band_metadata() -> None:
    """Print GSD and wavelength metadata for all Landsat observation types.

    Uses get_gsd() and get_wavelength() from ingredients.py to retrieve
    band-level metadata from OBSERVATION_BAND_METADATA.
    """
    from hum_ai.data_engine.ingredients import get_gsd, get_wavelength

    landsat_obs_types = [
        ObservationType.LANDSAT_COASTAL,
        ObservationType.LANDSAT_BLUE,
        ObservationType.LANDSAT_GREEN,
        ObservationType.LANDSAT_RED,
        ObservationType.LANDSAT_NIR08,
        ObservationType.LANDSAT_SWIR16,
        ObservationType.LANDSAT_SWIR22,
        ObservationType.LANDSAT_LWIR11,
    ]

    print("Landsat band metadata:")
    for obs_type in landsat_obs_types:
        gsd = get_gsd(obs_type)
        wl = get_wavelength(obs_type)
        print(f"  {obs_type.name}: GSD={gsd}m, wavelength={wl}nm")
    # Output:
    #   LANDSAT_COASTAL: GSD=30.0m, wavelength=440.0nm
    #   LANDSAT_BLUE: GSD=30.0m, wavelength=480.0nm
    #   LANDSAT_GREEN: GSD=30.0m, wavelength=560.0nm
    #   LANDSAT_RED: GSD=30.0m, wavelength=655.0nm
    #   LANDSAT_NIR08: GSD=30.0m, wavelength=865.0nm
    #   LANDSAT_SWIR16: GSD=30.0m, wavelength=1610.0nm
    #   LANDSAT_SWIR22: GSD=30.0m, wavelength=2200.0nm
    #   LANDSAT_LWIR11: GSD=100.0m, wavelength=10900.0nm


# ---------------------------------------------------------------------------
# 9. Spectral index helpers
# ---------------------------------------------------------------------------


def ndvi(red, nir):
    """Normalized Difference Vegetation Index: (NIR - Red) / (NIR + Red)

    Use bands: red, nir08
    """
    return (nir - red) / (nir + red)


def nbr(nir, swir22):
    """Normalized Burn Ratio: (NIR - SWIR2) / (NIR + SWIR2)

    Use bands: nir08, swir22
    Useful for mapping burn severity and fire-affected areas.
    """
    return (nir - swir22) / (nir + swir22)


def ndmi(nir, swir16):
    """Normalized Difference Moisture Index: (NIR - SWIR1) / (NIR + SWIR1)

    Use bands: nir08, swir16
    Sensitive to vegetation water content.
    """
    return (nir - swir16) / (nir + swir16)


def ndwi(green, nir):
    """Normalized Difference Water Index: (Green - NIR) / (Green + NIR)

    Use bands: green, nir08
    Positive values indicate water surfaces.
    """
    return (green - nir) / (green + nir)


def ndbi(swir16, nir):
    """Normalized Difference Built-up Index: (SWIR1 - NIR) / (SWIR1 + NIR)

    Use bands: swir16, nir08
    Highlights urban and built-up areas.
    """
    return (swir16 - nir) / (swir16 + nir)


# ---------------------------------------------------------------------------
# 10. Direct STAC access (outside Data Engine framework)
# ---------------------------------------------------------------------------


def direct_stac_access_example() -> None:
    """Show how to query Landsat C2 L2 directly from the Planetary Computer
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

    # Search for Landsat C2 L2 items over San Francisco Bay Area
    search = catalog.search(
        collections=["landsat-c2-l2"],
        bbox=[-122.5, 37.5, -122.0, 38.0],
        datetime="2023-01-01/2023-06-01",
    )

    items = list(search.items())
    print(f"Found {len(items)} Landsat C2 L2 items")

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
    print("Landsat 8/9 C2 L2 -- Data Engine Configuration Examples")
    print("=" * 60)

    print("\n--- 1. Source Metadata ---")
    inspect_landsat_metadata()

    print("\n--- 2. CollectionInput ---")
    ci = create_landsat_collection_input()
    print(f"Created: {ci}")

    print("\n--- 3. Band Subsets ---")
    print(f"RGB+NIR: {landsat_rgbn.band_ids}")
    print(f"SWIR subset: {landsat_swir.band_ids}")
    print(f"With thermal: {landsat_with_thermal.band_ids}")

    print("\n--- 4. ImageChips v3 Config ---")
    chips_config = create_image_chips_v3_config()

    print("\n--- 5. OlmoEarth Config ---")
    olmo_config = create_olmo_earth_config()

    print("\n--- 6. Observation Type Mapping ---")
    print_observation_type_mapping()

    print("\n--- 7. Band Metadata ---")
    print_band_metadata()
