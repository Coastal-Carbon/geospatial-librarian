"""
ESA WorldCover — Recipe for accessing land cover classification data

This recipe demonstrates how to:
  1. Search for ESA WorldCover items via Microsoft Planetary Computer
  2. Load the classification raster for an area of interest
  3. Decode class values and compute land cover statistics
  4. Use the IO LULC Annual ancillary module for H3 zonal summaries

ESA WorldCover class values (map band):
    0   = No Data
    10  = Tree cover
    20  = Shrubland
    30  = Grassland
    40  = Cropland
    50  = Built-up
    60  = Bare / sparse vegetation
    70  = Snow and ice
    80  = Permanent water bodies
    90  = Herbaceous wetland
    95  = Mangroves
    100 = Moss and lichen
"""

import numpy as np
import odc.stac

from hum_ai.data_engine.collections import CollectionName
from hum_ai.data_engine.ingredients import COLLECTION_BAND_MAP, SOURCE_INFO
from hum_ai.stac.search import get_client


# ---------------------------------------------------------------------------
# 1. Search for ESA WorldCover items covering a bounding box
# ---------------------------------------------------------------------------

def search_worldcover_items(bbox: tuple[float, float, float, float]):
    """Search for ESA WorldCover items over a bounding box.

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat) in WGS84 degrees.

    Returns:
        pystac ItemCollection of matching WorldCover tiles.
    """
    catalog = get_client(CollectionName.ESA_WORLDCOVER)
    search = catalog.search(
        collections=[CollectionName.ESA_WORLDCOVER.id],
        bbox=bbox,
    )
    items = search.item_collection()
    print(f"Found {len(items)} ESA WorldCover items for bbox {bbox}")
    return items


# ---------------------------------------------------------------------------
# 2. Load the classification raster as an xarray Dataset
# ---------------------------------------------------------------------------

def load_worldcover_map(
    bbox: tuple[float, float, float, float],
    crs: str = "EPSG:4326",
    resolution: float | None = None,
):
    """Load the ESA WorldCover classification map for a bounding box.

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat) in WGS84 degrees.
        crs: Target coordinate reference system. Default is EPSG:4326.
        resolution: Target resolution in CRS units. Defaults to native 10m
            (approximately 0.0001 degrees in EPSG:4326, or 10.0 in UTM).

    Returns:
        xarray.Dataset with the 'map' band containing class values.
    """
    items = search_worldcover_items(bbox)
    if len(items) == 0:
        raise ValueError(f"No WorldCover items found for bbox {bbox}")

    # Use the 'map' band only (index 0) for land cover classification.
    # Bands are: map, input_quality.1, input_quality.2, input_quality.3
    band_info = SOURCE_INFO[CollectionName.ESA_WORLDCOVER]

    load_kwargs = dict(
        bbox=bbox,
        crs=crs,
        bands=[band_info["band_ids"][0]],  # 'map' band only
        resampling="nearest",  # categorical data requires nearest-neighbor
    )
    if resolution is not None:
        load_kwargs["resolution"] = resolution

    dataset = odc.stac.load(items, **load_kwargs)
    return dataset


# ---------------------------------------------------------------------------
# 3. Decode class values and compute area statistics
# ---------------------------------------------------------------------------

# ESA WorldCover class lookup (official class values from the product)
WORLDCOVER_CLASSES = {
    0: "No Data",
    10: "Tree cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare / sparse vegetation",
    70: "Snow and ice",
    80: "Permanent water bodies",
    90: "Herbaceous wetland",
    95: "Mangroves",
    100: "Moss and lichen",
}


def compute_class_fractions(classification: np.ndarray) -> dict[str, float]:
    """Compute the fractional area of each land cover class.

    Args:
        classification: 2D numpy array of WorldCover class values.

    Returns:
        Dictionary mapping class name to fraction of valid pixels.
    """
    # Exclude no-data pixels from the denominator
    valid_mask = classification != 0
    total_valid = valid_mask.sum()

    if total_valid == 0:
        return {name: 0.0 for name in WORLDCOVER_CLASSES.values()}

    fractions = {}
    for value, name in WORLDCOVER_CLASSES.items():
        if value == 0:
            continue
        count = (classification == value).sum()
        fractions[name] = float(count / total_valid)

    return fractions


# ---------------------------------------------------------------------------
# 4. H3 zonal summaries using the IO LULC Annual ancillary module
# ---------------------------------------------------------------------------

def summarize_landcover_for_cells(h3_cells: list[str], date_range: str = "2023-06-01"):
    """Compute landcover zonal statistics for a set of H3 cells.

    This uses the IO LULC Annual product (io-lulc-annual-v02), which is the
    temporal counterpart to ESA WorldCover and uses the LandcoverCategory enum:

        LandcoverCategory.No_Data           = 0
        LandcoverCategory.Water             = 1
        LandcoverCategory.Trees             = 2
        LandcoverCategory.Flooded_vegetation = 4
        LandcoverCategory.Crops             = 5
        LandcoverCategory.Built_area        = 7
        LandcoverCategory.Bare_ground       = 8
        LandcoverCategory.Snow_ice          = 9
        LandcoverCategory.Clouds            = 10
        LandcoverCategory.Rangeland         = 11

    Args:
        h3_cells: List of H3 cell IDs (as hex strings).
        date_range: Date range string for the STAC search.

    Returns:
        pandas DataFrame with columns:
            cell, start_time, end_time, landcover_majority, landcover_unique
    """
    from hum_ai.data_engine.ancillary.landcover import LandcoverAncillaryData

    lc = LandcoverAncillaryData()
    df = lc.summarize_from_cells(h3_cells, date_range=date_range)
    return df


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Example: Load WorldCover for a small area in the Netherlands
    bbox_netherlands = (4.0, 51.8, 5.0, 52.2)

    # Load the classification map
    ds = load_worldcover_map(bbox_netherlands)
    classification_array = ds["map"].values.squeeze()

    # Compute class fractions
    fractions = compute_class_fractions(classification_array)
    print("\nLand cover fractions:")
    for class_name, fraction in sorted(fractions.items(), key=lambda x: -x[1]):
        if fraction > 0.001:
            print(f"  {class_name:30s} {fraction:6.1%}")

    # Example: H3 zonal summary using IO LULC Annual
    # (requires database access and valid H3 cells)
    # example_cells = ["8a1fb466659ffff", "8a1fb46665d7fff"]
    # df = summarize_landcover_for_cells(example_cells)
    # print(df)
