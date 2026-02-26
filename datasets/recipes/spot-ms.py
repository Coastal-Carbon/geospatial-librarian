"""SPOT Multispectral — Executable recipes for the Geospatial Librarian catalog.

These recipes demonstrate how to work with SPOT-MS imagery through the data-engine
library. SPOT-MS provides 4 bands (Blue, Green, Red, NIR) at 6m resolution from
Airbus Defence and Space, accessed via Hum's internal STAC FastAPI catalog.

Collection: spot-ms (catalog: stac-fastapi)
Enum:       CollectionName.SPOT_MS
Bands:      B0 (Blue, 485nm), B1 (Green, 565nm), B2 (Red, 655nm), B3 (NIR, 825nm)
Resolution: 6.0m multispectral, 1.5m panchromatic
Data type:  uint16, missing_value=0
"""

from __future__ import annotations

import numpy as np

from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import (
    COLLECTION_BAND_MAP,
    SOURCE_INFO,
    CollectionInput,
    ObservationType,
    get_gsd,
    get_wavelength,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SPOT_MS_COLLECTION = CollectionName.SPOT_MS
SPOT_MS_INFO = SOURCE_INFO[SPOT_MS_COLLECTION]
SPOT_MS_NODATA = SPOT_MS_INFO["missing_value"]  # 0
SPOT_MS_RESOLUTION = SPOT_MS_INFO["resolution"]  # 6.0


# ---------------------------------------------------------------------------
# Recipe 1: Collection input configurations
# ---------------------------------------------------------------------------


def spot_ms_all_bands() -> CollectionInput:
    """Create a CollectionInput for all 4 SPOT-MS bands at native 6m resolution.

    Returns:
        CollectionInput configured for Blue, Green, Red, NIR at 6.0m
    """
    return CollectionInput(collection_name=SPOT_MS_COLLECTION)


def spot_ms_rgb_only() -> CollectionInput:
    """Create a CollectionInput for RGB bands only (no NIR).

    Useful for true-color visualization workflows where NIR is not needed.

    Returns:
        CollectionInput configured for Blue, Green, Red at 6.0m
    """
    return CollectionInput(
        collection_name=SPOT_MS_COLLECTION,
        band_ids=("B0", "B1", "B2"),
    )


def spot_ms_ndvi_bands() -> CollectionInput:
    """Create a CollectionInput for Red and NIR bands only.

    Minimal band selection for NDVI computation.

    Returns:
        CollectionInput configured for Red, NIR at 6.0m
    """
    return CollectionInput(
        collection_name=SPOT_MS_COLLECTION,
        band_ids=("B2", "B3"),
    )


def spot_ms_at_resolution(resolution: float) -> CollectionInput:
    """Create a CollectionInput for all bands at a custom resolution.

    Useful for resampling to match another dataset (e.g., 10m for Sentinel-2).

    Args:
        resolution: Target resolution in meters (e.g., 10.0 for Sentinel-2 matching)

    Returns:
        CollectionInput configured for all bands at the specified resolution
    """
    return CollectionInput(
        collection_name=SPOT_MS_COLLECTION,
        resolution=resolution,
    )


# ---------------------------------------------------------------------------
# Recipe 2: Spectral indices
# ---------------------------------------------------------------------------


def compute_ndvi(
    red: np.ndarray,
    nir: np.ndarray,
    nodata: int = SPOT_MS_NODATA,
) -> np.ndarray:
    """Compute NDVI from SPOT-MS Red (B2, 655nm) and NIR (B3, 825nm) bands.

    Normalized Difference Vegetation Index. Values near +1 indicate dense
    vegetation; values near 0 indicate bare soil or impervious surfaces;
    negative values indicate water.

    Args:
        red: Red band array (B2). Expected dtype uint16.
        nir: NIR band array (B3). Expected dtype uint16.
        nodata: Missing value to mask out (default: 0).

    Returns:
        NDVI array with float32 values in [-1, 1]. Nodata pixels are NaN.
    """
    mask = (red == nodata) | (nir == nodata)
    red_f = red.astype(np.float32)
    nir_f = nir.astype(np.float32)
    denominator = nir_f + red_f
    ndvi = np.where(denominator > 0, (nir_f - red_f) / denominator, np.nan)
    ndvi[mask] = np.nan
    return ndvi


def compute_ndwi(
    green: np.ndarray,
    nir: np.ndarray,
    nodata: int = SPOT_MS_NODATA,
) -> np.ndarray:
    """Compute NDWI from SPOT-MS Green (B1, 565nm) and NIR (B3, 825nm) bands.

    Normalized Difference Water Index (McFeeters, 1996). Positive values
    indicate open water surfaces; negative values indicate vegetation or soil.

    Args:
        green: Green band array (B1). Expected dtype uint16.
        nir: NIR band array (B3). Expected dtype uint16.
        nodata: Missing value to mask out (default: 0).

    Returns:
        NDWI array with float32 values in [-1, 1]. Nodata pixels are NaN.
    """
    mask = (green == nodata) | (nir == nodata)
    green_f = green.astype(np.float32)
    nir_f = nir.astype(np.float32)
    denominator = green_f + nir_f
    ndwi = np.where(denominator > 0, (green_f - nir_f) / denominator, np.nan)
    ndwi[mask] = np.nan
    return ndwi


def compute_gndvi(
    green: np.ndarray,
    nir: np.ndarray,
    nodata: int = SPOT_MS_NODATA,
) -> np.ndarray:
    """Compute Green NDVI from SPOT-MS Green (B1, 565nm) and NIR (B3, 825nm).

    Green Normalized Difference Vegetation Index. More sensitive to
    chlorophyll concentration than standard NDVI. Useful for assessing
    vegetation vigor and nitrogen status in crops.

    Args:
        green: Green band array (B1). Expected dtype uint16.
        nir: NIR band array (B3). Expected dtype uint16.
        nodata: Missing value to mask out (default: 0).

    Returns:
        GNDVI array with float32 values in [-1, 1]. Nodata pixels are NaN.
    """
    mask = (green == nodata) | (nir == nodata)
    green_f = green.astype(np.float32)
    nir_f = nir.astype(np.float32)
    denominator = nir_f + green_f
    gndvi = np.where(denominator > 0, (nir_f - green_f) / denominator, np.nan)
    gndvi[mask] = np.nan
    return gndvi


# ---------------------------------------------------------------------------
# Recipe 3: Nodata masking utility
# ---------------------------------------------------------------------------


def mask_nodata(
    bands: np.ndarray,
    nodata: int = SPOT_MS_NODATA,
) -> np.ndarray:
    """Create a boolean mask where True indicates valid (non-nodata) pixels.

    For multi-band arrays, a pixel is valid only if ALL bands have non-nodata
    values. This is the standard approach before computing indices or running
    classification.

    Args:
        bands: Array of shape (n_bands, height, width) or (height, width).
        nodata: Missing value (default: 0).

    Returns:
        Boolean array of shape (height, width). True = valid pixel.
    """
    if bands.ndim == 3:
        return np.all(bands != nodata, axis=0)
    return bands != nodata


# ---------------------------------------------------------------------------
# Recipe 4: Band metadata inspection
# ---------------------------------------------------------------------------


def print_spot_ms_band_info() -> None:
    """Print detailed band metadata for SPOT-MS from the data-engine registry.

    Prints band IDs, names, observation types, ground sample distance, and
    center wavelength for each band.
    """
    info = SOURCE_INFO[SPOT_MS_COLLECTION]
    band_map = COLLECTION_BAND_MAP[SPOT_MS_COLLECTION]

    print("SPOT-MS Band Information")
    print("=" * 60)
    print(f"  Collection ID : {SPOT_MS_COLLECTION.id}")
    print(f"  Catalog       : {SPOT_MS_COLLECTION.catalog_id}")
    print(f"  Resolution    : {info['resolution']}m")
    print(f"  Data type     : {info['dtype']}")
    print(f"  Missing value : {info['missing_value']}")
    print()
    print(f"  {'Index':<6} {'Band ID':<6} {'Name':<8} {'ObservationType':<20} {'GSD':>5} {'Wavelength':>11}")
    print(f"  {'-'*6} {'-'*6} {'-'*8} {'-'*20} {'-'*5} {'-'*11}")

    for idx, obs_type in band_map.items():
        band_id = info["band_ids"][idx]
        band_name = info["band_names"][idx]
        gsd = get_gsd(obs_type)
        wl = get_wavelength(obs_type)
        gsd_str = f"{gsd}m" if gsd is not None else "N/A"
        wl_str = f"{wl}nm" if wl is not None else "N/A"
        print(f"  {idx:<6} {band_id:<6} {band_name:<8} {obs_type.name:<20} {gsd_str:>5} {wl_str:>11}")


# ---------------------------------------------------------------------------
# Recipe 5: Cross-sensor resolution matching
# ---------------------------------------------------------------------------


def spot_ms_matched_to_sentinel2() -> tuple[CollectionInput, CollectionInput]:
    """Create matched CollectionInputs for SPOT-MS and Sentinel-2 at 10m.

    Returns SPOT-MS resampled to 10m and Sentinel-2 visible/NIR bands at
    their native 10m resolution. The two inputs can be stacked directly
    for multi-sensor analysis.

    Returns:
        Tuple of (spot_input, sentinel2_input) both at 10m resolution.
    """
    spot_input = CollectionInput(
        collection_name=CollectionName.SPOT_MS,
        resolution=10.0,
    )
    s2_input = CollectionInput(
        collection_name=CollectionName.SENTINEL2,
        band_ids=("B02", "B03", "B04", "B08"),  # Blue, Green, Red, NIR
        resolution=10.0,
    )
    return spot_input, s2_input


def spot_ms_matched_to_naip() -> tuple[CollectionInput, CollectionInput]:
    """Create matched CollectionInputs for SPOT-MS and NAIP at 6m.

    Returns SPOT-MS at native 6m and NAIP resampled from 2.5m to 6m.
    Useful for comparing commercial SPOT with free NAIP over US sites.

    Returns:
        Tuple of (spot_input, naip_input) both at 6m resolution.
    """
    spot_input = CollectionInput(
        collection_name=CollectionName.SPOT_MS,
    )
    naip_input = CollectionInput(
        collection_name=CollectionName.NAIP,
        resolution=6.0,
    )
    return spot_input, naip_input


# ---------------------------------------------------------------------------
# Main — run band info display when executed directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print_spot_ms_band_info()
