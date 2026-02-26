"""
Copernicus DEM (GLO-30 / GLO-90) -- Standalone Recipe

Demonstrates how to access Copernicus DEM elevation data from Microsoft
Planetary Computer via direct STAC queries and compute zonal statistics
(median, range) per H3 cell.

IMPORTANT: Copernicus DEM is NOT integrated into the Hum Data Engine.
There is no CollectionName entry for COP-DEM and no ancillary data class.
The Data Engine uses NASADEM for elevation via ElevationAncillaryData
(see hum_ai.data_engine.ancillary.elevation). This recipe shows how to
access Copernicus DEM independently via direct STAC queries to Planetary
Computer, which hosts 'cop-dem-glo-30' and 'cop-dem-glo-90' collections.

Usage:
    python cop-dem.py

Requirements:
    pip install pystac-client planetary-computer odc-stac h3 rioxarray rasterstats shapely
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

import h3
import numpy as np
import odc.stac
import pandas as pd
import planetary_computer
import pystac_client
from rasterstats import zonal_stats
from shapely.geometry import Polygon
from shapely.ops import unary_union

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

STAC_CATALOG_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"

# Planetary Computer hosts two Copernicus DEM collections:
#   'cop-dem-glo-30' -- 30m (~1 arc-second) posting
#   'cop-dem-glo-90' -- 90m (~3 arc-second) posting
STAC_COLLECTION_30M = "cop-dem-glo-30"
STAC_COLLECTION_90M = "cop-dem-glo-90"

# Default to 30m product
STAC_COLLECTION = STAC_COLLECTION_30M

# H3 resolution 11 (~2000 m2 cells, ~24.8m spacing) matches 30m pixels well,
# consistent with the Data Engine's NASADEM configuration.
DEFAULT_H3_RESOLUTION = 11

OUTPUT_COLUMNS = ["cell", "elevation_median", "elevation_range"]

# Copernicus DEM uses 0 as nodata for ocean/void areas
NODATA_VALUE = 0


# ---------------------------------------------------------------------------
# Helper: convert H3 cells to a unified polygon
# ---------------------------------------------------------------------------


def h3_cells_to_polygon(h3_cells: Iterable[str]) -> Polygon:
    """Convert a collection of H3 cell IDs to a single Shapely polygon."""
    polygons = []
    for cell in h3_cells:
        # h3.cell_to_boundary returns (lat, lng) pairs; Shapely wants (lng, lat)
        lonlats = [(lng, lat) for (lat, lng) in h3.cell_to_boundary(cell)]
        polygons.append(Polygon(lonlats))
    return unary_union(polygons)


# ---------------------------------------------------------------------------
# Step 1: Search Planetary Computer STAC for Copernicus DEM tiles
# ---------------------------------------------------------------------------


def search_copdem_tiles(
    bbox: tuple[float, float, float, float],
    collection: str = STAC_COLLECTION,
):
    """
    Search the Planetary Computer STAC catalog for Copernicus DEM tiles
    intersecting the given bounding box.

    NOTE: This uses direct STAC queries -- there is no CollectionName enum
    entry for Copernicus DEM in the data-engine. The data-engine's
    CollectionInput / CollectionName system does not support COP-DEM.

    Parameters
    ----------
    bbox : tuple
        (west, south, east, north) in EPSG:4326
    collection : str
        STAC collection ID. Either 'cop-dem-glo-30' (30m) or 'cop-dem-glo-90' (90m).

    Returns
    -------
    pystac.ItemCollection
        Matched STAC items
    """
    catalog = pystac_client.Client.open(
        STAC_CATALOG_URL,
        modifier=planetary_computer.sign_inplace,
    )

    search = catalog.search(
        collections=[collection],
        bbox=bbox,
    )
    items = search.item_collection()
    logger.info("STAC search returned %d Copernicus DEM items from '%s'",
                len(items), collection)
    return items


# ---------------------------------------------------------------------------
# Step 2: Load raster data via odc.stac
# ---------------------------------------------------------------------------


def load_copdem_raster(items, bbox: tuple[float, float, float, float]):
    """
    Load Copernicus DEM tiles as a dask-backed xarray DataArray.

    Parameters
    ----------
    items : pystac.ItemCollection
        STAC items from the search step
    bbox : tuple
        (west, south, east, north) to spatially subset the load

    Returns
    -------
    xarray.DataArray
        Elevation values (meters above EGM2008 geoid) with nodata handling
    """
    data = odc.stac.load(
        items,
        chunks={"x": 128, "y": 128},
        bbox=bbox,
        bands=["data"],  # Copernicus DEM band name is 'data'
    )

    # The loaded dataset has a 'data' variable containing elevation
    data = data["data"]

    # Handle nodata -- Copernicus DEM uses 0 for ocean/void
    data = data.where(data != NODATA_VALUE, np.nan)

    logger.info(
        "Loaded raster: shape=%s, CRS=%s", data.shape, data.rio.crs
    )
    return data


# ---------------------------------------------------------------------------
# Step 3: Compute zonal statistics per H3 cell
# ---------------------------------------------------------------------------


def compute_elevation_stats(
    data,
    h3_cells: list[str],
    default_h3_resolution: int = DEFAULT_H3_RESOLUTION,
) -> pd.DataFrame:
    """
    Compute elevation median and range for each H3 cell from Copernicus DEM.

    This follows the same pattern as the Data Engine's ElevationAncillaryData
    (which uses NASADEM), adapted for Copernicus DEM.

    Parameters
    ----------
    data : xarray.DataArray
        The loaded Copernicus DEM raster
    h3_cells : list of str
        H3 cell IDs to summarize
    default_h3_resolution : int
        The H3 resolution that matches the raster pixel spacing.
        Cells finer than this use all_touched=True.

    Returns
    -------
    pd.DataFrame
        Columns: cell, elevation_median, elevation_range
    """
    resolution = h3.get_resolution(h3_cells[0])
    if resolution > default_h3_resolution:
        logger.info("Using all_touched=True (H3 res %d > default %d)",
                     resolution, default_h3_resolution)
        all_touched = True
    else:
        all_touched = False

    nodata = NODATA_VALUE

    results = []
    for cell in h3_cells:
        boundary = h3.cell_to_boundary(cell)
        poly = Polygon([(lng, lat) for lat, lng in boundary])

        try:
            subset = data.rio.clip(geometries=[poly], crs="EPSG:4326")
        except Exception:
            # Cell has no data coverage (e.g., over ocean)
            continue

        summary = zonal_stats(
            [poly],
            subset.to_numpy(),
            affine=subset.rio.transform(),
            nodata=nodata,
            stats=["median", "range"],
            all_touched=all_touched,
        )[0]

        if None not in summary.values():
            results.append({
                "cell": cell,
                "elevation_median": summary["median"],
                "elevation_range": summary["range"],
            })

    df = pd.DataFrame(results, columns=OUTPUT_COLUMNS)
    logger.info("Computed elevation stats for %d / %d cells",
                len(df), len(h3_cells))
    return df


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


def summarize_elevation(
    h3_cells: list[str],
    collection: str = STAC_COLLECTION,
) -> pd.DataFrame:
    """
    End-to-end pipeline: search, load, and summarize Copernicus DEM elevation
    for the given H3 cells.

    Unlike NASADEM (which has ElevationAncillaryData in the data-engine),
    Copernicus DEM must be accessed via direct STAC queries as shown here.
    """
    polygon = h3_cells_to_polygon(h3_cells)
    bbox = polygon.bounds

    items = search_copdem_tiles(bbox, collection=collection)
    if len(items) == 0:
        logger.warning("No Copernicus DEM tiles found for the given area")
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    data = load_copdem_raster(items, bbox)
    df = compute_elevation_stats(data, h3_cells)
    return df


# ---------------------------------------------------------------------------
# Demo / test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Example: a small cluster of H3 cells in coastal Alaska
    # (same test region used in the Data Engine's elevation.py for comparison)
    lat, lng = 60.66, -145.91
    center_cell = h3.latlng_to_cell(lat, lng, DEFAULT_H3_RESOLUTION)
    test_cells = list(h3.grid_disk(center_cell, k=1))
    logger.info("Test area: %d H3 cells at resolution %d",
                len(test_cells), DEFAULT_H3_RESOLUTION)

    # Run with GLO-30 (30m) product
    result = summarize_elevation(test_cells, collection=STAC_COLLECTION_30M)
    print("\n--- Copernicus DEM GLO-30 Elevation Summary ---")
    print(result.to_string(index=False))
    print(f"\nMedian elevation across cells: {result['elevation_median'].median():.1f} m")
    print(f"Max elevation range in a cell: {result['elevation_range'].max():.1f} m")

    print("\nNote: The Data Engine uses NASADEM (not Copernicus DEM) for its")
    print("elevation ancillary data. See nasadem.py for the Data Engine recipe.")
