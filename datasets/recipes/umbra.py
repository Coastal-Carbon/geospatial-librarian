"""
Umbra SAR: Executable recipes for data access and processing.

This module provides ready-to-use functions for working with Umbra SAR
imagery through Hum's data engine. Umbra is a commercial X-band SAR sensor
providing ~1m resolution VV-polarized imagery via the stac-fastapi catalog.

Data engine references:
    - CollectionName.UMBRA -> catalog='stac-fastapi', collection='umbra'
    - SOURCE_INFO[CollectionName.UMBRA] -> resolution=1.0, band_ids=['HH','VV','VH','HV']
    - ObservationType.UMBRA_VV -> band index 0 in COLLECTION_BAND_MAP
    - BandInfo(gsd=1, wavelength=None) in OBSERVATION_BAND_METADATA
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
from scipy.ndimage import uniform_filter
from shapely.geometry import Polygon, box

from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import (
    COLLECTION_BAND_MAP,
    SOURCE_INFO,
    CollectionInput,
    ObservationType,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UMBRA_COLLECTION = CollectionName.UMBRA
UMBRA_CATALOG_ID = UMBRA_COLLECTION.catalog_id      # 'stac-fastapi'
UMBRA_COLLECTION_ID = UMBRA_COLLECTION.id            # 'umbra'
UMBRA_RESOLUTION = SOURCE_INFO[UMBRA_COLLECTION]['resolution']  # 1.0
UMBRA_BAND_IDS = SOURCE_INFO[UMBRA_COLLECTION]['band_ids']      # ['HH','VV','VH','HV']
UMBRA_OBS_TYPE = ObservationType.UMBRA_VV


# ---------------------------------------------------------------------------
# Data access helpers
# ---------------------------------------------------------------------------

def make_umbra_input(
    band_ids: tuple[str, ...] = ('VV',),
    resolution: float | None = None,
) -> CollectionInput:
    """Create a CollectionInput configured for Umbra SAR.

    Args:
        band_ids: Polarization bands to load. Defaults to ('VV',) since
            >98% of the Umbra archive is VV-polarized.
        resolution: Target resolution in meters. Defaults to the native
            1.0m from SOURCE_INFO.

    Returns:
        A CollectionInput ready for use in data engine pipelines.
    """
    kwargs: dict = {
        'collection_name': UMBRA_COLLECTION,
        'band_ids': band_ids,
    }
    if resolution is not None:
        kwargs['resolution'] = resolution
    return CollectionInput(**kwargs)


def print_umbra_info() -> None:
    """Print a summary of Umbra's data engine configuration."""
    info = SOURCE_INFO[UMBRA_COLLECTION]
    band_map = COLLECTION_BAND_MAP[UMBRA_COLLECTION]

    print("Umbra SAR — Data Engine Configuration")
    print("=" * 45)
    print(f"  Catalog:        {UMBRA_CATALOG_ID}")
    print(f"  Collection ID:  {UMBRA_COLLECTION_ID}")
    print(f"  Resolution:     {info['resolution']}m")
    print(f"  Band IDs:       {info['band_ids']}")
    print(f"  Band mapping:   {band_map}")
    print(f"  Requester pays: {info['requester_pays']}")


# ---------------------------------------------------------------------------
# SAR preprocessing utilities
# ---------------------------------------------------------------------------

def to_db(backscatter: np.ndarray) -> np.ndarray:
    """Convert linear-scale SAR backscatter to decibels (dB).

    Args:
        backscatter: Array of SAR backscatter values in linear (power) scale.

    Returns:
        Array of backscatter values in dB (10 * log10).
        Zero and negative values are mapped to NaN.
    """
    safe = np.where(backscatter > 0, backscatter, np.nan)
    return 10.0 * np.log10(safe)


def from_db(db_values: np.ndarray) -> np.ndarray:
    """Convert dB-scale SAR backscatter back to linear (power) scale.

    Args:
        db_values: Array of SAR backscatter values in dB.

    Returns:
        Array of backscatter values in linear scale.
    """
    return 10.0 ** (db_values / 10.0)


def lee_filter(image: np.ndarray, size: int = 7) -> np.ndarray:
    """Apply a simplified Lee speckle filter to SAR imagery.

    The Lee filter is an adaptive filter that preserves edges while
    reducing speckle noise. It works by computing a weighted combination
    of the local mean and the original pixel value, where the weight
    depends on the local coefficient of variation.

    Args:
        image: 2D SAR backscatter array in linear scale.
        size: Window size for the filter (default 7x7). Larger windows
            provide more smoothing but reduce spatial detail.

    Returns:
        Speckle-filtered image in linear scale.
    """
    mean = uniform_filter(image.astype(np.float64), size=size)
    sqr_mean = uniform_filter((image.astype(np.float64)) ** 2, size=size)
    variance = sqr_mean - mean ** 2
    overall_variance = np.var(image)

    # Compute adaptive weight: high variance = keep original, low = use mean
    weight = np.clip(variance / (variance + overall_variance + 1e-10), 0, 1)
    return mean + weight * (image - mean)


# ---------------------------------------------------------------------------
# Change detection
# ---------------------------------------------------------------------------

def log_ratio_change(
    before: np.ndarray,
    after: np.ndarray,
) -> np.ndarray:
    """Compute log-ratio change detection between two SAR scenes.

    The log-ratio is the standard approach for SAR change detection because
    it is symmetric, approximately normally distributed, and accounts for
    the multiplicative noise model of SAR.

    Values near 0 indicate no change. Positive values indicate an increase
    in backscatter (e.g., new construction, flooding retreat exposing rough
    surfaces). Negative values indicate a decrease (e.g., building
    demolition, flooding of previously dry surfaces).

    Args:
        before: SAR backscatter from earlier date (linear scale).
        after: SAR backscatter from later date (linear scale).

    Returns:
        Log-ratio change map. NaN where either input is zero or negative.
    """
    safe_before = np.where(before > 0, before, np.nan)
    safe_after = np.where(after > 0, after, np.nan)
    return np.log(safe_after / safe_before)


def threshold_changes(
    change_map: np.ndarray,
    n_sigma: float = 2.0,
) -> np.ndarray:
    """Classify pixels as changed or unchanged using a sigma threshold.

    Assumes the log-ratio change map is approximately normally distributed,
    which holds for most SAR change detection scenarios over natural and
    built environments.

    Args:
        change_map: Log-ratio change map from ``log_ratio_change``.
        n_sigma: Number of standard deviations for the change threshold.
            Higher values = fewer false alarms but more missed detections.
            Typical range is 2.0 to 3.0.

    Returns:
        Integer classification: -1 = decrease, 0 = no change, 1 = increase.
    """
    mean = np.nanmean(change_map)
    std = np.nanstd(change_map)
    result = np.zeros_like(change_map, dtype=np.int8)
    result[change_map > mean + n_sigma * std] = 1
    result[change_map < mean - n_sigma * std] = -1
    return result


# ---------------------------------------------------------------------------
# Multi-source collection setup
# ---------------------------------------------------------------------------

def make_sar_optical_inputs() -> dict[str, CollectionInput]:
    """Create a standard set of SAR + optical collection inputs.

    Returns a dictionary with keys 'umbra', 'sentinel1', 'sentinel2'
    configured with their default bands and resolutions from SOURCE_INFO.

    This is a convenience function for common multi-source workflows
    where high-res SAR (Umbra), free SAR (Sentinel-1), and optical
    (Sentinel-2) are used together.

    Returns:
        Dictionary mapping collection short names to CollectionInput objects.
    """
    return {
        'umbra': CollectionInput(
            collection_name=CollectionName.UMBRA,
            band_ids=('VV',),
        ),
        'sentinel1': CollectionInput(
            collection_name=CollectionName.SENTINEL1,
        ),
        'sentinel2': CollectionInput(
            collection_name=CollectionName.SENTINEL2,
        ),
    }


# ---------------------------------------------------------------------------
# Main (demonstration)
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print_umbra_info()

    print("\n--- Example: Create Umbra CollectionInput ---")
    umbra_input = make_umbra_input()
    print(f"  Collection: {umbra_input.collection_name.id}")
    print(f"  Bands:      {umbra_input.band_ids}")
    print(f"  Resolution: {umbra_input.resolution}m")

    print("\n--- Example: Multi-source inputs ---")
    inputs = make_sar_optical_inputs()
    for name, inp in inputs.items():
        info = SOURCE_INFO[inp.collection_name]
        print(f"  {name}: {info['resolution']}m, bands={inp.band_ids}")

    print("\n--- Example: SAR preprocessing demo ---")
    # Simulate a small SAR backscatter image
    rng = np.random.default_rng(42)
    synthetic_sar = rng.exponential(scale=0.1, size=(64, 64)).astype(np.float32)
    filtered = lee_filter(synthetic_sar, size=5)
    db_image = to_db(filtered)
    print(f"  Raw range:      [{synthetic_sar.min():.4f}, {synthetic_sar.max():.4f}]")
    print(f"  Filtered range: [{filtered.min():.4f}, {filtered.max():.4f}]")
    print(f"  dB range:       [{np.nanmin(db_image):.1f}, {np.nanmax(db_image):.1f}]")

    print("\n--- Example: Change detection demo ---")
    scene_t1 = rng.exponential(scale=0.1, size=(64, 64)).astype(np.float32)
    scene_t2 = scene_t1.copy()
    # Simulate a change: increase backscatter in a 10x10 patch (e.g., new structure)
    scene_t2[20:30, 20:30] *= 5.0
    change = log_ratio_change(scene_t1, scene_t2)
    classified = threshold_changes(change, n_sigma=2.0)
    n_increase = np.sum(classified == 1)
    n_decrease = np.sum(classified == -1)
    n_nochange = np.sum(classified == 0)
    print(f"  Increase pixels: {n_increase}")
    print(f"  Decrease pixels: {n_decrease}")
    print(f"  No change:       {n_nochange}")
