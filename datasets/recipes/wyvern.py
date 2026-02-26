"""
Wyvern Hyperspectral Imagery — Data Engine Recipe
==================================================

Demonstrates how to set up a CollectionInput for Wyvern 23-band hyperspectral
imagery and access it through the data engine.

Key facts:
  - catalog_id: 'stac-fastapi'
  - collection_id: 'wyvern'
  - 23 contiguous hyperspectral bands from 503nm to 799nm
  - All bands at 5.3m resolution, uint16, missing_value=0
  - Commercial data — only Hum's licensed holdings are available

Bands (in order):
     0: Green_503     1: Green_510     2: Green_519     3: Green_535
     4: Green_549     5: Green_570     6: Yellow_584    7: Yellow_600
     8: Yellow_614    9: Red_635      10: Red_649      11: Red_660
    12: Red_669      13: Red_679      14: Red_690      15: Red_699
    16: Rededge_711  17: Rededge_722  18: Rededge_734  19: Rededge_750
    20: Rededge_764  21: Rededge_782  22: Nir_799
"""

import numpy as np

from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import (
    COLLECTION_BAND_MAP,
    SOURCE_INFO,
    CollectionInput,
    ObservationType,
)


# ---------------------------------------------------------------------------
# 1. Inspect available band information
# ---------------------------------------------------------------------------

wyvern_info = SOURCE_INFO[CollectionName.WYVERN]

print("Wyvern SOURCE_INFO:")
print(f"  Band IDs:       {wyvern_info['band_ids']}")
print(f"  Band Names:     {wyvern_info['band_names']}")
print(f"  Resolution:     {wyvern_info['resolution']}m")
print(f"  dtype:          {wyvern_info['dtype']}")
print(f"  missing_value:  {wyvern_info['missing_value']}")

print("\nWyvern ObservationType mapping:")
for band_idx, obs_type in COLLECTION_BAND_MAP[CollectionName.WYVERN].items():
    print(f"  Band {band_idx:2d}: {obs_type.name} = '{obs_type.value}'")


# ---------------------------------------------------------------------------
# 2. Create a CollectionInput — all 23 bands at default resolution
# ---------------------------------------------------------------------------

wyvern_all_bands = CollectionInput(
    collection_name=CollectionName.WYVERN,
    # band_ids and resolution default to SOURCE_INFO values:
    #   band_ids = all 23 hyperspectral bands
    #   resolution = 5.3m
)

print(f"\nAll-band input: {wyvern_all_bands.band_ids}")
print(f"Resolution: {wyvern_all_bands.resolution}m")


# ---------------------------------------------------------------------------
# 3. Create a CollectionInput — red edge subset for vegetation analysis
# ---------------------------------------------------------------------------

wyvern_red_edge = CollectionInput(
    collection_name=CollectionName.WYVERN,
    band_ids=(
        'Band_711nm', 'Band_722nm', 'Band_734nm',
        'Band_750nm', 'Band_764nm', 'Band_782nm',
    ),
)

print(f"\nRed edge subset: {wyvern_red_edge.band_ids}")


# ---------------------------------------------------------------------------
# 4. Create a CollectionInput — green bands for water quality analysis
# ---------------------------------------------------------------------------

wyvern_green = CollectionInput(
    collection_name=CollectionName.WYVERN,
    band_ids=(
        'Band_503nm', 'Band_510nm', 'Band_519nm',
        'Band_535nm', 'Band_549nm', 'Band_570nm',
    ),
)

print(f"Green subset: {wyvern_green.band_ids}")


# ---------------------------------------------------------------------------
# 5. Create a CollectionInput — red bands for chlorophyll absorption analysis
# ---------------------------------------------------------------------------

wyvern_red = CollectionInput(
    collection_name=CollectionName.WYVERN,
    band_ids=(
        'Band_635nm', 'Band_649nm', 'Band_660nm',
        'Band_669nm', 'Band_679nm', 'Band_690nm', 'Band_699nm',
    ),
)

print(f"Red subset: {wyvern_red.band_ids}")


# ---------------------------------------------------------------------------
# 6. Spectral index helpers — narrowband versions
# ---------------------------------------------------------------------------

def narrowband_ndvi(red_679: np.ndarray, nir_799: np.ndarray) -> np.ndarray:
    """Narrowband NDVI using the chlorophyll absorption maximum (679nm) and
    NIR reflectance plateau (799nm).

    More precise than broadband NDVI because Band_679nm sits exactly at the
    chlorophyll-a absorption trough rather than averaging across a wide red band.
    """
    return (nir_799 - red_679) / (nir_799 + red_679)


def ndre_narrowband(red_edge_711: np.ndarray, nir_799: np.ndarray) -> np.ndarray:
    """Narrowband NDRE (Normalized Difference Red Edge).

    Sensitive to chlorophyll content and canopy structure. The 711nm band
    sits at the base of the red edge inflection, making this index
    responsive to subtle vegetation stress signals.
    """
    return (nir_799 - red_edge_711) / (nir_799 + red_edge_711)


def green_ndvi(green_549: np.ndarray, nir_799: np.ndarray) -> np.ndarray:
    """Green NDVI — uses the green reflectance peak (549nm) instead of red.

    More sensitive to moderate-to-high chlorophyll concentrations where
    standard NDVI saturates. Also known as GNDVI.
    """
    return (nir_799 - green_549) / (nir_799 + green_549)


def mtci(
    red_679: np.ndarray,
    rededge_711: np.ndarray,
    rededge_750: np.ndarray,
) -> np.ndarray:
    """MERIS Terrestrial Chlorophyll Index.

    Uses three bands near 681nm, 709nm, and 753nm. Wyvern bands at 679nm,
    711nm, and 750nm are close approximations. MTCI is linearly related to
    canopy chlorophyll content over a wide range.
    """
    return (rededge_750 - rededge_711) / (rededge_711 - red_679)


# ---------------------------------------------------------------------------
# 7. Red Edge Position (REP) estimation
# ---------------------------------------------------------------------------

def red_edge_position(
    red_679: np.ndarray,
    red_699: np.ndarray,
    rededge_711: np.ndarray,
    rededge_734: np.ndarray,
    rededge_750: np.ndarray,
    rededge_782: np.ndarray,
) -> np.ndarray:
    """Estimate the Red Edge Position (REP) via linear interpolation.

    The REP is the wavelength at which the first derivative of reflectance
    is maximized in the 690-750nm region. Shifts in REP correlate strongly
    with chlorophyll concentration: higher chlorophyll shifts the red edge
    to longer wavelengths.

    This is a simplified 4-point linear interpolation method. For more
    precise estimation, fit a Gaussian or polynomial to the full red edge
    spectral profile.

    Returns wavelength in nanometers for each pixel.
    """
    # Midpoint reflectance between red absorption minimum and NIR plateau
    r_midpoint = (red_679 + rededge_782) / 2.0

    # Linear interpolation between the two bands that bracket r_midpoint
    # Using the 711nm and 734nm bands as the interpolation interval
    rep = 711.0 + 23.0 * (r_midpoint - rededge_711) / (rededge_734 - rededge_711)

    return rep


# ---------------------------------------------------------------------------
# 8. Spectral region wavelength arrays (for curve analysis)
# ---------------------------------------------------------------------------

# Center wavelengths in nanometers, in band order
WYVERN_WAVELENGTHS = np.array([
    503, 510, 519, 535, 549, 570,   # Green (indices 0-5)
    584, 600, 614,                    # Yellow (indices 6-8)
    635, 649, 660, 669, 679, 690, 699,  # Red (indices 9-15)
    711, 722, 734, 750, 764, 782,    # Red Edge (indices 16-21)
    799,                              # NIR (index 22)
], dtype=np.float64)

# Spectral region boundaries (band indices, inclusive)
SPECTRAL_REGIONS = {
    'green':     (0, 5),
    'yellow':    (6, 8),
    'red':       (9, 15),
    'red_edge':  (16, 21),
    'nir':       (22, 22),
}


# ---------------------------------------------------------------------------
# 9. First derivative of spectral curve
# ---------------------------------------------------------------------------

def spectral_derivative(
    spectral_cube: np.ndarray,
    wavelengths: np.ndarray = WYVERN_WAVELENGTHS,
) -> np.ndarray:
    """Compute the first derivative of a spectral cube along the band axis.

    Parameters
    ----------
    spectral_cube : np.ndarray
        Array of shape (23, H, W) — bands along axis 0.
    wavelengths : np.ndarray
        Center wavelengths in nm for each band. Defaults to WYVERN_WAVELENGTHS.

    Returns
    -------
    np.ndarray
        First derivative array of shape (22, H, W). Each slice [i] is
        (R[i+1] - R[i]) / (lambda[i+1] - lambda[i]).
    """
    d_reflectance = np.diff(spectral_cube, axis=0)
    d_wavelength = np.diff(wavelengths)
    # Broadcast wavelength deltas across spatial dimensions
    return d_reflectance / d_wavelength[:, np.newaxis, np.newaxis]


# ---------------------------------------------------------------------------
# 10. Multi-source project: Wyvern + Sentinel-2
# ---------------------------------------------------------------------------
# Combines Wyvern hyperspectral detail with Sentinel-2 for SWIR bands and
# temporal density.

multi_source_inputs = (
    CollectionInput(
        collection_name=CollectionName.WYVERN,
    ),
    CollectionInput(
        collection_name=CollectionName.SENTINEL2,
        catalog_filters={'eo:cloud_cover': {'lt': 5}},
    ),
)


# ---------------------------------------------------------------------------
# 11. Time-range filtering example
# ---------------------------------------------------------------------------
# This shows how to define a time range for filtering Wyvern scenes.
# NOTE: ProjectDefinition does not exist in the data-engine library.
# Use CollectionInput with catalog_filters or the search API directly.

from datetime import datetime, timezone

from hum_ai.data_engine.ingredients import Range

# Define a time range for your analysis
time_range = Range(
    min=datetime(2024, 1, 1, tzinfo=timezone.utc),
    max=datetime(2025, 1, 1, tzinfo=timezone.utc),
)

# Create a Wyvern CollectionInput (project-level configuration is handled
# by the specific format recipe, e.g., ImageChipsV3Configuration or
# OlmoEarthSamplesV1Configuration — not a generic ProjectDefinition class)
wyvern_for_project = CollectionInput(
    collection_name=CollectionName.WYVERN,
)


# ---------------------------------------------------------------------------
# 12. Checking data holdings for Wyvern
# ---------------------------------------------------------------------------
# Use the STAC catalog utilities to discover what Wyvern scenes exist for an
# area. The search functions are in the catalog and ancillary modules:
#
#   from hum_ai.data_engine.catalog.stac_utils import ...
#   from hum_ai.data_engine.ancillary.search import search
#
# The search function queries Hum's internal STAC FastAPI for the 'wyvern'
# collection. Only scenes that Hum has ingested will be returned.


# ---------------------------------------------------------------------------
# 13. COLLECTION_BAND_MAP reference — maps band index to ObservationType
# ---------------------------------------------------------------------------

wyvern_band_map = COLLECTION_BAND_MAP[CollectionName.WYVERN]
# Returns:
# {
#     0: ObservationType.WYVERN_503NM,
#     1: ObservationType.WYVERN_510NM,
#     2: ObservationType.WYVERN_519NM,
#     3: ObservationType.WYVERN_535NM,
#     4: ObservationType.WYVERN_549NM,
#     5: ObservationType.WYVERN_570NM,
#     6: ObservationType.WYVERN_584NM,
#     7: ObservationType.WYVERN_600NM,
#     8: ObservationType.WYVERN_614NM,
#     9: ObservationType.WYVERN_635NM,
#     10: ObservationType.WYVERN_649NM,
#     11: ObservationType.WYVERN_660NM,
#     12: ObservationType.WYVERN_669NM,
#     13: ObservationType.WYVERN_679NM,
#     14: ObservationType.WYVERN_690NM,
#     15: ObservationType.WYVERN_699NM,
#     16: ObservationType.WYVERN_711NM,
#     17: ObservationType.WYVERN_722NM,
#     18: ObservationType.WYVERN_734NM,
#     19: ObservationType.WYVERN_750NM,
#     20: ObservationType.WYVERN_764NM,
#     21: ObservationType.WYVERN_782NM,
#     22: ObservationType.WYVERN_799NM,
# }
