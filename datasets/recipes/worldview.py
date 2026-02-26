"""WorldView Imagery — Executable Recipes

Practical code for working with Maxar WorldView 8-band multispectral
imagery through Hum's data engine.

Collection: worldview (stac-fastapi)
Bands: Coastal Blue, Blue, Green, Yellow, Red, Red Edge, NIR1, NIR2
Native resolution: ~1.84m multispectral, ~0.5m panchromatic
Data type: uint16, missing value: 0
"""

from __future__ import annotations

import numpy as np

from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import (
    COLLECTION_BAND_MAP,
    SOURCE_INFO,
    CollectionInput,
    ObservationType,
)


# ---------------------------------------------------------------------------
# Collection configuration helpers
# ---------------------------------------------------------------------------

def get_worldview_info() -> dict:
    """Return the SOURCE_INFO dict for WorldView."""
    return SOURCE_INFO[CollectionName.WORLDVIEW]


def get_worldview_band_map() -> dict[int, ObservationType]:
    """Return the band-index-to-ObservationType mapping for WorldView."""
    return COLLECTION_BAND_MAP[CollectionName.WORLDVIEW]


def print_worldview_summary() -> None:
    """Print a summary of WorldView collection configuration."""
    info = get_worldview_info()
    band_map = get_worldview_band_map()

    print("Maxar WorldView — Data Engine Configuration")
    print("=" * 50)
    print(f"  Collection ID : worldview")
    print(f"  Catalog       : stac-fastapi")
    print(f"  Resolution    : {info['resolution']}m (native MS)")
    print(f"  Data type     : {info['dtype']}")
    print(f"  Missing value : {info['missing_value']}")
    print(f"  Bands ({len(info['band_ids'])}):")
    for idx, band_id in enumerate(info['band_ids']):
        obs = band_map[idx]
        print(f"    [{idx}] {band_id:20s} -> {obs.value}")


# ---------------------------------------------------------------------------
# CollectionInput constructors
# ---------------------------------------------------------------------------

def worldview_all_bands(resolution: float = 1.84) -> CollectionInput:
    """CollectionInput for all 8 WorldView multispectral bands.

    Args:
        resolution: Target resolution in meters. Native is 1.84m,
            commercial products are commonly 2.0m.
    """
    return CollectionInput(
        collection_name=CollectionName.WORLDVIEW,
        resolution=resolution,
    )


def worldview_rgb(resolution: float = 2.0) -> CollectionInput:
    """CollectionInput for WorldView true-color RGB."""
    return CollectionInput(
        collection_name=CollectionName.WORLDVIEW,
        band_ids=('Red', 'Green', 'Blue'),
        resolution=resolution,
    )


def worldview_vegetation_bands(resolution: float = 2.0) -> CollectionInput:
    """CollectionInput for vegetation-focused analysis.

    Includes Red, Red Edge, NIR1, NIR2, Yellow, and Green — the bands
    most useful for vegetation indices and stress detection.
    """
    return CollectionInput(
        collection_name=CollectionName.WORLDVIEW,
        band_ids=('Green', 'Yellow', 'Red', 'Red Edge', 'Near-Infrared 1', 'Near-Infrared 2'),
        resolution=resolution,
    )


def worldview_coastal_bands(resolution: float = 2.0) -> CollectionInput:
    """CollectionInput for coastal/shallow-water analysis.

    Includes Coastal Blue, Blue, and Green — the bands that penetrate
    water most effectively.
    """
    return CollectionInput(
        collection_name=CollectionName.WORLDVIEW,
        band_ids=('Coastal Blue', 'Blue', 'Green'),
        resolution=resolution,
    )


# ---------------------------------------------------------------------------
# Spectral indices
# ---------------------------------------------------------------------------

def ndvi(red: np.ndarray, nir1: np.ndarray) -> np.ndarray:
    """Normalized Difference Vegetation Index using WorldView Red and NIR1.

    Args:
        red: Red band (660nm), uint16 or float
        nir1: Near-Infrared 1 band (835nm), uint16 or float

    Returns:
        NDVI array, float32, range [-1, 1], NaN where denominator is zero
    """
    r = red.astype(np.float32)
    n = nir1.astype(np.float32)
    denom = n + r
    return np.where(denom > 0, (n - r) / denom, np.nan)


def ndvi_nir2(red: np.ndarray, nir2: np.ndarray) -> np.ndarray:
    """NDVI using NIR2 — more robust under humid/hazy conditions.

    NIR2 (950nm) is less affected by atmospheric water vapor absorption
    than NIR1 (835nm). Values will differ from standard NDVI; do not
    mix NIR1-based and NIR2-based NDVI in the same analysis.

    Args:
        red: Red band (660nm), uint16 or float
        nir2: Near-Infrared 2 band (950nm), uint16 or float

    Returns:
        NDVI array, float32, range [-1, 1]
    """
    r = red.astype(np.float32)
    n = nir2.astype(np.float32)
    denom = n + r
    return np.where(denom > 0, (n - r) / denom, np.nan)


def ndwi(green: np.ndarray, nir1: np.ndarray) -> np.ndarray:
    """Normalized Difference Water Index (McFeeters, 1996).

    Positive values indicate open water. Uses Green and NIR1.

    Args:
        green: Green band (545nm)
        nir1: Near-Infrared 1 band (835nm)

    Returns:
        NDWI array, float32, range [-1, 1]
    """
    g = green.astype(np.float32)
    n = nir1.astype(np.float32)
    denom = g + n
    return np.where(denom > 0, (g - n) / denom, np.nan)


def ndre(red_edge: np.ndarray, nir1: np.ndarray) -> np.ndarray:
    """Normalized Difference Red Edge index.

    Sensitive to chlorophyll content and canopy structure. Often more
    responsive to vegetation vigor than NDVI in dense canopies.

    Args:
        red_edge: Red Edge band (730nm)
        nir1: Near-Infrared 1 band (835nm)

    Returns:
        NDRE array, float32, range [-1, 1]
    """
    re = red_edge.astype(np.float32)
    n = nir1.astype(np.float32)
    denom = n + re
    return np.where(denom > 0, (n - re) / denom, np.nan)


def yellowness_index(
    green: np.ndarray,
    yellow: np.ndarray,
    red: np.ndarray,
) -> np.ndarray:
    """Yellowness index exploiting WorldView's unique Yellow band.

    Detects vegetation senescence, chlorosis, and stress. Higher values
    indicate more yellowness relative to surrounding green/red reflectance.

    Args:
        green: Green band (545nm)
        yellow: Yellow band (610nm)
        red: Red band (660nm)

    Returns:
        Yellowness index array, float32
    """
    g = green.astype(np.float32)
    y = yellow.astype(np.float32)
    r = red.astype(np.float32)
    denom = g + r
    return np.where(denom > 0, (2.0 * y - g - r) / denom, np.nan)


def coastal_blue_ratio(
    coastal_blue: np.ndarray,
    blue: np.ndarray,
) -> np.ndarray:
    """Ratio of Coastal Blue to Blue for atmospheric/water analysis.

    Useful for assessing water turbidity and atmospheric scattering.
    Lower ratios can indicate turbid water or heavy aerosol loading.

    Args:
        coastal_blue: Coastal Blue band (425nm)
        blue: Blue band (480nm)

    Returns:
        Band ratio array, float32
    """
    cb = coastal_blue.astype(np.float32)
    b = blue.astype(np.float32)
    return np.where(b > 0, cb / b, np.nan)


# ---------------------------------------------------------------------------
# Bathymetry
# ---------------------------------------------------------------------------

def stumpf_ratio_bathymetry(
    coastal_blue: np.ndarray,
    green: np.ndarray,
    m0: float = 0.0,
    m1: float = 1.0,
) -> np.ndarray:
    """Stumpf et al. (2003) log-ratio relative bathymetry.

    Estimates relative water depth from the ratio of log reflectance in
    two bands with different water absorption characteristics. Must be
    calibrated against known depth points (m0, m1) for absolute depth.

    Only valid in clear, shallow water (typically <20-25m).

    Args:
        coastal_blue: Coastal Blue band (425nm)
        green: Green band (545nm)
        m0: Calibration offset (default 0.0 = uncalibrated)
        m1: Calibration gain (default 1.0 = uncalibrated)

    Returns:
        Relative depth array, float32. Uncalibrated unless m0/m1 are set.
    """
    cb = coastal_blue.astype(np.float32)
    g = green.astype(np.float32)

    cb_safe = np.where(cb > 0, cb, np.nan)
    g_safe = np.where(g > 0, g, np.nan)

    ratio = np.log(cb_safe) / np.log(g_safe)
    return m1 * ratio + m0


# ---------------------------------------------------------------------------
# Data quality helpers
# ---------------------------------------------------------------------------

def mask_missing(data: np.ndarray, missing_value: int = 0) -> np.ndarray:
    """Replace missing value pixels with NaN.

    WorldView uses 0 as its missing/no-data value. Be aware that valid
    dark pixels (deep shadows, deep water) can also have very low DN
    values near zero.

    Args:
        data: Image array (uint16 or float)
        missing_value: The no-data value to mask (default 0)

    Returns:
        Float32 array with missing pixels set to NaN
    """
    result = data.astype(np.float32)
    result[data == missing_value] = np.nan
    return result


def dn_to_toa_reflectance(
    dn: np.ndarray,
    abs_cal_factor: float,
    effective_bandwidth: float,
    sun_elevation_deg: float,
    earth_sun_distance: float = 1.0,
) -> np.ndarray:
    """Convert WorldView digital numbers to top-of-atmosphere reflectance.

    Requires per-band calibration coefficients from the image metadata
    (IMD or XML file). This is a simplified version — consult the Maxar
    technical documentation for the full radiometric calibration procedure.

    Args:
        dn: Raw digital number array (uint16)
        abs_cal_factor: Absolute calibration factor from metadata
        effective_bandwidth: Effective bandwidth from metadata (nm)
        sun_elevation_deg: Sun elevation angle in degrees from metadata
        earth_sun_distance: Earth-Sun distance in AU (default 1.0)

    Returns:
        TOA reflectance array, float32
    """
    import math

    # Step 1: DN to at-sensor radiance
    radiance = dn.astype(np.float32) * (abs_cal_factor / effective_bandwidth)

    # Step 2: Radiance to TOA reflectance (simplified)
    sun_zenith_rad = math.radians(90.0 - sun_elevation_deg)
    cos_sz = math.cos(sun_zenith_rad)

    # Note: A proper implementation would include the band-specific
    # solar irradiance (ESUN) value. This simplified version normalizes
    # by sun geometry only.
    toa = (radiance * math.pi * earth_sun_distance ** 2) / cos_sz

    return toa


# ---------------------------------------------------------------------------
# Multi-sensor fusion helpers
# ---------------------------------------------------------------------------

def worldview_sentinel2_inputs(
    wv_resolution: float = 2.0,
) -> tuple[CollectionInput, CollectionInput]:
    """Create paired CollectionInputs for WorldView + Sentinel-2 fusion.

    WorldView provides high-resolution visible/NIR. Sentinel-2 adds
    SWIR bands that WorldView lacks.

    Args:
        wv_resolution: WorldView target resolution in meters

    Returns:
        Tuple of (worldview_input, sentinel2_swir_input)
    """
    wv = CollectionInput(
        collection_name=CollectionName.WORLDVIEW,
        band_ids=('Red', 'Green', 'Blue', 'Near-Infrared 1'),
        resolution=wv_resolution,
    )
    s2_swir = CollectionInput(
        collection_name=CollectionName.SENTINEL2,
        band_ids=('B11', 'B12'),
        resolution=20.0,
    )
    return wv, s2_swir


# ---------------------------------------------------------------------------
# Main — print collection summary when run directly
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print_worldview_summary()
