"""
SuperDove — Data Engine Recipe
==============================

Demonstrates how to set up a CollectionInput for Planet SuperDove 8-band
imagery and access it through the data engine.

Bands (in order):
    0: Coastal Blue   1: Blue        2: Green I   3: Green
    4: Yellow         5: Red         6: Red Edge  7: Near-Infrared
"""

from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import (
    SOURCE_INFO,
    COLLECTION_BAND_MAP,
    CollectionInput,
    ObservationType,
)


# ---------------------------------------------------------------------------
# 1. Inspect available band information
# ---------------------------------------------------------------------------

superdove_info = SOURCE_INFO[CollectionName.SUPERDOVE]

print("SuperDove SOURCE_INFO:")
print(f"  Band IDs:   {superdove_info['band_ids']}")
print(f"  Band Names: {superdove_info['band_names']}")
print(f"  Resolution: {superdove_info['resolution']}m")

print("\nSuperDove ObservationType mapping:")
for band_idx, obs_type in COLLECTION_BAND_MAP[CollectionName.SUPERDOVE].items():
    print(f"  Band {band_idx}: {obs_type.name} = '{obs_type.value}'")


# ---------------------------------------------------------------------------
# 2. Create a CollectionInput — all 8 bands at default resolution
# ---------------------------------------------------------------------------

superdove_all_bands = CollectionInput(
    collection_name=CollectionName.SUPERDOVE,
    # band_ids and resolution default to SOURCE_INFO values:
    #   band_ids = all 8 bands
    #   resolution = 1.0m (Hum's stored resolution)
)

print(f"\nAll-band input: {superdove_all_bands.band_ids}")
print(f"Resolution: {superdove_all_bands.resolution}m")


# ---------------------------------------------------------------------------
# 3. Create a CollectionInput — RGB + NIR subset
# ---------------------------------------------------------------------------

superdove_rgbn = CollectionInput(
    collection_name=CollectionName.SUPERDOVE,
    band_ids=('Blue', 'Green', 'Red', 'Near-Infrared'),
)

print(f"\nRGB+NIR subset: {superdove_rgbn.band_ids}")


# ---------------------------------------------------------------------------
# 4. Create a CollectionInput — bands for vegetation analysis (NDVI + NDRE)
# ---------------------------------------------------------------------------

superdove_veg = CollectionInput(
    collection_name=CollectionName.SUPERDOVE,
    band_ids=('Red', 'Red Edge', 'Near-Infrared'),
)

print(f"Vegetation subset: {superdove_veg.band_ids}")


# ---------------------------------------------------------------------------
# 5. Spectral index helpers
# ---------------------------------------------------------------------------

def ndvi(red, nir):
    """Normalized Difference Vegetation Index: (NIR - Red) / (NIR + Red)"""
    return (nir - red) / (nir + red)


def ndre(red_edge, nir):
    """Normalized Difference Red Edge Index: (NIR - RedEdge) / (NIR + RedEdge)
    More sensitive to chlorophyll content than NDVI.
    """
    return (nir - red_edge) / (nir + red_edge)


def ndwi(green, nir):
    """Normalized Difference Water Index: (Green - NIR) / (Green + NIR)"""
    return (green - nir) / (green + nir)
